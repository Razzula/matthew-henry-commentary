# pylint: disable=fixme, line-too-long, invalid-name, superfluous-parens, trailing-whitespace, arguments-differ
"""A script to scrape BibleHub for Strong's numbers and other data for the Hebrew and Greek text of the Bible."""
import json
import os
import re
import time
import unicodedata

import requests
from bs4 import BeautifulSoup
import urllib3

rootDir = os.path.dirname(__file__)

with open(os.path.join(rootDir, 'src', 'manifest.json'), 'r', encoding='utf-8') as f:
    manifest = json.load(f)

startTime = time.time()

for book in manifest:

    # if (book.get('title') != 'Luke'):
    #     continue

    if (book['usfm'] == 'SNG'):
        bookName = 'songs'
    else:
        if (book.get('full-title')):
            bookName = str.lower(book['full-title'])
            # de-numericalise
            bookName = bookName.replace('iii ', '3_')
            bookName = bookName.replace('ii ', '2_')
            bookName = bookName.replace('i ', '1_')
        else:
            bookName = str.lower(book["title"])

    print(book['usfm'])

    for chapter, verseCount in enumerate(book['chapters']):
        chapterData = {}

        for verse in range(verseCount):
            verseData = {}

            url = f'https://biblehub.com/interlinear/{bookName}/{chapter+1}-{verse+1}.htm'
            # note: we could do the whole chapter at once which would reduce requests and improve performance
            # there is no easy way to distinguish between the different verses in the chapter, though

            response = None
            while (response is None):
                try:
                    # GET webpage
                    response = requests.get(url, timeout=None)
                except urllib3.exceptions.ConnectTimeoutError:
                    response = None
                    print(f'Error: {url} timed out')
                    time.sleep(20)

            # PARSE
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            # tables
            root = soup.find('div', {'class': 'padleft'})

            if (root is not None):
                tables = root.find_all('table')
                tokenCount = 1
                for table in tables:

                    token: dict = {}

                    cells = table.find_all('span')
                    for cell in cells: # token

                        if (cell.attrs.get('class') is None):
                            continue # LUK.1
                        for cellClass in cell.attrs.get('class'):
                            # strongs   Strongs number of Hebrew word
                            # pos       Strongs number of Greek word

                            # hebrew    Hebrew (or Aramaic) word
                            # greek     Greek word

                            # translit  transliteration of word
                            # eng       translation of word

                            # strongsnt(2) # see https://biblehub.com/hebrewparse.htm and https://biblehub.com/grammar/greek.htm
                                # Prep-b    Preposition-b
                                # |
                                # N         Noun
                                # -
                                # f         feminine
                                # s         singular

                            # ref...    verse number (ignorable)

                            metadata = None

                            # unify Hebrew and Greek classes
                            if (cellClass in ['hebrew', 'greek']):
                                cellClass = 'native'

                            data = cell.text.strip()
                            data = unicodedata.normalize('NFKD', data)

                            if (cellClass == 'punct'):
                                token['punct'] = data
                                continue

                            # PRIMARY DATA
                            if (cellClass in ['strongs', 'pos', 'eng', 'native', 'translit']): # data we want to process

                                # rename classes
                                if (cellClass in ['strongs', 'pos'] and data != '[e]'):
                                    # STRONGS NUMBER AND DESCRIPTION
                                    data = f'H{data}' if (cellClass == 'strongs') else f'G{data}'
                                    cellClass = 'strongs'
                                    # additional information stored in title
                                    href = cell.find('a')
                                    if (href):
                                        href = href.attrs.get('title')
                                        if (href):
                                            metadata = href.split('=')[-1]

                                # PROCESS DATA
                                if (data != '[e]'):
                                    if (metadata):
                                        token[cellClass] = {
                                            'data': data,
                                            'metadata': metadata,
                                        }
                                    else:
                                        token[cellClass] = data

                            # GRAMAMR PARSING
                            elif (cellClass in ['strongsnt', 'strongsnt2']):

                                language = 'hebrew' if cellClass == 'strongsnt' else 'greek'

                                metadata = None
                                if (data != '[e]'):
                                    # additional information stored in title
                                    href = cell.find('a')
                                    if (href):
                                        href = href.attrs.get('title')
                                        if (href):
                                            metadata = href.split('=')[-1]

                                    if (metadata):

                                        longSplit = r'::|,' if language == 'hebrew' else '-'
                                        shortSplit = r'\||,' if language == 'hebrew' else '-'

                                        def parseGrammar(string, split):

                                            if (isinstance(string, str)):
                                                res = re.split(split, string)
                                                for i, s in enumerate(res):
                                                    for newSplit in ['-', '\u2010']:
                                                        if (newSplit in s):
                                                            res[i] = parseGrammar(s, newSplit)

                                                    if (isinstance(res[i], str)):
                                                        res[i] = s.strip()
                                                return res
                                            return None

                                        # parse string to object
                                        grammarLong = parseGrammar(metadata, longSplit)
                                        gramamrShort = parseGrammar(data, shortSplit)

                                        token['grammar'] = []

                                        # map
                                        if (language == 'hebrew'):
                                            # HEBREW
                                            for posIndex, pos in enumerate(gramamrShort):

                                                if (isinstance(pos, str)):
                                                    tag = pos
                                                else:
                                                    tag = pos[0]
                                                if (isinstance(grammarLong[posIndex], str)):
                                                    name = grammarLong[posIndex]
                                                else:
                                                    name = grammarLong[posIndex][0]

                                                obj = {
                                                    'pos': name.lower()
                                                }
                                                if (isinstance(pos, list)):
                                                    obj['attributes'] = []
                                                    for componentIndex, component in enumerate(pos[1:]):
                                                        obj['attributes'].append(grammarLong[posIndex][1:][componentIndex])
                                                token['grammar'].append(obj)

                                        elif (language == 'greek'):
                                            # GREEK
                                            tag = gramamrShort[0]
                                            obj = {
                                                'pos': grammarLong[0].lower()
                                            }
                                            if (len(gramamrShort) > 1):
                                                obj['attributes'] = []
                                                for posIndex, pos in enumerate(gramamrShort[1:]):
                                                    obj['attributes'].append(grammarLong[1:][posIndex])
                                            token['grammar'].append(obj)

                    if (token.get('strongs')):
                        if (not token.get('grammar')):
                            if (len(token['strongs']) == 1): # GEN.4.22
                                token['strongs'] = { 'data': None }
                            else:
                                pass # error
                            pass
                        # print(token)
                        verseData[str(tokenCount)] = token
                        tokenCount += 1
                    else:
                        if (token):
                            pass

            # handle verseData
            chapterData[verse + 1] = verseData

            pass # verse
            # break
        pass

        # output
        outJSON = json.dumps(chapterData, indent=4, ensure_ascii=False).encode('utf-8')
        outDir = os.path.join(os.path.dirname(__file__), 'dist', 'bin', 'strongs', 'Interlinear', f'{book["usfm"]}.{chapter + 1}')
        if not os.path.exists(os.path.dirname(outDir)):
            os.makedirs(os.path.dirname(outDir))
        with open(outDir, 'w', encoding='utf-8') as f:
            f.write(outJSON.decode())
        pass

        # reformat file (condensed)
        # with open(outDir, 'r', encoding='utf-8') as f:
        #     temp = f.read()
        # temp = re.sub(re.compile(r'\n            '), ' ', temp)
        # temp = re.sub(re.compile(r'\n        },'), ' },', temp)
        # with open(outDir, 'w', encoding='utf-8') as f:
        #     f.write(temp)

        print(f'\t{chapter+1}')
        pass # chapter
        # break

    pass # book
    # break

print('done :D')

timeTaken = time.time() - startTime
if (timeTaken > 3600):
    print(f'--- {timeTaken / 3600} hours ---')
elif (timeTaken > 60):
    print(f'--- {timeTaken / 60} minutes ---')
else:
    print(f'--- {timeTaken} seconds ---')

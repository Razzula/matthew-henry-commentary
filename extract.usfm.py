# pylint: disable=fixme, line-too-long, invalid-name, superfluous-parens, trailing-whitespace, arguments-differ
"""TODO"""
import os
import re
import json
from pathlib import Path
import string
import subprocess

from usfm_grammar import USFMParser, Filter

encouneredMarkers = set()

def parseUSJStructure(usfmData):

    bookData = {}

    currentChapter = None
    chapterData = {}

    currentVerse = None
    verseData = []

    newParagraph = False

    strongsChapter = {}
    strongsVerse = {}

    for line in usfmData:
        if (line['marker'] in ['id', 'ide', 'h', 'toc1', 'toc2', 'toc3', 'mt1']):
            continue

        if (line['marker'] == 'c'):
            # CHAPTER
            if (currentVerse is not None and verseData):
                chapterData[currentVerse] = verseData
                verseData = []
            if (currentChapter is not None and chapterData):
                bookData[currentChapter] = chapterData
                chapterData = {}
            currentChapter = line['number']

            # load strongs data
            with open(os.path.abspath(os.path.join(rootDir, 'dist', 'strongs', f'{usfmData[0]["code"]}.{currentChapter}.json')), 'r', encoding='utf-8') as f:
                strongsChapter = json.load(f)
            continue

        elif (line['marker'] == 'p'):
            # PARAGRAPH
            paragraph = line['content']
            newParagraph = True
            for entry in paragraph:
                if (isinstance(entry, str)):
                    # regular token
                    verseData.append({ 'content': entry })
                    if (newParagraph):
                        verseData[-1]['type'] = 'p'
                    pass

                elif (entry['marker'] == 'v'):
                    # VERSE
                    if (currentVerse is not None and verseData):
                        # assign data to strongs
                        if (strongsVerse):
                            for index, item in enumerate(verseData):
                                if ((strong := item.get('strongs')) and (len(strongsVerse.get(strong, [])) == 1)):
                                    verseData[index]['token'] = strongsVerse[strong][0]
                        # save data
                        chapterData[currentVerse] = verseData
                        verseData = []
                    currentVerse = entry['number']

                    strongsVerse = {}
                    try:
                        for key, item in strongsChapter[currentVerse].items():
                            if ((not isinstance(item['strongs'], str)) and (strongsNumber := item['strongs']['data'])):
                                tokens = strongsVerse.get(strongsNumber, [])
                                tokens.append(key)
                                strongsVerse[strongsNumber] = tokens
                    except KeyError:
                        # there are some cases where the strongs data is missing
                        # Romans 16:25-27 (TR) = Romans 14:24-26
                        print(f'\t missing strongs data... ({currentChapter}:{currentVerse})')
                        pass
                    continue

                elif (entry['marker'] in ['f', 'x']):
                    # FOOTNOTE / CROSS-REFERENCE
                    # for the time being, we should just flatten this as plaintext
                    noteContents = flattenUSJToString(entry['content'][1:], '')
                    verseData.append({ 'type': 'note', 'content': noteContents })
                    continue

                else:
                    # TOKEN
                    tags = [] if (entry['marker'] == 'w') else [entry['marker']]
                    if (tags):
                        encouneredMarkers.add(entry['marker'])
                        pass
                    parseUSJEntry(entry, verseData, tags, newParagraph)
                    pass

                newParagraph = False

    if (currentVerse is not None and verseData):
        chapterData[currentVerse] = verseData
        verseData = []
    if (currentChapter is not None and chapterData):
        bookData[currentChapter] = chapterData
        chapterData = {}

    return bookData

def parseUSJEntry(usfmData, dataList, currentTags=None, newParagraph=False):
    """Recursviely fetch each leaf node in the USJ data structure and add them to a flat list."""
    if (currentTags is None):
        currentTags = []

    for entry in usfmData['content']:
        if (isinstance(entry, str)):
            # regular token
            token = newToken(entry, currentTags, newParagraph)
            if (usfmData.get('strong') is not None):
                token['strongs'] = usfmData['strong']
            dataList.append(token)
            pass

        elif (entry['marker'] == 'w'):
            # CHAR
            if (len(entry['content']) > 1):
                pass  # impossible?

            token = newToken(entry['content'][0], currentTags, newParagraph)
            if (entry.get('strong') is not None):
                token['strongs'] = entry['strong']
            dataList.append(token)
            pass

        else:
            # nested token
            newTags = list(set(currentTags.copy()))
            parseUSJEntry(entry, dataList, newTags, newParagraph)

        newParagraph = False


def flattenUSJToString(entry, string):
    for subentry in entry:
        if (isinstance(subentry, str)):
            string += subentry
        else:
            string = flattenUSJToString(subentry['content'], string)
    return string


def parseTokens(inputText, newParagraph=False, count=0, tags=None):
    """TODO"""
    if (tags is None):
        tags = []

    tokens = []
    PATTERN = r'\\w\*?\s*(?!\w)'
    # print(PATTERN.format(count))
    if (count > 0):
        # print(r'\\(\+{{{0}}})'.format(count))
        inputText = re.sub(r'\\(\+{{{0}}})'.format(count), r'\\', inputText)
        pass

    words = re.split(PATTERN.format(count), inputText)
    for word in words:
        word = word.strip()
        if (not word):
            continue

        token = {}
        tempTags = tags.copy()

        # process token
        if ('\\wj' in word):
            # everything in this 'word' is actually multiple words, with special formatting
            newInput = ''
            pre, data, post = re.split(r'\\wj\*?', word)

            tempTags.append('wj')
            newTokens = parseTokens(data, count=count+1, tags=tempTags)

            if (pre.strip()):
                tokens.append(newToken(pre.strip(), tempTags, newParagraph))
            if (newTokens):
                tokens.extend(newTokens)
            if (post.strip()):
                tokens.append(newToken(post.strip(), tempTags, newParagraph))
        elif ('|strong="' in word):
            word, strong = word.split('|strong="')
            token = newToken(word, tempTags)
            token['strongs'] = strong.rstrip(r'"\w*')
        elif (word.startswith('\\f')):
            data = re.findall(r'\\ft (.*)\\ft?\*', word)
            data = re.sub(r'\\\+?wh\s?\*?', '', data[0])
            token = newToken(data, tempTags, newParagraph)
        else:
            token = newToken(word, tempTags, newParagraph)

        tokens.append(token)
        newParagraph = False
    return tokens

def newToken(word, tags=None, newParagraph=False):
    if (tags is None):
        tempTags = []
    else:
        tempTags = tags.copy()

    token = {}
    token['content'] = word

    if (all(char in string.punctuation for char in word)):
        tempTags.append('punctuation')
    if (newParagraph):
        tempTags.append('p')

    if (tempTags):
        token['type'] = ' '.join(list(set(tempTags)))
    return token

def convertToJSON(inputDir, fileName, translation):
    """TODO"""
    print(fileName)

    with open(os.path.join(inputDir, fileName), 'r', encoding='utf-8') as f:
        usfmText = f.read()

    try:
        usfmData = USFMParser(usfmText).to_usj()
    except Exception as e:
        print('\terror parsing USFM file, ignoring errors...')
        usfmData = USFMParser(usfmText).to_usj(ignore_errors=True)

    chapters = parseUSJStructure(usfmData['content'])
    pass
    bookName = fileName.split('.')[0]
    pass

    for chapter, verses in chapters.items():
        jsonPath = os.path.join(rootDir, 'dist', 'bin', translation, f'{bookName}.{chapter}')
        if (os.path.exists(os.path.dirname(jsonPath)) is False):
            os.makedirs(os.path.dirname(jsonPath))
        with open(jsonPath, 'w', encoding='utf-8') as jsonFile:
            json.dump(verses, jsonFile, ensure_ascii=False, indent=4)

        # reformat file (condensed)
        with open(jsonPath, 'r', encoding='utf-8') as f:
            temp = f.read()
        temp = re.sub(re.compile(r'\n            '), ' ', temp)
        temp = re.sub(re.compile(r'\n        },'), ' },', temp)
        temp = re.sub(re.compile(r'\n        }'), ' }', temp)
        with open(jsonPath, 'w', encoding='utf-8') as f:
            f.write(temp)


translation = 'WEBBE'
rootDir = os.path.join(os.path.dirname(os.path.abspath(__file__)))

if (__name__ == '__main__'):

    inputDir = os.path.join(rootDir, 'src', translation)

    # convertToJSON(inputDir, 'JUD.usfm', translation)

    for file in os.listdir(inputDir):
        if (file.endswith('.usfm')):
            # if (file <= 'REV.usfm'): # TEMP
            #     continue
            convertToJSON(inputDir, file, translation)

    print(encouneredMarkers)

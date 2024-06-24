# pylint: disable=fixme, line-too-long, invalid-name, superfluous-parens, trailing-whitespace, arguments-differ
"""TODO"""
import json
import os
import time
from typing import Any
import unicodedata

import requests
from bs4 import BeautifulSoup
import urllib3

import src.strongs.greek as greek
import src.strongs.hebrew as hebrew

rootDir = os.path.join(os.path.dirname(os.path.abspath(__file__)))

URL_BLB = 'https://www.blueletterbible.org/lexicon/{}/kjv/wlc/0-1/'
URL_BH = 'https://biblehub.com/{}/{}.htm'

concordance: Any = {}
occurences: Any = {}

with open(os.path.join(rootDir, 'src', 'manifest.json'), 'r', encoding='utf-8') as f:
    books = json.load(f)

# PASSAGES
passageDir = os.path.join(rootDir, 'dist', 'strongs', 'Interlinear')
fileList = os.listdir(passageDir)
for book in books:
    for file in fileList:
        if (os.path.isfile(os.path.join(passageDir, file)) and file.startswith(book['usfm'])):
            with open(os.path.join(passageDir, file), 'r', encoding='utf-8') as f:
                chapter = json.load(f)
            for verseNumber, verse in chapter.items():
                for token, word in verse.items():
                    if ((number := word.get('strongs'))):
                        if (not isinstance(number, str)):
                            number = number['data']

                            ref = f'{file}.{verseNumber}.{token}'
                            if (occurences.get(number)):
                                occurences[number].append(ref)
                            else:
                                occurences[number] = [ref]
                            pass
pass

# STRONGS
for language, numbers in [('hebrew', hebrew.hebrew), ('greek', greek.greek)]:

    for strong in numbers:
        print(strong)

        token: Any = {
            'native': None,
            'translit': {},
            'pronunce': None,
            'pos': None,
            'derive': None,
            'define': None,
            'occurences': []
        }

        # GET
        url = URL_BLB.format(strong)
        response = None
        while (response is None):
            try:
                # GET webpage
                response = requests.get(url, timeout=None)
            except urllib3.exceptions.ConnectTimeoutError:
                response = None
                print(f'Error: {url} timed out')
                time.sleep(20)
        response.encoding = 'utf-8'
        soupBLB = BeautifulSoup(response.text, 'html.parser')

        url = URL_BH.format(language, strong[1:])
        response = None
        while (response is None):
            try:
                # GET webpage
                response = requests.get(url, timeout=None)
            except urllib3.exceptions.ConnectTimeoutError:
                response = None
                print(f'Error: {url} timed out')
                time.sleep(20)
        response.encoding = 'utf-8'
        soupBH = BeautifulSoup(response.text, 'html.parser')

        # PARSE
        data = soupBLB.find_all('div', {'class': 'lexicon-label'})
        if (data):
            for entry in data:
                # Transliteration
                if (entry.string == 'Transliteration'):
                    temp = entry.find_next('div', {'class': 'small-text-right'})
                    value = temp.text.strip()
                    value = unicodedata.normalize('NFKD', value)
                    token['translit']['org'] = value
                # Pronunciation
                elif (entry.string == 'Pronunciation'):
                    temp = entry.find_next('div', {'class': 'small-text-right'})
                    value = temp.text.split('\t')[0].strip()
                    value = unicodedata.normalize('NFKD', value)
                    token['pronunce'] = value
                # Part of Speech
                elif (entry.string == 'Part of Speech'):
                    temp = entry.find_next('div', {'class': 'small-text-right'})
                    value = temp.text.strip()
                    value = unicodedata.normalize('NFKD', value)
                    token['pos'] = value
                # Derivation
                elif (entry.string == 'Root Word (Etymology)'):
                    temp = entry.find_next('div')
                    value = temp.text.strip().lower()
                    value = unicodedata.normalize('NFKD', value)
                    token['derive'] = value
                # # Definition (Strong's)
                # elif (entry.string == 'Strong’s Definitions'):
                #     temp = entry.find_next('div')
                #     value = temp.text.strip().lower()
                #     value = unicodedata.normalize('NFKD', value)
                #     token['define'] = value
        data = soupBH.find_all('span', {'class': 'tophdg'})
        if (data):
            for entry in data:
                # Transliteration
                if (entry.string == 'Transliteration: '):
                    temp = entry.nextSibling
                    value = temp.text.strip()
                    value = unicodedata.normalize('NFKD', value)
                    token['translit']['ang'] = value
                # Native
                elif (entry.string == 'Original Word: '):
                    temp = entry.nextSibling
                    value = temp.text.strip()
                    value = unicodedata.normalize('NFKD', value)
                    token['native'] = value
        data = soupBH.find_all('div', {'class': 'vheading2'})
        if (data):
            for entry in data:
                # Definition (Strong's)
                if (entry.string == "Strong's Exhaustive Concordance"):
                    temp = entry.find_next('p').next_element
                    value = temp.text.strip().lower()
                    value = unicodedata.normalize('NFKD', value)
                    token['define'] = value

        # OCCURENCES
        if (occurences.get(strong)):
            token['occurences'] = occurences[strong]

        concordance[strong] = token
        pass
pass

with open(os.path.join(rootDir, 'dist', 'strongs', 'strongs.json'), 'w', encoding='utf-8') as f:
    json.dump(concordance, f, ensure_ascii=False, indent=4)

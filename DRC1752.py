# pylint: disable=fixme, line-too-long, invalid-name, superfluous-parens, trailing-whitespace, arguments-differ, annotation-unchecked, missing-function-docstring
import json
import os
import re
import requests
import inflect
from bs4 import BeautifulSoup

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DOUAY_RHEIMS = "https://www.sacredbible.org/challoner/index.htm"


def get_soup(url):
    response = requests.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


def extract_content(content_section, section_name=None):
    for a in content_section.find_all("a"):
        a.unwrap()  # Remove a tags but keep the text
    return (
        str(content_section)
        if section_name is None
        else f"<h2>{section_name}</h2>" + str(content_section)
    )


def save_html(dirName, fileName, sections, ignoreHr=False):
    book_dir = os.path.join(ROOT_DIR, "dist", 'bin', dirName)
    os.makedirs(book_dir, exist_ok=True)
    chapter_file = os.path.join(book_dir, f"{fileName}.html")

    out = ''
    for index, section in enumerate(sections):
        out += section
        if index < len(sections) - 1 and not ignoreHr:
            out += "<hr>"  # Add an hr tag between sections

    soup = BeautifulSoup(out, "html.parser")
    prettyOut = soup.prettify()
    with open(chapter_file, "w", encoding="utf-8") as f:
        f.write(prettyOut)

    print(f"Saved {fileName}")


def number_to_words(number):
    p = inflect.engine()
    return p.number_to_words(number)


def roman_to_number(match):
    book, roman, verse = match.groups()
    roman = roman.upper()
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    number = 0
    for index, value in enumerate(roman):
        if (
            index + 1 < len(roman) and values[value] < values[roman[index + 1]]
        ):  # if current item is not the last item on the string
            # and current item's value is smaller than next item's value
            number = (
                number - values[value]
            )  # then subtract current item's value from result
        else:
            number = (
                number + values[value]
            )  # otherwise add current item's value to result

    return f"{book} {number}:{verse}"


def roman_to_number2(match):
    book, roman = match.groups()
    roman = roman.upper()
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    number = 0
    for index, value in enumerate(roman):
        if (
            index + 1 < len(roman) and values[value] < values[roman[index + 1]]
        ):  # if current item is not the last item on the string
            # and current item's value is smaller than next item's value
            number = (
                number - values[value]
            )  # then subtract current item's value from result
        else:
            number = (
                number + values[value]
            )  # otherwise add current item's value to result

    return f"{book} {number}"

usfms = {
    '17': 'TOB',
    '18': 'JDT',
    '19': 'EST',
    '25': 'WIS',
    '26': 'SIR',
    '30': 'BAR',
    '32': 'DAN',
    '45': '1MA',
    '46': '2MA'
}

def main():
    # Getting the list of books from the Douay-Rheims Bible
    soup = get_soup(DOUAY_RHEIMS)
    books = soup.find_all("a", href=True, text=True)

    for book in books:
        if not book["href"].startswith("OT"):
            continue
        book_number = book["href"].split("OT-")[1].split("_")[0]
        if (book_number not in usfms.keys()): # apocrypha
            continue

        book_name = book.text.strip()
        book_usfm = usfms[book_number]
        book_url = f"https://www.sacredbible.org/challoner/{book['href']}"
        book_soup = get_soup(book_url)

        if (book_usfm in ['DAN', 'EST']):
            book_name = f'Additions to {book_name}'

        # Extract book introduction

        lines = book_soup.get_text().split('\n')

        # Extract chapters
        chapters = {}

        for line in lines:
            if not line.startswith('{'):
                continue
            line = line.strip()
            pattern = r"\{(\d+:\d+)\} (.+)"
            match = re.search(pattern, line)
            if (match):
                meta, data = match.groups()
                chapter, verse = meta.split(':')

                if (book_usfm == 'DAN'):
                    if (chapter not in ['3', '13', '14']):
                        continue # canonical
                    if (chapter == '3' and (int(verse) < 24 or int(verse) > 90)):
                        continue
                elif (book_usfm == 'EST'):
                    if (int(chapter) < 10):
                        continue # canoncial
                    if (chapter == '10' and (int(verse) < 4)):
                        continue

                if (chapters.get(chapter) is None):
                    chapters[chapter] = {}
                if (chapters[chapter].get(verse) is None):
                    chapters[chapter][verse] = []

                chapters[chapter][verse].append({ 'type': 'p', 'content': data })


        rootOutDir = os.path.join('bin', f'{book_number}.{book_usfm}')
        if not os.path.exists(rootOutDir):
            os.makedirs(rootOutDir)
        with open(os.path.join(rootOutDir, 'manifest.json'), 'w') as f:
            f.write(json.dumps({
                "title": book_name,
                "landing": f"{book_usfm}.0.html",
                "children": "usfm-chapter",
                "format": "passage",
                "usfm": book_usfm
            }, indent=4))

        with open(os.path.join(rootOutDir, f'{book_usfm}.0.html'), 'w') as f:
            f.write(f'<p>{book_name} (TODO!)</p>')

        for chapterNumber, chapterData in chapters.items():

            if (book_usfm == 'DAN'):
                if (chapterNumber == '3'):
                    chapterData['disclaimer'] = 'These verses are an insertion inbetween Daniel 3:23 and Daniel 3:24. They are not found in the Hebrew or Aramaic texts, but are found in the Greek Septuagint and the Latin Vulgate.'
                else:
                    chapterData['disclaimer'] = 'This chapter is an addition to the book of Daniel. It is not found in the Hebrew or Aramaic texts, but are found in the Greek Septuagint and the Latin Vulgate.'
            elif (book_usfm == 'EST'):
                if (chapterNumber == '10'):
                    chapterData['disclaimer'] = 'These verses are an insertion at the end of Esther. They are not found in the Hebrew or Aramaic texts, but are found in the Greek Septuagint and the Latin Vulgate.'
                else:
                    chapterData['disclaimer'] = 'This chapter is an addition to the book of Esther. It is not found in the Hebrew or Aramaic texts, but are found in the Greek Septuagint and the Latin Vulgate.'
            else:
                chapterData['disclaimer'] = 'This book is an addition to the Old Testament. It is not found in the Hebrew or Aramaic texts, but are found in the Greek Septuagint and the Latin Vulgate.'

            # OUT
            outJSON = json.dumps(chapterData, indent=4)
            outDir = os.path.join(rootOutDir, f'{book_usfm}.{chapterNumber}.json')
            print(f'{book_usfm}.{chapterNumber}')
            with open(outDir, 'w') as f:
                f.write(outJSON)
            pass

            # reformat file (condensed)
            with open(outDir, 'r') as f:
                temp = f.read()
            temp = re.sub(re.compile(r'\n            '), ' ', temp)
            temp = re.sub(re.compile(r'\n        },'), ' },', temp)
            temp = re.sub(re.compile(r'\n        }'), ' }', temp)
            with open(outDir, 'w') as f:
                f.write(temp)
            pass

if __name__ == "__main__":
    main()

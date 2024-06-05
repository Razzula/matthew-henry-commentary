# pylint: disable=fixme, line-too-long, invalid-name, superfluous-parens, trailing-whitespace, arguments-differ, annotation-unchecked, missing-function-docstring
import json
import os
import re
import requests
import inflect
from bs4 import BeautifulSoup

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BIBLE_GATEWAY = "https://www.biblegateway.com"


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


def main():

    with open("src/books.json", "r", encoding="utf-8") as f:
        usfms = json.load(f)

    # PREFACES
    for i in range(6):
        numerals = ["I", "II", "III", "IV", "V", "VI"]
        soup = get_soup(f"https://www.ccel.org/h/henry/mhc2/MHC0000{1}.HTM")
        paragraphs = [
            f"<center><h1>VOLUME {numerals[i]}</h1></center>" + str(soup.find("center"))
        ]
        paras = soup.find_all("p")
        for para in paras:
            para = extract_content(para)

            pattern = re.compile(
                r"(\w+\.?) M{0,3}((?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))\.\s*(\d+)\b",
                re.IGNORECASE,
            )
            para = re.sub(pattern, roman_to_number, para)

            pattern = re.compile(
                r"(\w+\.?) M{0,3}((?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))\.",
                re.IGNORECASE,
            )
            para = re.sub(pattern, roman_to_number2, para)

            paragraphs.append(para)
        save_html(f"VOL.{i+1}", "preface", paragraphs, ignoreHr=True)

    # BIBLE GATEWAY
    soup = get_soup(f"{BIBLE_GATEWAY}/resources/matthew-henry/toc")
    soup = soup.find("div", {"class": "exbib-content"})

    books = soup.find_all("a", href=True, text=True)
    for book in books:

        book_soup = get_soup(f'{BIBLE_GATEWAY}{book["href"]}')
        book_soup = book_soup.find("div", {"class": "exbib-content"})
        book_name = book.text
        book_usfm = None
        book_number = None
        for index, usfm in enumerate(usfms):
            if book_name.upper().replace(' ', '') in usfm:
                book_usfm = usfm[0]
                book_number = f"0{index+1}" if index < 9 else index+1
                break
        print(book_usfm)

        book_intro = book_soup.find("div", {"class": "article introduction"})
        pref_soup = get_soup(
            f"https://www.ccel.org/h/henry/mhc2/MHC{book_number}000.HTM"
        )
        pref_soup = pref_soup.find_all("center")[1]
        save_html(f'{book_number}.{book_usfm}', f'{book_usfm}.0', [str(pref_soup) + extract_content(book_intro)])

        chapters = book_soup.find_all("a", href=True, text=True)

        for chapter in chapters:
            if (
                "/resources/matthew-henry/" not in chapter["href"]
                or "Chapter" not in chapter.text
            ):
                continue
            chapter_name = f"{book_name} {chapter.text.split()[-1]}"
            chapter_title = (
                f"CHAPTER {number_to_words(int(chapter.text.split()[-1]))}".upper()
            )

            chapter_usfm = f"{book_usfm}.{chapter.text.split()[-1]}"
            chapter_url = f"{BIBLE_GATEWAY}{chapter['href']}"
            chapter_soup = get_soup(chapter_url)
            chapter_soup = chapter_soup.find("div", {"class": "exbib-content"})

            sections_content = []

            # INTRO
            chapter_intro = chapter_soup.find("div", {"class": "article"})
            fancy_book_name = ''
            for char in book_name:
                fancy_book_name += f'{char.upper()}'
            sections_content.append(
                f'<center><br><font size="+3"><b>{fancy_book_name}</b></font><br><br><font size="+2">{chapter_title}.</font><hr size="1" width="50"></center>'
                + extract_content(chapter_intro)
            )

            # MANIFEST
            manifest = {
                "title": book_name,
                "landing": f"{book_usfm}.0.html",
                "children": "usfm-chapter",
                "usfm": book_usfm,
            }
            with open(os.path.join(ROOT_DIR, 'dist', 'bin', f'{book_number}.{book_usfm}', 'manifest.json'), "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=4)

            # SECTIONS
            section_links = chapter_soup.find_all("a", href=True, text=True)

            for section in section_links:
                if (
                    "/resources/matthew-henry/" not in section["href"]
                    or "Verse" not in section.text
                ):
                    continue
                section_url = f"{BIBLE_GATEWAY}{section['href']}"
                section_name = f"{chapter_name}:{section.text.split()[-1]}"
                section_soup = get_soup(section_url)
                content_section = section_soup.find("div", {"class": "exbib-content"})
                sections_content.append(extract_content(content_section, section_name))

            save_html(f'{book_number}.{book_usfm}', chapter_usfm, sections_content)
            # break
        # break


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Parse OpenGNT data to extract Greek text with English glosses."""

import re
from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
OPENGNT_FILENAME = "OpenGNT_keyedFeatures.csv"

# NT book name to number mapping (using traditional numbering where Matthew = 40)
BOOK_NAMES = {
    "matthew": 40, "matt": 40, "mt": 40,
    "mark": 41, "mk": 41,
    "luke": 42, "lk": 42,
    "john": 43, "jn": 43,
    "acts": 44,
    "romans": 45, "rom": 45,
    "1corinthians": 46, "1cor": 46, "1 corinthians": 46,
    "2corinthians": 47, "2cor": 47, "2 corinthians": 47,
    "galatians": 48, "gal": 48,
    "ephesians": 49, "eph": 49,
    "philippians": 50, "phil": 50,
    "colossians": 51, "col": 51,
    "1thessalonians": 52, "1thess": 52, "1 thessalonians": 52,
    "2thessalonians": 53, "2thess": 53, "2 thessalonians": 53,
    "1timothy": 54, "1tim": 54, "1 timothy": 54,
    "2timothy": 55, "2tim": 55, "2 timothy": 55,
    "titus": 56,
    "philemon": 57, "phlm": 57,
    "hebrews": 58, "heb": 58,
    "james": 59, "jas": 59,
    "1peter": 60, "1pet": 60, "1 peter": 60,
    "2peter": 61, "2pet": 61, "2 peter": 61,
    "1john": 62, "1jn": 62, "1 john": 62,
    "2john": 63, "2jn": 63, "2 john": 63,
    "3john": 64, "3jn": 64, "3 john": 64,
    "jude": 65,
    "revelation": 66, "rev": 66,
}

# Reverse mapping for display
BOOK_NUMBERS = {
    40: "Matthew", 41: "Mark", 42: "Luke", 43: "John", 44: "Acts",
    45: "Romans", 46: "1 Corinthians", 47: "2 Corinthians", 48: "Galatians",
    49: "Ephesians", 50: "Philippians", 51: "Colossians",
    52: "1 Thessalonians", 53: "2 Thessalonians", 54: "1 Timothy",
    55: "2 Timothy", 56: "Titus", 57: "Philemon", 58: "Hebrews",
    59: "James", 60: "1 Peter", 61: "2 Peter", 62: "1 John",
    63: "2 John", 64: "3 John", 65: "Jude", 66: "Revelation",
}


def parse_passage_reference(ref: str) -> dict:
    """Parse a passage reference into components.

    Supports:
    - Full book: "Ephesians"
    - Single chapter: "Ephesians 1"
    - Verse range: "John 1:1-18"
    - Single verse: "John 1:1"

    Returns:
        Dictionary with book_num, and optionally chapter/verse info
    """
    ref = ref.strip()

    # Try pattern: "Book Chapter:StartVerse-EndVerse"
    pattern_verse_range = r"^(.+?)\s+(\d+):(\d+)-(\d+)$"
    match = re.match(pattern_verse_range, ref)
    if match:
        book_name = match.group(1).lower().replace(" ", "")
        book_num = BOOK_NAMES.get(book_name)
        if book_num is None:
            raise ValueError(f"Unknown book: {match.group(1)}")
        return {
            "book_num": book_num,
            "type": "verse_range",
            "chapter": int(match.group(2)),
            "start_verse": int(match.group(3)),
            "end_verse": int(match.group(4))
        }

    # Try pattern: "Book Chapter:Verse"
    pattern_single_verse = r"^(.+?)\s+(\d+):(\d+)$"
    match = re.match(pattern_single_verse, ref)
    if match:
        book_name = match.group(1).lower().replace(" ", "")
        book_num = BOOK_NAMES.get(book_name)
        if book_num is None:
            raise ValueError(f"Unknown book: {match.group(1)}")
        return {
            "book_num": book_num,
            "type": "verse_range",
            "chapter": int(match.group(2)),
            "start_verse": int(match.group(3)),
            "end_verse": int(match.group(3))
        }

    # Try pattern: "Book Chapter"
    pattern_chapter = r"^(.+?)\s+(\d+)$"
    match = re.match(pattern_chapter, ref)
    if match:
        book_name = match.group(1).lower().replace(" ", "")
        book_num = BOOK_NAMES.get(book_name)
        if book_num is None:
            raise ValueError(f"Unknown book: {match.group(1)}")
        return {
            "book_num": book_num,
            "type": "chapter",
            "chapter": int(match.group(2))
        }

    # Try pattern: just "Book"
    book_name = ref.lower().replace(" ", "")
    book_num = BOOK_NAMES.get(book_name)
    if book_num is not None:
        return {
            "book_num": book_num,
            "type": "book"
        }

    raise ValueError(f"Invalid passage reference: {ref}")


def load_opengnt_data(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """Load the OpenGNT CSV data."""
    if csv_path is None:
        csv_path = DATA_DIR / OPENGNT_FILENAME

    if not csv_path.exists():
        raise FileNotFoundError(
            f"OpenGNT data not found at {csv_path}. "
            "Run 'python -m src.download_data' first."
        )

    # OpenGNT CSV uses tab separator
    df = pd.read_csv(csv_path, sep='\t', low_memory=False)
    return df


def extract_greek_word(tantt_cell: str) -> str:
    """Extract Greek word from TANTT column."""
    if not tantt_cell or pd.isna(tantt_cell):
        return ""

    content = tantt_cell.strip('〔〕')
    parts = content.split('=')
    if len(parts) >= 2:
        return parts[1].strip()

    return ""


def extract_strongs_number(tantt_cell: str) -> str:
    """Extract Strong's number from TANTT column.

    Format: 〔BIMNRSTWH=Βίβλος=G0976=N-NSF;〕
    Returns: G976 (normalized without leading zeros after G)
    """
    if not tantt_cell or pd.isna(tantt_cell):
        return ""

    content = tantt_cell.strip('〔〕')
    # Look for G followed by digits
    match = re.search(r'(G\d+)', content)
    if match:
        strongs = match.group(1)
        # Normalize: G0976 -> G976
        return 'G' + str(int(strongs[1:]))

    return ""


def extract_gloss(gloss_cell: str) -> str:
    """Extract gloss from gloss column."""
    if not gloss_cell or pd.isna(gloss_cell):
        return ""

    content = gloss_cell.strip('〔〕')
    parts = content.split('｜')
    if len(parts) >= 3:
        gloss = parts[2].strip()
        if gloss:
            return gloss
    if parts:
        return parts[0].strip()

    return ""


def extract_book(book_num: int, df: pd.DataFrame) -> dict:
    """Extract all chapters and verses for a book."""
    ref_col = '〔book｜chapter｜verse〕'
    tantt_col = '〔TANTT〕'
    gloss_col = '〔MounceGloss｜TyndaleHouseGloss｜OpenGNTGloss〕'

    # Filter for this book
    book_pattern = f'〔{book_num}｜'
    book_data = df[df[ref_col].str.startswith(book_pattern)]

    if book_data.empty:
        return {"chapters": []}

    # Parse all references to get chapter/verse structure
    chapters = {}
    for _, row in book_data.iterrows():
        ref = row[ref_col]
        # Parse 〔49｜1｜1〕
        match = re.match(r'〔(\d+)｜(\d+)｜(\d+)〕', ref)
        if match:
            chapter = int(match.group(2))
            verse = int(match.group(3))

            if chapter not in chapters:
                chapters[chapter] = {}
            if verse not in chapters[chapter]:
                chapters[chapter][verse] = []

            greek_word = extract_greek_word(row[tantt_col])
            gloss = extract_gloss(row[gloss_col])
            strongs = extract_strongs_number(row[tantt_col])

            if greek_word and gloss:
                word_data = {
                    "greek": greek_word,
                    "gloss": gloss
                }
                if strongs:
                    word_data["strongs"] = strongs
                chapters[chapter][verse].append(word_data)

    # Convert to list format
    result_chapters = []
    for ch_num in sorted(chapters.keys()):
        verses = []
        for v_num in sorted(chapters[ch_num].keys()):
            if chapters[ch_num][v_num]:
                verses.append({
                    "verse": v_num,
                    "words": chapters[ch_num][v_num]
                })
        result_chapters.append({
            "chapter": ch_num,
            "verses": verses
        })

    return {"chapters": result_chapters}


def extract_chapter(book_num: int, chapter: int, df: pd.DataFrame) -> list:
    """Extract all verses for a chapter."""
    ref_col = '〔book｜chapter｜verse〕'
    tantt_col = '〔TANTT〕'
    gloss_col = '〔MounceGloss｜TyndaleHouseGloss｜OpenGNTGloss〕'

    # Filter for this chapter
    chapter_pattern = f'〔{book_num}｜{chapter}｜'
    chapter_data = df[df[ref_col].str.startswith(chapter_pattern)]

    verses = {}
    for _, row in chapter_data.iterrows():
        ref = row[ref_col]
        match = re.match(r'〔(\d+)｜(\d+)｜(\d+)〕', ref)
        if match:
            verse = int(match.group(3))
            if verse not in verses:
                verses[verse] = []

            greek_word = extract_greek_word(row[tantt_col])
            gloss = extract_gloss(row[gloss_col])
            strongs = extract_strongs_number(row[tantt_col])

            if greek_word and gloss:
                word_data = {
                    "greek": greek_word,
                    "gloss": gloss
                }
                if strongs:
                    word_data["strongs"] = strongs
                verses[verse].append(word_data)

    result = []
    for v_num in sorted(verses.keys()):
        if verses[v_num]:
            result.append({
                "verse": v_num,
                "words": verses[v_num]
            })

    return result


def extract_passage(passage_ref: str, df: Optional[pd.DataFrame] = None) -> dict:
    """Extract Greek words and glosses for a passage."""
    parsed = parse_passage_reference(passage_ref)
    book_num = parsed["book_num"]

    if df is None:
        df = load_opengnt_data()

    if parsed["type"] == "book":
        # Full book
        book_data = extract_book(book_num, df)
        return {
            "passage": passage_ref,
            "book": BOOK_NUMBERS[book_num],
            "type": "book",
            "chapters": book_data["chapters"]
        }

    elif parsed["type"] == "chapter":
        # Single chapter
        verses = extract_chapter(book_num, parsed["chapter"], df)
        return {
            "passage": passage_ref,
            "book": BOOK_NUMBERS[book_num],
            "type": "chapter",
            "chapter": parsed["chapter"],
            "verses": verses
        }

    else:
        # Verse range
        ref_col = '〔book｜chapter｜verse〕'
        tantt_col = '〔TANTT〕'
        gloss_col = '〔MounceGloss｜TyndaleHouseGloss｜OpenGNTGloss〕'

        chapter = parsed["chapter"]
        start_verse = parsed["start_verse"]
        end_verse = parsed["end_verse"]

        verses = []
        for verse_num in range(start_verse, end_verse + 1):
            pattern = f'〔{book_num}｜{chapter}｜{verse_num}〕'
            mask = df[ref_col] == pattern
            verse_data = df[mask]

            if verse_data.empty:
                continue

            words = []
            for _, row in verse_data.iterrows():
                greek_word = extract_greek_word(row[tantt_col])
                gloss = extract_gloss(row[gloss_col])
                strongs = extract_strongs_number(row[tantt_col])
                if greek_word and gloss:
                    word_data = {"greek": greek_word, "gloss": gloss}
                    if strongs:
                        word_data["strongs"] = strongs
                    words.append(word_data)

            if words:
                verses.append({"verse": verse_num, "words": words})

        return {
            "passage": passage_ref,
            "book": BOOK_NUMBERS[book_num],
            "type": "verse_range",
            "chapter": chapter,
            "start_verse": start_verse,
            "end_verse": end_verse,
            "verses": verses
        }


def load_greek_passage(passage_ref: str) -> dict:
    """Convenience function to load Greek passage data."""
    return extract_passage(passage_ref)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Extract Greek passage data")
    parser.add_argument("passage", help="Passage reference, e.g., 'John 1:1-18' or 'Ephesians'")
    parser.add_argument("--output", "-o", help="Output JSON file")
    args = parser.parse_args()

    result = load_greek_passage(args.passage)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Saved to {args.output}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""Fetch ESV Bible text from the ESV API."""

import re
import sys
from pathlib import Path

import requests

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import ESV_API_KEY
except ImportError:
    ESV_API_KEY = None

ESV_API_URL = "https://api.esv.org/v3/passage/text/"

# Book chapter counts for fetching full books
BOOK_CHAPTERS = {
    "Matthew": 28, "Mark": 16, "Luke": 24, "John": 21, "Acts": 28,
    "Romans": 16, "1 Corinthians": 16, "2 Corinthians": 13, "Galatians": 6,
    "Ephesians": 6, "Philippians": 4, "Colossians": 4,
    "1 Thessalonians": 5, "2 Thessalonians": 3, "1 Timothy": 6,
    "2 Timothy": 4, "Titus": 3, "Philemon": 1, "Hebrews": 13,
    "James": 5, "1 Peter": 5, "2 Peter": 3, "1 John": 5,
    "2 John": 1, "3 John": 1, "Jude": 1, "Revelation": 22,
}


def fetch_single_chapter(book: str, chapter: int, api_key: str) -> dict:
    """Fetch a single chapter from the ESV API."""
    passage_ref = f"{book} {chapter}"

    params = {
        "q": passage_ref,
        "include-verse-numbers": "true",
        "include-first-verse-numbers": "true",
        "include-footnotes": "false",
        "include-footnote-body": "false",
        "include-headings": "true",
        "include-short-copyright": "false",
        "include-passage-references": "false",
        "include-selahs": "true",
        "indent-paragraphs": "0",
        "indent-poetry": "false",
        "indent-declares": "0",
        "indent-psalm-doxology": "0",
        "line-length": "0",
    }

    headers = {"Authorization": f"Token {api_key}"}

    response = requests.get(ESV_API_URL, params=params, headers=headers)
    response.raise_for_status()

    data = response.json()

    if not data.get("passages"):
        return {"chapter": chapter, "verses": []}

    passage_text = data["passages"][0]
    verses = parse_esv_verses_with_headings(passage_text)

    return {"chapter": chapter, "verses": verses}


def fetch_esv_passage(passage_ref: str, api_key: str = None) -> dict:
    """Fetch ESV passage text from the API."""
    if api_key is None:
        api_key = ESV_API_KEY

    if not api_key or api_key == "your-api-key-here":
        raise ValueError(
            "ESV API key not configured. "
            "Copy config.py.example to config.py and add your API key."
        )

    passage_ref = passage_ref.strip()

    # Normalize book names
    book_name = None
    for book in BOOK_CHAPTERS.keys():
        if passage_ref.lower() == book.lower() or passage_ref.lower().replace(" ", "") == book.lower().replace(" ", ""):
            book_name = book
            break

    if book_name:
        # Fetch full book chapter by chapter
        print(f"   Fetching {BOOK_CHAPTERS[book_name]} chapters...")
        chapters = []
        for ch in range(1, BOOK_CHAPTERS[book_name] + 1):
            chapter_data = fetch_single_chapter(book_name, ch, api_key)
            chapters.append(chapter_data)
            print(f"      Chapter {ch}: {len(chapter_data['verses'])} verses")

        return {
            "passage": passage_ref,
            "canonical": book_name,
            "type": "book",
            "chapters": chapters
        }

    # Single passage request
    params = {
        "q": passage_ref,
        "include-verse-numbers": "true",
        "include-first-verse-numbers": "true",
        "include-footnotes": "false",
        "include-footnote-body": "false",
        "include-headings": "true",
        "include-short-copyright": "false",
        "include-passage-references": "false",
        "include-selahs": "true",
        "indent-paragraphs": "0",
        "indent-poetry": "false",
        "indent-declares": "0",
        "indent-psalm-doxology": "0",
        "line-length": "0",
    }

    headers = {"Authorization": f"Token {api_key}"}

    response = requests.get(ESV_API_URL, params=params, headers=headers)
    response.raise_for_status()

    data = response.json()

    if not data.get("passages"):
        raise ValueError(f"No passages returned for: {passage_ref}")

    passage_text = data["passages"][0]
    verses = parse_esv_verses_with_headings(passage_text)

    return {
        "passage": passage_ref,
        "canonical": data.get("canonical", passage_ref),
        "type": "verses",
        "verses": verses
    }


def is_likely_heading(text: str) -> bool:
    """Check if text looks like a section heading rather than verse content.

    Headings are short phrases without sentence-ending punctuation.
    Verse content typically ends with . : , ; ! ? or other punctuation.
    """
    if not text or len(text) > 80:
        return False

    # Verse content typically ends with punctuation
    verse_endings = '.,:;!?"\''
    if text[-1] in verse_endings:
        return False

    return True


def parse_esv_verses_with_headings(passage_text: str) -> list[dict]:
    """Parse ESV passage text into verses, extracting section headings.

    ESV API format with headings:
    - Headings appear on their own line before verses (not indented)
    - Headings are followed by blank lines
    - Headings don't end with sentence punctuation
    - Verse text may also appear after blank lines but ends with punctuation
    """
    verses = []
    text = passage_text.strip()

    # Find all verse markers and their positions
    verse_pattern = r'\[(\d+)\]'
    matches = list(re.finditer(verse_pattern, text))

    if not matches:
        return verses

    # Track current heading (applies to next verse)
    current_heading = None

    # Check for heading before first verse
    before_first = text[:matches[0].start()].strip()
    if before_first:
        lines = before_first.split('\n')
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            stripped = line.strip()
            if stripped:
                # Check if it looks like a heading
                if is_likely_heading(stripped):
                    current_heading = stripped
                break

    for i, match in enumerate(matches):
        verse_num = int(match.group(1))
        start_pos = match.end()

        # Find the end of this verse's text
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(text)

        # Get raw verse segment (may include trailing heading for next verse)
        segment = text[start_pos:end_pos]

        # Split segment to find verse text and any trailing heading
        lines = segment.split('\n')

        verse_lines = []
        trailing_heading = None
        blank_line_seen = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_line_seen = True
            elif blank_line_seen:
                # After a blank line - could be heading or verse continuation
                # Headings don't end with sentence punctuation
                if is_likely_heading(stripped):
                    # This is a heading for the next verse
                    trailing_heading = stripped
                else:
                    # Verse continuation (ends with punctuation)
                    verse_lines.append(stripped)
                    blank_line_seen = False  # Reset for potential later content
            else:
                # Before any blank line - definitely verse text
                verse_lines.append(stripped)

        # Build verse text
        verse_text = ' '.join(verse_lines)
        verse_text = re.sub(r'\s+', ' ', verse_text).strip()

        if verse_text:
            verse_data = {
                "verse": verse_num,
                "text": verse_text
            }
            if current_heading:
                verse_data["heading"] = current_heading
            verses.append(verse_data)

        # Set heading for next verse
        current_heading = trailing_heading

    return verses


def parse_esv_verses(passage_text: str) -> list[dict]:
    """Parse ESV passage text into individual verses."""
    return parse_esv_verses_with_headings(passage_text)


def fetch_esv_verses(passage_ref: str, api_key: str = None) -> dict:
    """Convenience function - alias for fetch_esv_passage."""
    return fetch_esv_passage(passage_ref, api_key)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Fetch ESV passage")
    parser.add_argument("passage", help="Passage reference, e.g., 'John 1:1-18' or 'Ephesians'")
    parser.add_argument("--api-key", help="ESV API key (overrides config.py)")
    parser.add_argument("--output", "-o", help="Output JSON file")
    args = parser.parse_args()

    try:
        result = fetch_esv_passage(args.passage, args.api_key)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Saved to {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.HTTPError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)

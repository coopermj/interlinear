#!/usr/bin/env python3
"""Fetch NET Bible text from the NET Bible API at labs.bible.org."""

import re
import requests

NET_API_URL = "https://labs.bible.org/api/"

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


def fetch_net_chapter(book: str, chapter: int) -> dict:
    """Fetch a single chapter from the NET Bible API."""
    passage_ref = f"{book} {chapter}"

    params = {
        "passage": passage_ref,
        "type": "json"
    }

    response = requests.get(NET_API_URL, params=params)
    response.raise_for_status()

    data = response.json()

    if not data:
        return {"chapter": chapter, "verses": []}

    verses = []
    for item in data:
        verse_num = int(item.get("verse", 0))
        text = item.get("text", "").strip()
        # Clean up NET-specific formatting
        text = re.sub(r'\s+', ' ', text)

        if verse_num and text:
            verses.append({
                "verse": verse_num,
                "text": text
            })

    return {"chapter": chapter, "verses": verses}


def fetch_net_passage(passage_ref: str) -> dict:
    """Fetch NET Bible passage text from the API."""
    passage_ref = passage_ref.strip()

    # Normalize book names
    book_name = None
    for book in BOOK_CHAPTERS.keys():
        if passage_ref.lower() == book.lower() or passage_ref.lower().replace(" ", "") == book.lower().replace(" ", ""):
            book_name = book
            break

    if book_name:
        # Fetch full book chapter by chapter
        print(f"   Fetching NET {BOOK_CHAPTERS[book_name]} chapters...")
        chapters = []
        for ch in range(1, BOOK_CHAPTERS[book_name] + 1):
            chapter_data = fetch_net_chapter(book_name, ch)
            chapters.append(chapter_data)
            print(f"      Chapter {ch}: {len(chapter_data['verses'])} verses")

        return {
            "passage": passage_ref,
            "canonical": book_name,
            "type": "book",
            "translation": "NET",
            "chapters": chapters
        }

    # Single passage request
    params = {
        "passage": passage_ref,
        "type": "json"
    }

    response = requests.get(NET_API_URL, params=params)
    response.raise_for_status()

    data = response.json()

    if not data:
        raise ValueError(f"No passages returned for: {passage_ref}")

    verses = []
    for item in data:
        verse_num = int(item.get("verse", 0))
        text = item.get("text", "").strip()
        text = re.sub(r'\s+', ' ', text)

        if verse_num and text:
            verses.append({
                "verse": verse_num,
                "text": text
            })

    return {
        "passage": passage_ref,
        "canonical": passage_ref,
        "type": "verses",
        "translation": "NET",
        "verses": verses
    }


if __name__ == "__main__":
    import json
    result = fetch_net_passage("Ephesians 1:1-3")
    print(json.dumps(result, indent=2))

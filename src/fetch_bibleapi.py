#!/usr/bin/env python3
"""Fetch Bible text from bible-api.com (supports multiple translations)."""

import re
import time
import requests

BIBLE_API_URL = "https://bible-api.com/"

# Available translations at bible-api.com
AVAILABLE_TRANSLATIONS = {
    "web": "World English Bible",
    "asv": "American Standard Version",
    "kjv": "King James Version",
    "bbe": "Bible in Basic English",
    "darby": "Darby Bible",
    "ylt": "Young's Literal Translation",
    "oeb-us": "Open English Bible (US)",
    "oeb-cw": "Open English Bible (Commonwealth)",
}

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


def fetch_chapter(book: str, chapter: int, translation: str = "web", retries: int = 3) -> dict:
    """Fetch a single chapter from bible-api.com."""
    passage_ref = f"{book} {chapter}"

    url = f"{BIBLE_API_URL}{passage_ref.replace(' ', '+')}?translation={translation}"

    for attempt in range(retries):
        response = requests.get(url)
        if response.status_code == 429:
            # Rate limited - wait and retry
            wait_time = 5 * (attempt + 1)  # 5, 10, 15 seconds
            print(f"      Rate limited, waiting {wait_time}s...")
            time.sleep(wait_time)
            continue
        response.raise_for_status()
        break
    else:
        response.raise_for_status()  # Raise the last error

    # Delay between requests to avoid rate limiting
    time.sleep(0.5)

    data = response.json()

    if "verses" not in data:
        return {"chapter": chapter, "verses": []}

    verses = []
    for item in data["verses"]:
        verse_num = int(item.get("verse", 0))
        text = item.get("text", "").strip()
        # Clean up formatting
        text = re.sub(r'\s+', ' ', text)

        if verse_num and text:
            verses.append({
                "verse": verse_num,
                "text": text
            })

    return {"chapter": chapter, "verses": verses}


def fetch_passage(passage_ref: str, translation: str = "web") -> dict:
    """Fetch Bible passage text from bible-api.com.

    Args:
        passage_ref: Passage reference like "John 1:1-18" or "Ephesians"
        translation: Translation code (web, asv, kjv, etc.)
    """
    passage_ref = passage_ref.strip()
    trans_name = AVAILABLE_TRANSLATIONS.get(translation, translation.upper())

    # Normalize book names
    book_name = None
    for book in BOOK_CHAPTERS.keys():
        if passage_ref.lower() == book.lower() or passage_ref.lower().replace(" ", "") == book.lower().replace(" ", ""):
            book_name = book
            break

    if book_name:
        # Fetch full book chapter by chapter
        print(f"   Fetching {trans_name} {BOOK_CHAPTERS[book_name]} chapters...")
        chapters = []
        for ch in range(1, BOOK_CHAPTERS[book_name] + 1):
            chapter_data = fetch_chapter(book_name, ch, translation)
            chapters.append(chapter_data)
            print(f"      Chapter {ch}: {len(chapter_data['verses'])} verses")

        return {
            "passage": passage_ref,
            "canonical": book_name,
            "type": "book",
            "translation": trans_name,
            "chapters": chapters
        }

    # Single passage request
    url = f"{BIBLE_API_URL}{passage_ref.replace(' ', '+')}?translation={translation}"

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    if "verses" not in data:
        raise ValueError(f"No passages returned for: {passage_ref}")

    verses = []
    for item in data["verses"]:
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
        "canonical": data.get("reference", passage_ref),
        "type": "verses",
        "translation": trans_name,
        "verses": verses
    }


# Convenience functions for specific translations
def fetch_asv_passage(passage_ref: str) -> dict:
    """Fetch American Standard Version passage."""
    return fetch_passage(passage_ref, "asv")


def fetch_kjv_passage(passage_ref: str) -> dict:
    """Fetch King James Version passage."""
    return fetch_passage(passage_ref, "kjv")


def fetch_web_passage(passage_ref: str) -> dict:
    """Fetch World English Bible passage."""
    return fetch_passage(passage_ref, "web")


if __name__ == "__main__":
    import json
    result = fetch_asv_passage("Ephesians 1:1-3")
    print(json.dumps(result, indent=2))

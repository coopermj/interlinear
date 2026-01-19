#!/usr/bin/env python3
"""Strong's Greek dictionary lookup for appendix generation."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
STRONGS_FILE = DATA_DIR / "strongs-greek.json"

_strongs_dict = None


def load_strongs_dictionary() -> dict:
    """Load the Strong's Greek dictionary."""
    global _strongs_dict
    if _strongs_dict is not None:
        return _strongs_dict

    if not STRONGS_FILE.exists():
        raise FileNotFoundError(
            f"Strong's dictionary not found at {STRONGS_FILE}. "
            "The data file should be downloaded automatically."
        )

    with open(STRONGS_FILE, 'r', encoding='utf-8') as f:
        _strongs_dict = json.load(f)

    return _strongs_dict


def lookup_strongs(strongs_num: str) -> dict:
    """Look up a Strong's number and return its entry.

    Args:
        strongs_num: e.g., "G3056" or "G976"

    Returns:
        Dictionary with lemma, translit, strongs_def, kjv_def, derivation
    """
    dictionary = load_strongs_dictionary()
    return dictionary.get(strongs_num, {})


def collect_strongs_from_greek_data(greek_data: dict) -> dict:
    """Collect all unique Strong's numbers from Greek passage data.

    Returns:
        Dictionary mapping Strong's number to entry info
    """
    strongs_numbers = set()

    if greek_data.get("type") == "book":
        for chapter in greek_data.get("chapters", []):
            for verse in chapter.get("verses", []):
                for word in verse.get("words", []):
                    if "strongs" in word:
                        strongs_numbers.add(word["strongs"])
    else:
        for verse in greek_data.get("verses", []):
            for word in verse.get("words", []):
                if "strongs" in word:
                    strongs_numbers.add(word["strongs"])

    # Look up each Strong's number
    dictionary = load_strongs_dictionary()
    entries = {}

    for num in sorted(strongs_numbers, key=lambda x: int(x[1:])):
        entry = dictionary.get(num, {})
        if entry:
            entries[num] = {
                "strongs": num,
                "lemma": entry.get("lemma", ""),
                "translit": entry.get("translit", ""),
                "definition": entry.get("strongs_def", "").strip(),
                "kjv_def": entry.get("kjv_def", ""),
                "derivation": entry.get("derivation", "")
            }
        else:
            # Entry not in dictionary - use what we have from the text
            entries[num] = {
                "strongs": num,
                "lemma": "",
                "translit": "",
                "definition": "",
                "kjv_def": "",
                "derivation": ""
            }

    return entries


def format_appendix_entries(entries: dict) -> list:
    """Format Strong's entries for LaTeX appendix.

    Returns list of entries sorted by Strong's number.
    """
    result = []
    for num in sorted(entries.keys(), key=lambda x: int(x[1:])):
        entry = entries[num]
        result.append(entry)
    return result


if __name__ == "__main__":
    # Test
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.parse_greek import load_greek_passage

    data = load_greek_passage("Ephesians 1:1-3")
    entries = collect_strongs_from_greek_data(data)

    print(f"Found {len(entries)} unique Strong's numbers:\n")
    for num, entry in list(entries.items())[:5]:
        print(f"{num}: {entry['lemma']} ({entry['translit']})")
        print(f"   Definition: {entry['definition'][:60]}...")
        print()

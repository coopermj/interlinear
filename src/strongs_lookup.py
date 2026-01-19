#!/usr/bin/env python3
"""Strong's Greek dictionary lookup with Liddell & Scott definitions."""

import json
import re
import unicodedata
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
STRONGS_FILE = DATA_DIR / "strongs-greek.json"
LSJ_FILE = DATA_DIR / "lsj.json"

_strongs_dict = None
_lsj_dict = None
_lsj_normalized = None


def normalize_greek(text: str) -> str:
    """Normalize Greek text by removing accents and breathing marks."""
    if not text:
        return ""
    # NFD normalization separates base characters from combining marks
    text = unicodedata.normalize('NFD', text)
    # Remove combining marks (accents, breathings, etc.)
    text = ''.join(c for c in text if unicodedata.category(c) not in ['Mn'])
    return text.lower()


def load_lsj_dictionary() -> tuple[dict, dict]:
    """Load the Liddell & Scott Greek-English Lexicon.

    Returns:
        Tuple of (raw dictionary, normalized lookup dictionary)
    """
    global _lsj_dict, _lsj_normalized
    if _lsj_dict is not None:
        return _lsj_dict, _lsj_normalized

    if not LSJ_FILE.exists():
        print(f"Note: LSJ dictionary not found at {LSJ_FILE}")
        _lsj_dict = {}
        _lsj_normalized = {}
        return _lsj_dict, _lsj_normalized

    with open(LSJ_FILE, 'r', encoding='utf-8') as f:
        _lsj_dict = json.load(f)

    # Build normalized lookup (maps normalized form to original key)
    _lsj_normalized = {}
    for key in _lsj_dict.keys():
        norm_key = normalize_greek(key)
        if norm_key not in _lsj_normalized:
            _lsj_normalized[norm_key] = key

    return _lsj_dict, _lsj_normalized


def clean_lsj_html(html_text: str) -> str:
    """Convert LSJ HTML to plain text suitable for LaTeX."""
    if not html_text:
        return ""

    text = html_text
    # Remove bold tags (headword)
    text = re.sub(r'<b>([^<]*)</b>', r'\1', text)
    # Convert italics to plain (Greek citations)
    text = re.sub(r'<i>([^<]*)</i>', r'\1', text)
    # Remove other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def lookup_lsj(lemma: str) -> str:
    """Look up a Greek lemma in the LSJ dictionary.

    Args:
        lemma: Greek word (e.g., "λόγος")

    Returns:
        LSJ definition as plain text, or empty string if not found
    """
    lsj, lsj_norm = load_lsj_dictionary()

    if not lemma or not lsj:
        return ""

    # Try direct match first
    if lemma in lsj:
        return clean_lsj_html(lsj[lemma].get('d', ''))

    # Try lowercase match
    lower_lemma = lemma.lower()
    for key in lsj.keys():
        if key.lower() == lower_lemma:
            return clean_lsj_html(lsj[key].get('d', ''))

    # Try normalized match (no accents)
    norm_lemma = normalize_greek(lemma)
    if norm_lemma in lsj_norm:
        original_key = lsj_norm[norm_lemma]
        return clean_lsj_html(lsj[original_key].get('d', ''))

    return ""


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

    # Look up each Strong's number and corresponding LSJ entry
    dictionary = load_strongs_dictionary()
    entries = {}
    lsj_found = 0

    for num in sorted(strongs_numbers, key=lambda x: int(x[1:])):
        entry = dictionary.get(num, {})
        if entry:
            lemma = entry.get("lemma", "")
            lsj_def = lookup_lsj(lemma) if lemma else ""
            if lsj_def:
                lsj_found += 1

            entries[num] = {
                "strongs": num,
                "lemma": lemma,
                "translit": entry.get("translit", ""),
                "definition": entry.get("strongs_def", "").strip(),
                "lsj_definition": lsj_def,
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
                "lsj_definition": "",
                "kjv_def": "",
                "derivation": ""
            }

    print(f"   Found LSJ definitions for {lsj_found}/{len(entries)} entries")
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

    print(f"\nFound {len(entries)} unique Strong's numbers:\n")
    for num, entry in list(entries.items())[:5]:
        print(f"{num}: {entry['lemma']} ({entry['translit']})")
        print(f"   Strong's: {entry['definition'][:60]}...")
        if entry.get('lsj_definition'):
            print(f"   LSJ: {entry['lsj_definition'][:80]}...")
        else:
            print(f"   LSJ: (not found)")
        print()

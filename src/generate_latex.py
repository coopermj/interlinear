#!/usr/bin/env python3
"""Generate LaTeX document from Greek and ESV data."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .strongs_lookup import collect_strongs_from_greek_data, format_appendix_entries

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# LaTeX special characters that need escaping
LATEX_SPECIAL = {
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
}


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in text."""
    if not text:
        return ""

    result = text
    # Handle backslash first
    result = result.replace('\\', r'\textbackslash{}')

    for char, replacement in LATEX_SPECIAL.items():
        result = result.replace(char, replacement)

    return result


def sanitize_filename(passage_ref: str) -> str:
    """Convert passage reference to safe filename."""
    name = passage_ref.replace(' ', '_').replace(':', '_')
    name = re.sub(r'[^\w\-]', '', name)
    return name


def merge_verse_data(greek_verses: list, esv_verses: list) -> list[dict]:
    """Merge Greek and ESV verse data by verse number."""
    # Build lookup with text and heading
    esv_lookup = {}
    for v in esv_verses:
        esv_lookup[v["verse"]] = {
            "text": v.get("text", ""),
            "heading": v.get("heading", "")
        }

    verses = []
    for greek_verse in greek_verses:
        verse_num = greek_verse["verse"]
        esv_data = esv_lookup.get(verse_num, {"text": "", "heading": ""})

        verses.append({
            "number": verse_num,
            "greek_words": greek_verse.get("words", []),
            "esv_text": esv_data["text"],
            "heading": esv_data["heading"]
        })

    return verses


def merge_book_data(greek_data: dict, esv_data: dict) -> list[dict]:
    """Merge Greek and ESV data for a full book."""
    # Build lookup for ESV chapters with headings
    esv_chapters = {}
    if esv_data.get("type") == "book" and "chapters" in esv_data:
        for ch in esv_data["chapters"]:
            esv_chapters[ch["chapter"]] = {
                v["verse"]: {"text": v.get("text", ""), "heading": v.get("heading", "")}
                for v in ch["verses"]
            }
    elif "verses" in esv_data:
        esv_chapters[1] = {
            v["verse"]: {"text": v.get("text", ""), "heading": v.get("heading", "")}
            for v in esv_data["verses"]
        }

    chapters = []
    for greek_chapter in greek_data.get("chapters", []):
        ch_num = greek_chapter["chapter"]
        esv_verse_lookup = esv_chapters.get(ch_num, {})

        verses = []
        for greek_verse in greek_chapter.get("verses", []):
            verse_num = greek_verse["verse"]
            esv_verse_data = esv_verse_lookup.get(verse_num, {"text": "", "heading": ""})

            # Include Strong's numbers in word data
            greek_words = []
            for word in greek_verse.get("words", []):
                word_data = {
                    "greek": word.get("greek", ""),
                    "gloss": word.get("gloss", "")
                }
                if "strongs" in word:
                    word_data["strongs"] = word["strongs"]
                greek_words.append(word_data)

            verses.append({
                "number": verse_num,
                "greek_words": greek_words,
                "esv_text": esv_verse_data["text"],
                "heading": esv_verse_data["heading"]
            })

        chapters.append({
            "number": ch_num,
            "verses": verses
        })

    return chapters


def escape_chapter_data(chapters: list) -> list:
    """Escape LaTeX special chars in chapter data."""
    for chapter in chapters:
        for verse in chapter["verses"]:
            verse["esv_text"] = escape_latex(verse["esv_text"])
            verse["heading"] = escape_latex(verse.get("heading", ""))
            for word in verse["greek_words"]:
                word["gloss"] = escape_latex(word["gloss"])
    return chapters


def escape_verse_data(verses: list) -> list:
    """Escape LaTeX special chars in verse data."""
    for verse in verses:
        verse["esv_text"] = escape_latex(verse["esv_text"])
        verse["heading"] = escape_latex(verse.get("heading", ""))
        for word in verse["greek_words"]:
            word["gloss"] = escape_latex(word["gloss"])
    return verses


def render_book(greek_data: dict, esv_data: dict, passage_ref: str) -> Path:
    """Render a full book document."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chapters = merge_book_data(greek_data, esv_data)
    chapters = escape_chapter_data(chapters)

    # Collect Strong's entries for appendix
    strongs_entries_raw = collect_strongs_from_greek_data(greek_data)
    strongs_entries = format_appendix_entries(strongs_entries_raw)

    # Escape LaTeX special characters in Strong's entries
    for entry in strongs_entries:
        entry["lemma"] = escape_latex(entry.get("lemma", ""))
        entry["translit"] = escape_latex(entry.get("translit", ""))
        entry["definition"] = escape_latex(entry.get("definition", ""))
        entry["lsj_definition"] = escape_latex(entry.get("lsj_definition", ""))

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='<<',
        variable_end_string='>>',
        comment_start_string='<#',
        comment_end_string='#>',
    )

    template = env.get_template("book.tex.jinja2")

    content = template.render(
        book_title=escape_latex(greek_data.get("book", passage_ref)),
        chapters=chapters,
        strongs_entries=strongs_entries
    )

    filename = sanitize_filename(passage_ref) + ".tex"
    output_path = OUTPUT_DIR / filename

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Generated LaTeX: {output_path}")
    print(f"   Included {len(strongs_entries)} Strong's entries in appendix")
    return output_path


def render_document(greek_data: dict, esv_data: dict, passage_ref: str) -> Path:
    """Render the LaTeX document from Greek and ESV data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check if this is a full book
    if greek_data.get("type") == "book":
        return render_book(greek_data, esv_data, passage_ref)

    # Handle single chapter or verse range
    verses = merge_verse_data(
        greek_data.get("verses", []),
        esv_data.get("verses", [])
    )

    verses = escape_verse_data(verses)

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='<<',
        variable_end_string='>>',
        comment_start_string='<#',
        comment_end_string='#>',
    )

    template = env.get_template("document.tex.jinja2")

    content = template.render(
        passage_title=escape_latex(passage_ref),
        verses=verses
    )

    filename = sanitize_filename(passage_ref) + ".tex"
    output_path = OUTPUT_DIR / filename

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Generated LaTeX: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Generate LaTeX from data files")
    parser.add_argument("--greek", required=True, help="Greek data JSON file")
    parser.add_argument("--esv", required=True, help="ESV data JSON file")
    parser.add_argument("--passage", required=True, help="Passage reference for title")
    args = parser.parse_args()

    with open(args.greek, 'r', encoding='utf-8') as f:
        greek_data = json.load(f)

    with open(args.esv, 'r', encoding='utf-8') as f:
        esv_data = json.load(f)

    output_path = render_document(greek_data, esv_data, args.passage)
    print(f"Output: {output_path}")

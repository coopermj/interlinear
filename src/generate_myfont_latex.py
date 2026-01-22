#!/usr/bin/env python3
"""Generate LaTeX document for myfont portrait layout with random glyph variants."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .strongs_lookup import collect_strongs_from_greek_data, format_appendix_entries

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "myfont_portrait"
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
    result = result.replace('\\', r'\textbackslash{}')

    for char, replacement in LATEX_SPECIAL.items():
        result = result.replace(char, replacement)

    return result


def sanitize_filename(passage_ref: str) -> str:
    """Convert passage reference to safe filename."""
    name = passage_ref.replace(' ', '_').replace(':', '_')
    name = re.sub(r'[^\w\-]', '', name)
    return name + "_myfont"


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


def render_myfont_book(greek_data: dict, esv_data: dict, passage_ref: str) -> Path:
    """Render a myfont portrait book document with random glyph variants."""
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

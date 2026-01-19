#!/usr/bin/env python3
"""Generate LaTeX document for multi-translation landscape layout."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .strongs_lookup import collect_strongs_from_greek_data, format_appendix_entries

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "multi_landscape"
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
    '~': r'\\textasciitilde{}',
    '^': r'\\textasciicircum{}',
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
    return name + "_multi"


def merge_multi_book_data(greek_data: dict, esv_data: dict, net_data: dict, kjv_data: dict) -> list[dict]:
    """Merge Greek and multiple translation data for a full book."""
    # Build lookups for each translation
    def build_chapter_lookup(data: dict) -> dict:
        chapters = {}
        if data.get("type") == "book" and "chapters" in data:
            for ch in data["chapters"]:
                chapters[ch["chapter"]] = {
                    v["verse"]: {"text": v.get("text", ""), "heading": v.get("heading", "")}
                    for v in ch["verses"]
                }
        elif "verses" in data:
            chapters[1] = {
                v["verse"]: {"text": v.get("text", ""), "heading": v.get("heading", "")}
                for v in data["verses"]
            }
        return chapters

    esv_chapters = build_chapter_lookup(esv_data)
    net_chapters = build_chapter_lookup(net_data)
    kjv_chapters = build_chapter_lookup(kjv_data)

    chapters = []
    for greek_chapter in greek_data.get("chapters", []):
        ch_num = greek_chapter["chapter"]
        esv_lookup = esv_chapters.get(ch_num, {})
        net_lookup = net_chapters.get(ch_num, {})
        kjv_lookup = kjv_chapters.get(ch_num, {})

        verses = []
        for greek_verse in greek_chapter.get("verses", []):
            verse_num = greek_verse["verse"]
            esv_verse = esv_lookup.get(verse_num, {"text": "", "heading": ""})
            net_verse = net_lookup.get(verse_num, {"text": "", "heading": ""})
            kjv_verse = kjv_lookup.get(verse_num, {"text": "", "heading": ""})

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
                "esv_text": esv_verse["text"],
                "net_text": net_verse["text"],
                "kjv_text": kjv_verse["text"],
                "heading": esv_verse.get("heading", "")
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
            verse["net_text"] = escape_latex(verse["net_text"])
            verse["kjv_text"] = escape_latex(verse["kjv_text"])
            verse["heading"] = escape_latex(verse.get("heading", ""))
            for word in verse["greek_words"]:
                word["gloss"] = escape_latex(word["gloss"])
    return chapters


def render_multi_book(greek_data: dict, esv_data: dict, net_data: dict, kjv_data: dict, passage_ref: str) -> Path:
    """Render a multi-translation landscape book document."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chapters = merge_multi_book_data(greek_data, esv_data, net_data, kjv_data)
    chapters = escape_chapter_data(chapters)

    # Collect Strong's entries for appendix
    strongs_entries_raw = collect_strongs_from_greek_data(greek_data)
    strongs_entries = format_appendix_entries(strongs_entries_raw)

    # Escape LaTeX special characters in Strong's entries
    for entry in strongs_entries:
        entry["lemma"] = escape_latex(entry.get("lemma", ""))
        entry["translit"] = escape_latex(entry.get("translit", ""))
        entry["definition"] = escape_latex(entry.get("definition", ""))

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

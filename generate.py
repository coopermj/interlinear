#!/usr/bin/env python3
"""
Interlinear Bible Generator

Generate beautifully typeset interlinear Bible passages with:
- Left column: Greek text with English glosses
- Right column(s): Bible translations

Layouts:
- esv-portrait: Greek + ESV (Remarkable Paper Pro portrait)
- multi-landscape: Greek + ESV + NET + KJV (Remarkable Paper Pro landscape)

Usage:
    python generate.py "John 1:1-18"
    python generate.py "Ephesians"
    python generate.py "Ephesians" --layout multi-landscape
"""

import argparse
import sys
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent))

from src.download_data import download_opengnt
from src.parse_greek import load_greek_passage, BOOK_CHAPTERS
from src.fetch_esv import fetch_esv_passage
from src.generate_latex import render_document
from src.build_pdf import build_pdf, check_lualatex
from src.merge_books import merge_collection, find_portrait_books

AVAILABLE_LAYOUTS = {
    "esv-portrait": "Greek + ESV (Remarkable Paper Pro portrait)",
    "multi-landscape": "Greek + ESV + NET + KJV (Remarkable Paper Pro landscape)",
    "myfont-portrait": "Greek + ESV with custom font and random glyph variants",
}


def count_greek_data(greek_data: dict) -> tuple[int, int, int]:
    """Count chapters, verses, and words in Greek data."""
    if greek_data.get("type") == "book":
        chapters = greek_data.get("chapters", [])
        chapter_count = len(chapters)
        verse_count = sum(len(ch.get("verses", [])) for ch in chapters)
        word_count = sum(
            len(v.get("words", []))
            for ch in chapters
            for v in ch.get("verses", [])
        )
        return chapter_count, verse_count, word_count
    else:
        verses = greek_data.get("verses", [])
        verse_count = len(verses)
        word_count = sum(len(v.get("words", [])) for v in verses)
        return 0, verse_count, word_count


def count_translation_data(data: dict) -> int:
    """Count verses in translation data."""
    if data.get("type") == "book":
        return sum(len(ch.get("verses", [])) for ch in data.get("chapters", []))
    else:
        return len(data.get("verses", []))


def generate_esv_portrait(args, greek_data):
    """Generate ESV Portrait layout."""
    # Fetch ESV text
    print(f"\n[3/4] Fetching ESV translation...")
    esv_data = fetch_esv_passage(args.passage, args.api_key)
    esv_verse_count = count_translation_data(esv_data)
    print(f"   Retrieved {esv_verse_count} verses from ESV API")

    # Generate LaTeX
    print(f"\n[4/4] Generating LaTeX document...")
    tex_path = render_document(greek_data, esv_data, args.passage)

    return tex_path


def generate_multi_landscape(args, greek_data):
    """Generate Multi Landscape layout with ESV, NET, KJV."""
    from src.fetch_net import fetch_net_passage
    from src.fetch_bibleapi import fetch_kjv_passage
    from src.generate_multi_latex import render_multi_book

    # Fetch ESV text
    print(f"\n[3/6] Fetching ESV translation...")
    esv_data = fetch_esv_passage(args.passage, args.api_key)
    esv_verse_count = count_translation_data(esv_data)
    print(f"   Retrieved {esv_verse_count} verses from ESV API")

    # Fetch NET text
    print(f"\n[4/6] Fetching NET translation...")
    net_data = fetch_net_passage(args.passage)
    net_verse_count = count_translation_data(net_data)
    print(f"   Retrieved {net_verse_count} verses from NET API")

    # Fetch KJV text
    print(f"\n[5/6] Fetching KJV translation...")
    kjv_data = fetch_kjv_passage(args.passage)
    kjv_verse_count = count_translation_data(kjv_data)
    print(f"   Retrieved {kjv_verse_count} verses from bible-api.com")

    # Generate LaTeX
    print(f"\n[6/6] Generating LaTeX document...")
    tex_path = render_multi_book(greek_data, esv_data, net_data, kjv_data, args.passage)

    return tex_path


def generate_myfont_portrait(args, greek_data):
    """Generate Myfont Portrait layout with random glyph variants."""
    from src.generate_myfont_latex import render_myfont_book

    # Fetch ESV text
    print(f"\n[3/4] Fetching ESV translation...")
    esv_data = fetch_esv_passage(args.passage, args.api_key)
    esv_verse_count = count_translation_data(esv_data)
    print(f"   Retrieved {esv_verse_count} verses from ESV API")

    # Generate LaTeX
    print(f"\n[4/4] Generating LaTeX document...")
    tex_path = render_myfont_book(greek_data, esv_data, args.passage)

    return tex_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate interlinear Bible PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Layouts:
    esv-portrait      Greek + ESV (default, Remarkable Paper Pro portrait)
    multi-landscape   Greek + ESV + NET + KJV (Remarkable Paper Pro landscape)
    myfont-portrait   Greek + ESV with custom font and random glyph variants

Examples:
    python generate.py "John 1:1-18"
    python generate.py "Ephesians"
    python generate.py "Ephesians" --layout multi-landscape
    python generate.py "Romans 8:28-39" --latex-only

Before first use:
    1. Copy config.py.example to config.py
    2. Add your ESV API key (from api.esv.org)
    3. Run: python -m src.download_data
        """
    )

    parser.add_argument(
        "passage",
        help="Passage reference (e.g., 'John 1:1-18', 'Ephesians', 'Romans 8')"
    )
    parser.add_argument(
        "--layout",
        choices=list(AVAILABLE_LAYOUTS.keys()),
        default="esv-portrait",
        help="Layout template to use (default: esv-portrait)"
    )
    parser.add_argument(
        "--latex-only",
        action="store_true",
        help="Generate LaTeX only, don't compile to PDF"
    )
    parser.add_argument(
        "--api-key",
        help="ESV API key (overrides config.py)"
    )
    parser.add_argument(
        "--keep-aux",
        action="store_true",
        help="Keep LaTeX auxiliary files"
    )

    args = parser.parse_args()

    try:
        # Step 1: Ensure OpenGNT data is available
        print(f"\n{'='*60}")
        print(f"Generating interlinear for: {args.passage}")
        print(f"Layout: {args.layout} - {AVAILABLE_LAYOUTS[args.layout]}")
        print(f"{'='*60}\n")

        print("[1/4] Checking Greek text data..." if args.layout == "esv-portrait" else "[1/6] Checking Greek text data...")
        download_opengnt()

        # Step 2: Load Greek data
        step = "[2/4]" if args.layout in ("esv-portrait", "myfont-portrait") else "[2/6]"
        print(f"\n{step} Loading Greek text for {args.passage}...")
        greek_data = load_greek_passage(args.passage)

        chapter_count, verse_count, word_count = count_greek_data(greek_data)

        if verse_count == 0:
            print(f"Warning: No Greek verses found for {args.passage}")
            print("The passage may be outside the New Testament or incorrectly formatted.")
            sys.exit(1)

        if chapter_count > 0:
            print(f"   Found {chapter_count} chapters, {verse_count} verses, {word_count} Greek words")
        else:
            print(f"   Found {verse_count} verses, {word_count} Greek words")

        # Generate based on layout
        if args.layout == "esv-portrait":
            tex_path = generate_esv_portrait(args, greek_data)
        elif args.layout == "multi-landscape":
            tex_path = generate_multi_landscape(args, greek_data)
        elif args.layout == "myfont-portrait":
            tex_path = generate_myfont_portrait(args, greek_data)
        else:
            raise ValueError(f"Unknown layout: {args.layout}")

        if args.latex_only:
            print(f"\n{'='*60}")
            print(f"LaTeX generated: {tex_path}")
            print(f"{'='*60}")
            return

        # Compile PDF
        if not check_lualatex():
            print("\nWarning: lualatex not found. LaTeX file generated but not compiled.")
            print(f"LaTeX file: {tex_path}")
            print("\nTo compile manually:")
            print(f"  cd {tex_path.parent}")
            print(f"  lualatex {tex_path.name}")
            return

        print("\nCompiling PDF with LuaLaTeX...")
        pdf_path = build_pdf(tex_path, clean=not args.keep_aux)

        print(f"\n{'='*60}")
        print(f"SUCCESS! PDF generated:")
        print(f"  {pdf_path}")
        print(f"{'='*60}\n")

        # Auto-merge portrait books into collection if this is a full book
        if args.layout == "esv-portrait" and greek_data.get("type") == "book":
            portrait_books = find_portrait_books()
            if len(portrait_books) > 1:
                print("Updating merged collection...")
                collection_path = merge_collection()
                print(f"  {collection_path}\n")

    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Merge multiple book PDFs into a single collection with TOC."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from pypdf import PdfReader, PdfWriter

from .build_pdf import build_pdf

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "esv_portrait"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# NT book order for sorting
NT_BOOK_ORDER = [
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1_Corinthians", "2_Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians",
    "1_Thessalonians", "2_Thessalonians", "1_Timothy",
    "2_Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1_Peter", "2_Peter", "1_John",
    "2_John", "3_John", "Jude", "Revelation",
]


def get_book_order(filename: str) -> int:
    """Get sort order for a book filename."""
    # Extract book name from filename (e.g., "Matthew.pdf" -> "Matthew")
    name = filename.replace(".pdf", "").replace("_multi", "")
    try:
        return NT_BOOK_ORDER.index(name)
    except ValueError:
        return 999  # Unknown books go at the end


def find_portrait_books() -> list[Path]:
    """Find all portrait (non-multi) book PDFs in output directory."""
    if not OUTPUT_DIR.exists():
        return []

    # Build set of valid book filenames
    valid_names = {f"{book}.pdf" for book in NT_BOOK_ORDER}

    pdfs = []
    for pdf in OUTPUT_DIR.glob("*.pdf"):
        # Only include files that match exact NT book names
        if pdf.name in valid_names:
            pdfs.append(pdf)

    # Sort by NT book order
    pdfs.sort(key=lambda p: get_book_order(p.name))
    return pdfs


def get_book_info(pdf_path: Path) -> dict:
    """Extract info about a book PDF."""
    reader = PdfReader(pdf_path)
    name = pdf_path.stem.replace("_", " ")
    return {
        "name": name,
        "path": pdf_path,
        "pages": len(reader.pages),
    }


def generate_toc_pdf(books: list[dict], total_stats: dict) -> Path:
    """Generate the TOC/cover PDF."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='<<',
        variable_end_string='>>',
        comment_start_string='<#',
        comment_end_string='#>',
    )

    template = env.get_template("collection_toc.tex.jinja2")

    # Calculate page numbers (TOC is 2 pages, then books start)
    current_page = 3  # After 2-page TOC
    books_with_pages = []
    for book in books:
        books_with_pages.append({
            "name": book["name"],
            "page": current_page,
        })
        current_page += book["pages"]

    content = template.render(
        books=books_with_pages,
        total_chapters=total_stats.get("chapters", ""),
        total_verses=total_stats.get("verses", ""),
        total_words=total_stats.get("words", ""),
    )

    toc_tex = OUTPUT_DIR / "_toc_temp.tex"
    with open(toc_tex, 'w', encoding='utf-8') as f:
        f.write(content)

    toc_pdf = build_pdf(toc_tex, clean=True)
    toc_tex.unlink(missing_ok=True)

    return toc_pdf


def merge_pdfs(toc_pdf: Path, book_pdfs: list[Path], output_path: Path) -> Path:
    """Merge TOC and book PDFs into a single file with bookmarks."""
    writer = PdfWriter()

    # Add TOC pages
    toc_reader = PdfReader(toc_pdf)
    for page in toc_reader.pages:
        writer.add_page(page)

    # Track page numbers for bookmarks
    current_page = len(toc_reader.pages)

    # Add each book with bookmark
    for pdf_path in book_pdfs:
        reader = PdfReader(pdf_path)
        book_name = pdf_path.stem.replace("_", " ")

        # Add bookmark pointing to first page of this book
        writer.add_outline_item(book_name, current_page)

        for page in reader.pages:
            writer.add_page(page)

        current_page += len(reader.pages)

    # Write merged PDF
    with open(output_path, 'wb') as f:
        writer.write(f)

    # Clean up temp TOC
    toc_pdf.unlink(missing_ok=True)

    return output_path


def merge_collection(output_name: str = "NT_Interlinear.pdf") -> Path:
    """Merge all portrait book PDFs into a single collection."""
    book_pdfs = find_portrait_books()

    if not book_pdfs:
        raise ValueError("No portrait book PDFs found in output/")

    print(f"Found {len(book_pdfs)} books to merge:")
    books = []
    for pdf in book_pdfs:
        info = get_book_info(pdf)
        books.append(info)
        print(f"   {info['name']}: {info['pages']} pages")

    total_pages = sum(b["pages"] for b in books)
    print(f"\nTotal: {total_pages} pages")

    # Generate TOC
    print("\nGenerating table of contents...")
    total_stats = {}  # Could be populated from a manifest file
    toc_pdf = generate_toc_pdf(books, total_stats)

    # Merge all PDFs
    print("Merging PDFs...")
    output_path = OUTPUT_DIR / output_name
    merge_pdfs(toc_pdf, book_pdfs, output_path)

    print(f"\nCreated: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Merge book PDFs into collection")
    parser.add_argument(
        "--output", "-o",
        default="NT_Interlinear.pdf",
        help="Output filename (default: NT_Interlinear.pdf)"
    )
    args = parser.parse_args()

    merge_collection(args.output)

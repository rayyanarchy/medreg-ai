"""
Ingestion pipeline: raw PDFs -> Markdown files.
Run manually whenever a PDF is added/changed. NOT part of the runtime app —
this is why pdfplumber lives in the 'ingestion' dependency group, not the base one.
"""

from pathlib import Path
import pdfplumber

DATA_DIR = Path("data")
OUTPUT_DIR = Path("ingestion/processed")


def table_to_markdown(table: list[list[str]]) -> str:
    """Converts a pdfplumber table (list of rows) into a Markdown table."""
    if not table or not table[0]:
        return ""

    def clean_row(row):
        return [(cell or "").strip().replace("\n", " ") for cell in row]

    header = clean_row(table[0])
    body = [clean_row(row) for row in table[1:]]

    lines = ["| " + " | ".join(header) + " |",
              "| " + " | ".join(["---"] * len(header)) + " |"]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def page_to_markdown(page) -> str:
    """One pdfplumber page -> Markdown: plain text with any tables inlined."""
    tables = page.find_tables()
    
    page_no_tables = page
    for table in tables:
        x0, top, x1, bottom = table.bbox
        bbox = (
            max(0.0, min(x0, float(page.width))),
            max(0.0, min(top, float(page.height))),
            max(0.0, min(x1, float(page.width))),
            max(0.0, min(bottom, float(page.height))),
        )
        page_no_tables = page_no_tables.outside_bbox(bbox, strict=False)
    
    parts = []
    text = page_no_tables.extract_text() or ""
    if text.strip():
        parts.append(text.strip())
    
    for table in tables:
        md_table = table_to_markdown(table.extract())
        if md_table:
            parts.append(md_table)
    
    return "\n\n".join(parts)


def pdf_to_markdown(pdf_path: Path) -> str:
    """
    One full PDF -> one Markdown string.
    Each page is prefixed with an HTML-comment marker so page numbers
    survive the conversion — the loader will read these back out.
    """
    md_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_md = page_to_markdown(page)
            if page_md.strip():
                md_pages.append(f"<!-- page: {page_num} -->\n{page_md}")
    return "\n\n".join(md_pages)


def convert_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(DATA_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in {DATA_DIR}")
        return

    for pdf_path in pdf_files:
        print(f"Converting {pdf_path.name}...")
        markdown = pdf_to_markdown(pdf_path)
        out_path = OUTPUT_DIR / f"{pdf_path.stem}.md"
        out_path.write_text(markdown, encoding="utf-8")
        print(f"  -> {out_path}")


if __name__ == "__main__":
    convert_all()

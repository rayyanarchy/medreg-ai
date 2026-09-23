"""
Runtime loader: reads pre-converted Markdown files from ingestion/processed/.
Never touches a PDF or imports pdfplumber — that dependency stays in ingestion/.
"""

import re
from pathlib import Path

PAGE_MARKER = re.compile(r"<!-- page: (\d+) -->")


def load_markdown(processed_dir: str) -> list[dict]:
    """
    Returns one dict per PAGE, same shape as before:
    {"source": "cdc_flu_factsheet.md", "page": 3, "text": "..."}
    """
    records = []
    for md_path in sorted(Path(processed_dir).glob("*.md")):
        content = md_path.read_text(encoding="utf-8")
        records.extend(_split_pages(content, md_path.stem + ".pdf"))
    return records


def _split_pages(content: str, source_name: str) -> list[dict]:
    """Splits one document's Markdown on page markers, pairing each
    chunk of text with the page number that preceded it."""
    matches = list(PAGE_MARKER.finditer(content))
    records = []

    for i, match in enumerate(matches):
        page_num = int(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        text = content[start:end].strip()

        if text:
            records.append({
                "source": source_name,
                "page": page_num,
                "text": text,
            })

    return records

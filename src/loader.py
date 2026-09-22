from pathlib import Path
from pypdf import PdfReader

def load_pdfs(data_dir: str) -> list[dict]:
    """
    Returns one dict per PAGE (not per document), like:
    {"source": "cdc_flu_factsheet.pdf", "page": 3, "text": "..."}
    Keeping it per-page (not per-document) now saves you a step later —
    you'll want page-level citations, not just "somewhere in this PDF."
    """
    records = []
    for pdf_path in sorted(Path(data_dir).glob("*.pdf")):
        reader = PdfReader(pdf_path)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():  # skip blank pages
                records.append({
                    "source": pdf_path.name,
                    "page": page_num,
                    "text": text,
                })
    return records

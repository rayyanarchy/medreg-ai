"""
Runtime loader: reads pre-parsed eCFR section records from
data/processed/part_11.json. Never touches XML at runtime — parsing
happens once in ingestion/parse_ecfr.py.
"""

import json
from pathlib import Path


def load_sections(processed_path: str = "data/processed/part_11.json") -> list[dict]:
    """
    Returns one dict per SECTION:
    {"section": "11.10", "heading": "...", "subpart": "B",
     "subpart_heading": "...", "paragraphs": [...]}
    """
    return json.loads(Path(processed_path).read_text(encoding="utf-8"))
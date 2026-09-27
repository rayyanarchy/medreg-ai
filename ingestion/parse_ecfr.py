"""
Ingestion step 2: parse the raw eCFR XML into one record per SECTION.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

RAW_PATH = Path("data/raw/part_11.xml")
OUTPUT_PATH = Path("data/processed/part_11.json")


def parse_sections(raw_path: Path) -> list[dict]:
    tree = ET.parse(raw_path)
    root = tree.getroot()

    records = []
    for subpart in root.findall("DIV6"):
        subpart_num = subpart.get("N")
        subpart_head = subpart.findtext("HEAD", default="").strip()

        for section in subpart.findall("DIV8"):
            paragraphs = ["".join(p.itertext()).strip() for p in section.findall("P")]
            records.append({
                "section": section.get("N"),
                "heading": section.findtext("HEAD", default="").strip(),
                "subpart": subpart_num,
                "subpart_heading": subpart_head,
                "paragraphs": paragraphs,
            })

    return records

def build():
    records = parse_sections(RAW_PATH)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Parsed {len(records)} sections -> {OUTPUT_PATH}")


if __name__ == "__main__":
    build()

"""
Ingestion step 1: download the raw eCFR XML for a given title/part.
Resolves the correct 'as of' date via titles.json rather than hardcoding
one — 'current' isn't accepted by this endpoint, and a fixed date will
eventually 404 once the title is amended again.
"""

import requests
from pathlib import Path

TITLES_URL = "https://www.ecfr.gov/api/versioner/v1/titles.json"
FULL_URL_TEMPLATE = "https://www.ecfr.gov/api/versioner/v1/full/{date}/title-{title}.xml"

OUTPUT_PATH = Path("data/raw/part_11.xml")


def get_latest_date(title: int) -> str:
    """Looks up the most recent 'up to date as of' date for a given title."""
    response = requests.get(TITLES_URL, timeout=30)
    response.raise_for_status()
    titles = response.json()["titles"]
    match = next(t for t in titles if t["number"] == title)
    return match["up_to_date_as_of"]


def fetch_part(title: int = 21, part: str = "11"):
    date = get_latest_date(title)
    url = FULL_URL_TEMPLATE.format(date=date, title=title)
    response = requests.get(url, params={"part": part}, timeout=30)
    response.raise_for_status()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(response.text, encoding="utf-8")
    print(f"Fetched as of {date}, saved {len(response.text)} characters to {OUTPUT_PATH}")


if __name__ == "__main__":
    fetch_part()

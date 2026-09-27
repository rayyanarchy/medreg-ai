"""
Turns parsed section records into chunk-ready dicts.
Short sections stay as one chunk (one section = one citable unit).
Long sections are split by top-level lettered paragraph — (a), (b), (c) —
using sequence-tracking to avoid confusing a sub-item roman numeral
like (i) for a new top-level letter.
"""

import re
import string

MAX_WORDS = 300
TOP_LEVEL_MARKER = re.compile(r"^\(([a-z])\)")


def group_paragraphs(paragraphs: list[str]) -> list[list[str]]:
    groups = []
    current = []
    next_letter_index = 0

    for para in paragraphs:
        expected = (
            string.ascii_lowercase[next_letter_index]
            if next_letter_index < 26 else None
        )
        match = TOP_LEVEL_MARKER.match(para)
        is_new_group = match and match.group(1) == expected

        if is_new_group:
            if current:
                groups.append(current)
            current = [para]
            next_letter_index += 1
        else:
            current.append(para)

    if current:
        groups.append(current)
    return groups


def make_chunks(sections: list[dict]) -> list[dict]:
    chunks = []

    for s in sections:
        full_text = "\n".join(s["paragraphs"])
        word_count = len(full_text.split())
        citation_base = f"21 CFR {s['section']}"

        if word_count <= MAX_WORDS:
            chunks.append({
                "chunk_id": f"21cfr_{s['section']}",
                "section": s["section"],
                "subpart": s["subpart"],
                "citation": citation_base,
                "text": f"{s['heading']}\n{full_text}",
            })
        else:
            for group in group_paragraphs(s["paragraphs"]):
                label_match = TOP_LEVEL_MARKER.match(group[0])
                label = label_match.group(1) if label_match else None
                chunks.append({
                    "chunk_id": f"21cfr_{s['section']}_{label or len(chunks)}",
                    "section": s["section"],
                    "subpart": s["subpart"],
                    "citation": f"{citation_base}({label})" if label else citation_base,
                    "text": f"{s['heading']}\n" + "\n".join(group),
                })

    return chunks

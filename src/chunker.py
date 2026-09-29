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
        citation_base = f"21 CFR {s['section']}"
        base = {"section": s["section"], "subpart": s["subpart"]}

        def whole_section_chunk():
            return {
                **base,
                "chunk_id": f"21cfr_{s['section']}",
                "citation": citation_base,
                "text": f"{s['heading']}\n{full_text}",
            }

        if len(full_text.split()) <= MAX_WORDS:
            chunks.append(whole_section_chunk())
            continue

        groups = group_paragraphs(s["paragraphs"])

        # A group that doesn't start with "(a)" is a lead-in sentence
        first = TOP_LEVEL_MARKER.match(groups[0][0])
        lead_in = []
        if not (first and first.group(1) == "a"):
            lead_in = groups.pop(0)

        if not groups:  # long section with no lettering: keep whole
            chunks.append(whole_section_chunk())
            continue

        lead_text = "\n".join(lead_in)

        if lead_in:
            chunks.append({
                **base,
                "chunk_id": f"21cfr_{s['section']}_intro",
                "citation": citation_base,
                "text": f"{s['heading']}\n{lead_text}",
            })

        for group in groups:
            label = TOP_LEVEL_MARKER.match(group[0]).group(1)
            parts = [s["heading"]] + ([lead_text] if lead_text else []) + group
            chunks.append({
                **base,
                "chunk_id": f"21cfr_{s['section']}_{label}",
                "citation": f"{citation_base}({label})",
                "text": "\n".join(parts),
            })

    return chunks

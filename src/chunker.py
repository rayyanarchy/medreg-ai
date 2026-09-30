"""
Turns parsed section records into chunk-ready dicts.
Short sections stay as one chunk (one section = one citable unit).
Long sections are split by top-level lettered paragraph — (a), (b), (c) —
using sequence-tracking to avoid confusing a sub-item roman numeral
like (i) for a new top-level letter. A lettered paragraph that is itself
long, such as the definitions in § 11.3(b), is split again by its
numbered items — (1), (2), (3).

Each chunk carries two versions of its text:
- "text": what the LLM reads — heading, lead-in sentences, then the paragraph.
- "embed_text": what gets embedded — heading and the paragraph only. Lead-ins
  are left out because every sibling chunk shares them, which makes the
  siblings look alike to the embedding model.
"""

import re
import string
from collections.abc import Sequence

MAX_WORDS = 300
MAX_PARAGRAPH_WORDS = 150
TOP_LEVEL_MARKER = re.compile(r"^\(([a-z])\)")
NUMBERED_MARKER = re.compile(r"^\((\d+)\)")
NUMBER_LABELS = [str(n) for n in range(1, 100)]


def group_paragraphs(
    paragraphs: list[str],
    marker: re.Pattern = TOP_LEVEL_MARKER,
    labels: Sequence[str] = string.ascii_lowercase,
) -> list[list[str]]:
    """
    Groups paragraphs under the marker that opens them: each group starts at
    the next expected label — (a), then (b), ... — and runs to the next one.
    """
    groups = []
    current = []
    next_label_index = 0

    for para in paragraphs:
        expected = labels[next_label_index] if next_label_index < len(labels) else None
        match = marker.match(para)
        is_new_group = match and match.group(1) == expected

        if is_new_group:
            if current:
                groups.append(current)
            current = [para]
            next_label_index += 1
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
            text = f"{s['heading']}\n{full_text}"
            return {
                **base,
                "chunk_id": f"21cfr_{s['section']}",
                "citation": citation_base,
                "text": text,
                "embed_text": text,
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
            text = f"{s['heading']}\n{lead_text}"
            chunks.append({
                **base,
                "chunk_id": f"21cfr_{s['section']}_intro",
                "citation": citation_base,
                "text": text,
                "embed_text": text,
            })

        for group in groups:
            label = TOP_LEVEL_MARKER.match(group[0]).group(1)
            chunk_id = f"21cfr_{s['section']}_{label}"
            citation = f"{citation_base}({label})"
            context = [s["heading"]] + ([lead_text] if lead_text else [])

            # A long lettered paragraph made of numbered items: one chunk per item.
            # group[0] is its opening line, e.g. "(b) The following definitions ...:"
            items = group_paragraphs(group[1:], NUMBERED_MARKER, NUMBER_LABELS)
            is_numbered_list = items and NUMBERED_MARKER.match(items[0][0])
            if len(" ".join(group).split()) > MAX_PARAGRAPH_WORDS and is_numbered_list:
                for item in items:
                    number = NUMBERED_MARKER.match(item[0]).group(1)
                    chunks.append({
                        **base,
                        "chunk_id": f"{chunk_id}_{number}",
                        "citation": f"{citation}({number})",
                        "text": "\n".join(context + [group[0]] + item),
                        "embed_text": "\n".join([s["heading"]] + item),
                    })
                continue

            chunks.append({
                **base,
                "chunk_id": chunk_id,
                "citation": citation,
                "text": "\n".join(context + group),
                "embed_text": "\n".join([s["heading"]] + group),
            })

    return chunks

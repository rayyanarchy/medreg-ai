"""
Tests for the loader and chunker. No API calls and no Chroma: chunking is
pure Python, so these run offline in under a second.

Run from the repo root:
    uv run python -m unittest discover tests
"""

import unittest

from src.chunker import MAX_WORDS, group_paragraphs, make_chunks
from src.loader import load_sections


def filler(words: int) -> str:
    """A sentence of `words` words, to push a section over the length limits."""
    return " ".join(["word"] * words)


def section(number: str, paragraphs: list[str]) -> dict:
    """A minimal section record, shaped like the output of parse_ecfr.py."""
    return {
        "section": number,
        "heading": f"§ {number} Test heading.",
        "subpart": "B",
        "subpart_heading": "Test subpart",
        "paragraphs": paragraphs,
    }


class TestGroupParagraphs(unittest.TestCase):
    def test_groups_by_lettered_marker(self):
        groups = group_paragraphs(["(a) First.", "More of a.", "(b) Second."])
        self.assertEqual(groups, [["(a) First.", "More of a."], ["(b) Second."]])

    def test_roman_numeral_is_not_a_new_letter(self):
        # "(i)" right after "(a)" is a sub-item, because the next letter expected is "(b)"
        groups = group_paragraphs(["(a) Lead.", "(i) Sub-item.", "(b) Next."])
        self.assertEqual(groups, [["(a) Lead.", "(i) Sub-item."], ["(b) Next."]])

    def test_lead_in_becomes_its_own_group(self):
        groups = group_paragraphs(["Intro sentence.", "(a) First."])
        self.assertEqual(groups, [["Intro sentence."], ["(a) First."]])


class TestMakeChunks(unittest.TestCase):
    def test_short_section_stays_whole(self):
        chunks = make_chunks([section("11.70", ["(a) Short.", "(b) Also short."])])
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["chunk_id"], "21cfr_11.70")
        self.assertEqual(chunks[0]["citation"], "21 CFR 11.70")

    def test_long_section_splits_by_letter_with_intro(self):
        paragraphs = [
            "Persons who use closed systems shall:",
            f"(a) {filler(MAX_WORDS // 2)}",
            f"(b) {filler(MAX_WORDS // 2)}",
        ]
        chunks = make_chunks([section("11.10", paragraphs)])

        ids = [c["chunk_id"] for c in chunks]
        self.assertEqual(ids, ["21cfr_11.10_intro", "21cfr_11.10_a", "21cfr_11.10_b"])
        self.assertEqual(chunks[1]["citation"], "21 CFR 11.10(a)")

    def test_lead_in_shown_to_llm_but_not_embedded(self):
        lead_in = "Persons who use closed systems shall:"
        paragraphs = [lead_in, f"(a) {filler(MAX_WORDS)}", "(b) Short."]
        chunk_a = make_chunks([section("11.10", paragraphs)])[1]

        self.assertIn(lead_in, chunk_a["text"])
        self.assertNotIn(lead_in, chunk_a["embed_text"])

    def test_long_numbered_paragraph_splits_by_item(self):
        paragraphs = [
            "(a) Short.",
            "(b) The following definitions apply:",
            f"(1) {filler(MAX_WORDS // 2)}",
            f"(2) {filler(MAX_WORDS // 2)}",
        ]
        chunks = make_chunks([section("11.3", paragraphs)])

        ids = [c["chunk_id"] for c in chunks]
        self.assertEqual(ids, ["21cfr_11.3_a", "21cfr_11.3_b_1", "21cfr_11.3_b_2"])
        self.assertEqual(chunks[2]["citation"], "21 CFR 11.3(b)(2)")
        # The "(b) The following definitions apply:" opener gives each item its context
        self.assertIn("definitions apply", chunks[1]["text"])


class TestRealCorpus(unittest.TestCase):
    """Checks against the committed data/processed/part_11.json."""

    @classmethod
    def setUpClass(cls):
        cls.sections = load_sections()
        cls.chunks = make_chunks(cls.sections)

    def test_loads_all_ten_sections(self):
        self.assertEqual(len(self.sections), 10)

    def test_chunk_count(self):
        self.assertEqual(len(self.chunks), 45)

    def test_chunk_ids_are_unique(self):
        ids = [c["chunk_id"] for c in self.chunks]
        self.assertEqual(len(ids), len(set(ids)))

    def test_known_chunks_exist(self):
        ids = {c["chunk_id"] for c in self.chunks}
        for expected in ["21cfr_11.10_e", "21cfr_11.3_b_5", "21cfr_11.10_intro", "21cfr_11.1_i"]:
            self.assertIn(expected, ids)

    def test_every_chunk_has_required_fields(self):
        for chunk in self.chunks:
            for field in ["chunk_id", "citation", "section", "subpart", "text", "embed_text"]:
                self.assertTrue(chunk[field], f"{chunk['chunk_id']} is missing {field}")


if __name__ == "__main__":
    unittest.main()

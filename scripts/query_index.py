"""
Smoke test for the vector index: embeds a question, asks Chroma for the
closest chunks, and prints them. Run scripts/build_index.py first.

Usage: python -m scripts.query_index "your question here"
"""

import re
import sys

from dotenv import load_dotenv

load_dotenv()

from src.embedder import embed_query
from src.vector_store import query

DEFAULT_QUESTION = "What are the requirements for audit trails?"
PREVIEW_CHARS = 100
PARAGRAPH_LABEL = re.compile(r"\(([a-z])\)$")  # the "(e)" in "21 CFR 11.10(e)"


def make_preview(doc: str, citation: str) -> str:
    """
    Returns the start of the chunk's own content, skipping the heading and
    lead-in sentence that chunker.py prepends to every lettered chunk.
    """
    label = PARAGRAPH_LABEL.search(citation)
    # Lettered chunk: jump to its "(e)" paragraph. Otherwise: just skip the heading line.
    marker = f"\n({label.group(1)})" if label else "\n"
    start = doc.find(marker)
    body = doc[start + 1:] if start != -1 else doc
    return body[:PREVIEW_CHARS].replace("\n", " ")


def search(question: str) -> None:
    results = query(embed_query(question))

    # Chroma returns one list per query; we sent one query, so take [0].
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    documents = results["documents"][0]

    print(f"Q: {question}\n")
    for rank, (meta, dist, doc) in enumerate(zip(metadatas, distances, documents), start=1):
        print(f"{rank}. {meta['citation']}  (distance {dist:.3f})")
        print(f"   {make_preview(doc, meta['citation'])}...\n")


if __name__ == "__main__":
    search(" ".join(sys.argv[1:]) or DEFAULT_QUESTION)

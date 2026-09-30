"""
Retrieval: finds the chunks most similar to a question.
Embeds the question, asks Chroma for the closest chunks, and flattens
Chroma's nested result into one plain dict per chunk.
"""

from src.embedder import embed_query
from src.vector_store import query

TOP_K = 6


def retrieve(question: str, k: int = TOP_K) -> list[dict]:
    """
    Returns the k closest chunks, best match first:
    {"chunk_id": "21cfr_11.10_e", "citation": "21 CFR 11.10(e)",
     "text": "...", "distance": 1.008}
    """
    results = query(embed_query(question), n_results=k)

    # Chroma returns one list per query; we sent one query, so take [0].
    return [
        {"chunk_id": chunk_id, "citation": meta["citation"], "text": text, "distance": distance}
        for chunk_id, meta, text, distance in zip(
            results["ids"][0],
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0],
        )
    ]

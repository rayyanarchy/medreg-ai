"""
Retrieval: finds the chunks most relevant to a question.
Embeds the question, fetches a wider set of candidates from Chroma, then
picks the final chunks with MMR (maximal marginal relevance) so that
near-duplicate paragraphs don't take every slot.
"""

import math

from src.embedder import embed_query
from src.vector_store import query

TOP_K = 6
FETCH_K = 20  # candidates fetched from Chroma for MMR to choose from
MMR_LAMBDA = 0.8  # 1.0 = relevance only (plain top-k); lower = more diversity


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """1.0 = same direction (same meaning), 0.0 = unrelated."""
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.hypot(*a) * math.hypot(*b))


def select_mmr(
    query_embedding: list[float], candidates: list[dict], k: int, mmr_lambda: float
) -> list[dict]:
    """
    Picks k candidates one at a time. Each pick maximises
        mmr_lambda * (similarity to the question)
        - (1 - mmr_lambda) * (similarity to the closest chunk already picked)
    so a chunk that repeats an earlier pick is pushed down the order.
    """
    relevance = [cosine_similarity(query_embedding, c["embedding"]) for c in candidates]
    redundancy = [0.0] * len(candidates)  # similarity to the closest chunk picked so far
    remaining = list(range(len(candidates)))
    picked = []

    while remaining and len(picked) < k:
        best = max(
            remaining,
            key=lambda i: mmr_lambda * relevance[i] - (1 - mmr_lambda) * redundancy[i],
        )
        remaining.remove(best)
        picked.append(best)
        for i in remaining:
            similarity = cosine_similarity(candidates[i]["embedding"], candidates[best]["embedding"])
            redundancy[i] = max(redundancy[i], similarity)

    return [candidates[i] for i in picked]


def retrieve_by_vector(
    query_embedding: list[float], k: int = TOP_K, mmr_lambda: float = MMR_LAMBDA
) -> list[dict]:
    """Same as retrieve(), for a question that is already embedded."""
    results = query(query_embedding, n_results=max(FETCH_K, k), include_embeddings=True)

    # Chroma returns one list per query; we sent one query, so take [0].
    candidates = [
        {
            "chunk_id": chunk_id,
            "citation": meta["citation"],
            "text": text,
            "distance": distance,
            "embedding": embedding,
        }
        for chunk_id, meta, text, distance, embedding in zip(
            results["ids"][0],
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0],
            results["embeddings"][0],
        )
    ]

    picked = select_mmr(query_embedding, candidates, k, mmr_lambda)
    for chunk in picked:
        del chunk["embedding"]  # 1,536 numbers the caller doesn't need
    return picked


def retrieve(question: str, k: int = TOP_K) -> list[dict]:
    """
    Returns k chunks in the order MMR picked them (most relevant first):
    {"chunk_id": "21cfr_11.10_e", "citation": "21 CFR 11.10(e)",
     "text": "...", "distance": 1.008}
    """
    return retrieve_by_vector(embed_query(question), k)

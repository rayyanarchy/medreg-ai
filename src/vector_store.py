"""
Chroma vector store: stores chunk embeddings + metadata, and returns
the chunks closest to a query vector. Persists to disk at db/chroma.
"""

import chromadb

PERSIST_DIR = "db/chroma"
COLLECTION_NAME = "part11_chunks"

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=PERSIST_DIR)
    return _client


def get_collection():
    return _get_client().get_or_create_collection(name=COLLECTION_NAME)


def reset_collection():
    """Deletes the collection so a rebuild starts clean (no stale chunks)."""
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # didn't exist yet
    return client.get_or_create_collection(name=COLLECTION_NAME)


def add_chunks(chunks: list[dict], embeddings: list[list[float]], collection=None):
    collection = collection or get_collection()
    collection.upsert(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[
            {"section": c["section"], "subpart": c["subpart"], "citation": c["citation"]}
            for c in chunks
        ],
    )


def query(
    query_embedding: list[float], n_results: int = 4, include_embeddings: bool = False
) -> dict:
    """Returns the closest chunks; pass include_embeddings=True to also get their vectors."""
    include = ["documents", "metadatas", "distances"]
    if include_embeddings:
        include.append("embeddings")
    return get_collection().query(
        query_embeddings=[query_embedding], n_results=n_results, include=include
    )
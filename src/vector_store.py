"""
Chroma vector store: stores chunk embeddings + their metadata, and
answers "which stored chunks are closest to this query vector."
Persists to disk at db/chroma so the index survives restarts.
"""

import chromadb

PERSIST_DIR = "db/chroma"
COLLECTION_NAME = "medreg_chunks"

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=PERSIST_DIR)
    return _client


def get_collection():
    """Returns the collection that stores chunk embeddings, creating it if needed."""
    return _get_client().get_or_create_collection(name=COLLECTION_NAME)


def add_chunks(chunks: list[dict], embeddings: list[list[float]]):
    """
    Stores a batch of chunks + their embeddings.
    Uses upsert (not add) so rerunning this script is safe — it overwrites
    a chunk with the same id instead of erroring on duplicates.
    """
    collection = get_collection()
    collection.upsert(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "page": c["page"]} for c in chunks],
    )


def query(query_embedding: list[float], n_results: int = 5) -> dict:
    """Finds the n_results chunks closest to the given query vector."""
    collection = get_collection()
    return collection.query(query_embeddings=[query_embedding], n_results=n_results)
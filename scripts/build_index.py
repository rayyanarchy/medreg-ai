"""
Builds the vector index: parsed sections -> chunks -> embeddings -> Chroma.
Rerun whenever data/processed/part_11.json or chunker.py changes.
"""

from dotenv import load_dotenv

load_dotenv()

from src.loader import load_sections
from src.chunker import make_chunks
from src.embedder import embed_texts
from src.vector_store import reset_collection, add_chunks


def build():
    sections = load_sections()
    chunks = make_chunks(sections)
    print(f"{len(sections)} sections -> {len(chunks)} chunks")

    collection = reset_collection()
    embeddings = embed_texts([c["text"] for c in chunks])  # 37 chunks: one API call
    add_chunks(chunks, embeddings, collection)

    print(f"Stored {collection.count()} chunks in Chroma.")


if __name__ == "__main__":
    build()

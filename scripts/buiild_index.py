"""
Builds the vector index: processed Markdown -> chunks -> embeddings -> Chroma.
Rerun this whenever ingestion/processed/ changes (new or edited PDFs).
"""

from dotenv import load_dotenv

load_dotenv()

from src.loader import load_markdown
from src.chunker import chunk_records
from src.embedder import embed_texts
from src.vector_store import add_chunks

BATCH_SIZE = 100


def build():
    pages = load_markdown("ingestion/processed")
    chunks = chunk_records(pages)
    print(f"{len(pages)} pages -> {len(chunks)} chunks")

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        embeddings = embed_texts(texts)
        add_chunks(batch, embeddings)
        print(f"  stored chunks {i}-{i + len(batch)} of {len(chunks)}")

    print("Done.")


if __name__ == "__main__":
    build()

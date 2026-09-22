def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Splits text into word-based chunks with overlap.
    chunk_size / overlap are in words, not characters — easier to reason about.
    """
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap  # step forward, but re-cover the overlap
    return chunks


def chunk_records(records: list[dict], chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """
    Applies chunk_text to every page record, keeping source/page metadata
    and adding a chunk_id so you can reference a specific chunk later.
    """
    chunked = []
    for record in records:
        pieces = chunk_text(record["text"], chunk_size, overlap)
        for i, piece in enumerate(pieces):
            chunked.append({
                "chunk_id": f"{record['source']}_p{record['page']}_c{i}",
                "source": record["source"],
                "page": record["page"],
                "text": piece,
            })
    return chunked

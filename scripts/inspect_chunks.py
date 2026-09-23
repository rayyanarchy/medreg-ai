from collections import Counter
from src.loader import load_markdown
from src.chunker import chunk_records

pages = load_markdown("ingestion/processed")
chunks = chunk_records(pages)

per_file = Counter(p["source"] for p in pages)
for source, count in per_file.items():
    print(f"{source}: {count} pages")

print(len(pages), "pages ->", len(chunks), "chunks")
print(chunks[0])

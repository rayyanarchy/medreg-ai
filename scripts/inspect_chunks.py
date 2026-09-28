from src.loader import load_sections
from src.chunker import make_chunks

sections = load_sections()
chunks = make_chunks(sections)

print(f"{len(sections)} sections -> {len(chunks)} chunks\n")

for c in chunks:
    words = len(c["text"].split())
    print(f"{c['chunk_id']:<22} {c['citation']:<20} {words:>4} words")

# Full text of one chunk, to eyeball the content
target = next((c for c in chunks if c["section"] == "11.10"), chunks[0])
print("\n--- sample chunk ---")
print(target["text"])

# MedReg AI

A Retrieval-Augmented Generation (RAG) system for asking natural-language questions against medical regulatory documents. Currently scoped to a single corpus: **21 CFR Part 11** (Electronic Records; Electronic Signatures), sourced directly from the eCFR API.

## Tech Stack

- **Ingestion:** custom XML parsing (eCFR API)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Vector store:** Chroma
- **Serving:** FastAPI (planned)
- **Deployment:** Docker (planned)

## How to Run

```bash
git clone https://github.com/rayyanarchy/medreg-ai.git
cd medreg-ai
uv sync

# fetch raw XML from eCFR
python ingestion/fetch_ecfr.py

# parse into structured JSON
python ingestion/parse_ecfr.py

# load + chunk
python src/chunker.py
```

## What's Working

- Fetches 21 CFR Part 11 as XML from the eCFR API (`ingestion/fetch_ecfr.py`)
- Parses raw XML into structured JSON (`ingestion/parse_ecfr.py`)
- Loads and chunks by section/subsection boundary, using the XML's `SECTION` / `SECTNO` / `SUBJECT` tags rather than fixed word-count chunks (`src/loader.py`, `src/chunker.py`)

## Roadmap

- [ ] Generate and store embeddings (`src/embedder.py`)
- [ ] Index chunks in Chroma (`src/vector_store.py`)
- [ ] Retrieval + answer generation
- [ ] Build and run self-generated eval set (Q&A pairs, hand-reviewed)
- [ ] FastAPI serving layer
- [ ] Docker containerization

## License

This project is open source and available under the [MIT License](LICENSE).

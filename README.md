# MedReg AI

A Retrieval-Augmented Generation (RAG) system for asking natural-language questions against medical regulatory documents. Currently scoped to a single corpus: **21 CFR Part 11** (Electronic Records; Electronic Signatures), sourced directly from the eCFR API.

## Tech Stack

- **Ingestion:** custom XML parsing (eCFR API)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Vector store:** Chroma
- **Answer generation:** OpenAI `gpt-4o-mini`
- **Serving:** FastAPI + uvicorn
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

# load + chunk (prints every chunk ID, citation and word count)
python -m scripts.inspect_chunks

# add your OpenAI key to a .env file in the project root
echo "OPENAI_API_KEY=your-key-here" > .env

# embed the chunks and store them in Chroma (persists to db/chroma)
python -m scripts.build_index

# ask the index a question and print the closest chunks
python -m scripts.query_index "What are the requirements for audit trails?"

# get a cited answer (retrieve top 6 chunks, then generate)
python -m scripts.ask "What are the requirements for audit trails?"

# score retrieval against the eval set (hit rate and MRR)
python -m scripts.run_eval

# serve the API, then open http://127.0.0.1:8000/docs to try it
uvicorn src.api:app --reload
```

Example request:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the requirements for audit trails?"}'
```

```json
{
  "question": "What are the requirements for audit trails?",
  "answer": "... Audit trail documentation must be retained ... [1].",
  "sources": [{"number": 1, "citation": "21 CFR 11.10(e)"}]
}
```

## What's Working

- Fetches 21 CFR Part 11 as XML from the eCFR API (`ingestion/fetch_ecfr.py`)
- Parses raw XML into structured JSON (`ingestion/parse_ecfr.py`)
- Loads and chunks by section/subsection boundary, using the XML's `SECTION` / `SECTNO` / `SUBJECT` tags rather than fixed word-count chunks. Long sections split by lettered paragraph, and the definitions list by numbered item, giving 45 chunks (`src/loader.py`, `src/chunker.py`)
- Embeds chunks with OpenAI `text-embedding-3-small` (`src/embedder.py`)
- Stores embeddings, chunk text and citation metadata in a persistent Chroma collection, and returns the closest chunks for a question (`src/vector_store.py`, `scripts/build_index.py`, `scripts/query_index.py`)
- Retrieves 20 candidates and picks 6 with MMR (maximal marginal relevance), so near-duplicate paragraphs don't crowd out the right one (`src/retriever.py`)
- Answers questions from the 6 retrieved chunks only, with numbered references back to the CFR paragraph, and says so when the regulation doesn't cover the question (`src/retriever.py`, `src/generator.py`, `scripts/ask.py`)
- Scores retrieval against a 25-question eval set covering all 10 sections, including out-of-scope questions (`eval/eval_set.json`, `scripts/run_eval.py`). Current result: 100% hit rate @ 6 and MRR 0.802 on the 23 in-scope questions, up from 87% and 0.757 before the chunking and MMR changes
- Serves the pipeline over HTTP: `POST /ask` returns the answer plus a structured sources list, `GET /health` reports status, and questions are validated (1–500 characters) before any model call (`src/api.py`)

## Roadmap

- [x] Generate and store embeddings (`src/embedder.py`)
- [x] Index chunks in Chroma (`src/vector_store.py`)
- [x] Retrieval + answer generation (`src/retriever.py`, `src/generator.py`)
- [x] Build and run self-generated eval set for retrieval (`eval/eval_set.json`, `scripts/run_eval.py`)
- [x] Improve retrieval on the eval misses (chunking fixes + MMR)
- [ ] Add answer-level eval checks (citation correctness, refusal, faithfulness)
- [x] FastAPI serving layer (`src/api.py`)
- [ ] Docker containerization

## License

This project is open source and available under the [MIT License](LICENSE).

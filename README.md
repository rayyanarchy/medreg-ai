# MedReg AI

A Retrieval-Augmented Generation (RAG) system for asking natural-language questions against medical regulatory documents. Currently scoped to a single corpus: **21 CFR Part 11** (Electronic Records; Electronic Signatures), sourced directly from the eCFR API.

## Tech Stack

- **Ingestion:** custom XML parsing (eCFR API)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Vector store:** Chroma
- **Answer generation:** OpenAI `gpt-4o-mini`
- **Serving:** FastAPI + uvicorn
- **Deployment:** Docker + Docker Compose

## How to Run

```bash
git clone https://github.com/rayyanarchy/medreg-ai.git
cd medreg-ai
uv sync

# add your OpenAI key to a .env file in the project root
echo "OPENAI_API_KEY=your-key-here" > .env

# fetch raw XML from eCFR, then parse it into structured JSON
# (both outputs are already committed under data/, so this is optional)
uv run python ingestion/fetch_ecfr.py
uv run python ingestion/parse_ecfr.py

# load + chunk (prints every chunk ID, citation and word count)
uv run python -m scripts.inspect_chunks

# run the unit tests (offline, no API key needed)
uv run python -m unittest discover tests

# embed the chunks and store them in Chroma (persists to db/chroma)
uv run python -m scripts.build_index

# ask the index a question and print the closest chunks
uv run python -m scripts.query_index "What are the requirements for audit trails?"

# get a cited answer (retrieve 6 chunks, then generate)
uv run python -m scripts.ask "What are the requirements for audit trails?"

# score retrieval against the eval set (hit rate and MRR)
uv run python -m scripts.run_eval

# score full answers (citations, right source, refusals); --rescore re-scores saved answers for free
uv run python -m scripts.run_answer_eval

# serve the API, then open http://127.0.0.1:8000/docs to try it
uv run uvicorn src.api:app --reload
```

Scripts under `scripts/` import from `src`, so run them from the repo root as modules (`-m`). Everything from `build_index` down calls the OpenAI API and costs a little: one embedding call per question, plus one chat call when an answer is generated.

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

### With Docker

The image holds the code and dependencies only. Your API key is read from `.env` when the container starts, and the Chroma index lives in `./db` on your machine, mounted into the container.

```bash
# build the image and the index (the index only needs rebuilding when chunking changes)
docker compose build
docker compose run --rm api python -m scripts.build_index

# start the API on http://127.0.0.1:8000 (docs at /docs), and stop it
docker compose up -d
docker compose down
```

## How It Works

```
eCFR API ──fetch──▶ data/raw (XML) ──parse──▶ data/processed (JSON) ──chunk──▶ embed ──▶ Chroma
                                                                                            │
                user question ──▶ FastAPI ──▶ embed ──▶ 20 candidates ──▶ MMR picks 6 ──────┘
                                                                              │
                                                       gpt-4o-mini ◀──────────┘
                                                            │
                                         answer with [n] markers + Sources list built by code
```

### Key decisions

**Chunk by regulatory structure, not by word count.** The eCFR XML marks every section (`SECTNO`, `SUBJECT`), so chunks follow the regulation itself. Short sections stay whole, long ones split by lettered paragraph — (a), (b), (c) — and the long definitions list in § 11.3(b) splits again by numbered item. Each chunk then maps to exactly one citable paragraph, such as `21 CFR 11.10(e)`. Fixed-size windows were ruled out because they cut paragraphs in half and make citations vague.

**Embed one text, show the LLM another.** Many paragraphs in § 11.10 share a lead-in ("Persons who use closed systems ... shall ..."). With the lead-in included, sibling chunks embedded almost identically and crowded each other out. Each chunk now keeps two versions: `embed_text` (heading + paragraph) for search, and `text` (heading + lead-in + paragraph) for the LLM, so the model still gets the full sentence.

**MMR instead of plain top-k.** Retrieval fetches 20 candidates from Chroma and uses maximal marginal relevance to pick 6: each pick weighs relevance to the question against similarity to chunks already picked. Lambda 0.8 came from a sweep on the eval set. 0.7–0.9 all scored 23/23, and 0.6 and below started dropping correct paragraphs.

**Citations are checked by code, not trusted from the model.** The LLM writes `[1]`, `[2]` markers at the end of each sentence. The `Sources:` list is built in code from the chunks that were actually retrieved, and markers that point at no chunk are dropped, so the model can't invent a citation. The system prompt includes a made-up worked example, because a written rule alone let `gpt-4o-mini` bunch every citation at the end of broad answers.

**Fail cheaply and safely in the API.** Questions are validated (1–500 characters) before any paid model call. OpenAI errors return a generic 502 with details in the server log. The Docker image never contains the API key or the index, and the port is bound to `127.0.0.1` only, because every `/ask` costs tokens.

### Evaluation

The eval set has 25 questions written from the Part 11 text and reviewed by hand: 23 in scope across all 10 sections, plus 2 out of scope that should be refused. A retrieval hit means an expected citation appears in the top 6.

| Retrieval change | Hit rate @ 6 | MRR |
|---|---|---|
| Plain top-6, original chunks | 87% (20/23) | 0.757 |
| + lead-in-free embeddings, definitions split by item | 96% (22/23) | 0.793 |
| + MMR (lambda 0.8) | **100% (23/23)** | **0.802** |

Answer-level results on the same set: 23/23 answers cite an expected source, 2/2 out-of-scope questions refused, 0 false refusals, 0 invalid citation markers, and 87% of sentences (41/47) carry a citation. The scored answers are committed in `eval/answers.json`, so each number traces back to the exact text it came from.

### Known limitations

- **Multi-part questions.** q22 asks about open *and* closed systems, but retrieval returned only closed-system chunks, so the answer covers half the question. It still counts as a retrieval hit, because one expected citation matched.
- **No faithfulness check yet.** The answer eval confirms that sentences cite the right paragraph, but not that the paragraph actually supports the sentence. That needs an LLM judge.
- **Single corpus.** Only 21 CFR Part 11 (45 chunks). No similarity threshold or reranking, because the eval hasn't shown a need for them at this size.

## What's Working

- Fetches 21 CFR Part 11 as XML from the eCFR API (`ingestion/fetch_ecfr.py`)
- Parses raw XML into structured JSON (`ingestion/parse_ecfr.py`)
- Loads and chunks by section/subsection boundary, using the XML's `SECTION` / `SECTNO` / `SUBJECT` tags rather than fixed word-count chunks. Long sections split by lettered paragraph, and the definitions list by numbered item, giving 45 chunks (`src/loader.py`, `src/chunker.py`)
- Embeds chunks with OpenAI `text-embedding-3-small` (`src/embedder.py`)
- Stores embeddings, chunk text and citation metadata in a persistent Chroma collection, and returns the closest chunks for a question (`src/vector_store.py`, `scripts/build_index.py`, `scripts/query_index.py`)
- Retrieves 20 candidates and picks 6 with MMR (maximal marginal relevance), so near-duplicate paragraphs don't crowd out the right one (`src/retriever.py`)
- Answers questions from the 6 retrieved chunks only, with numbered references back to the CFR paragraph, and says so when the regulation doesn't cover the question (`src/retriever.py`, `src/generator.py`, `scripts/ask.py`)
- Scores retrieval against a 25-question eval set covering all 10 sections, including out-of-scope questions (`eval/eval_set.json`, `scripts/run_eval.py`). Current result: 100% hit rate @ 6 and MRR 0.802 on the 23 in-scope questions, up from 87% and 0.757 before the chunking and MMR changes
- Scores the generated answers on the same set (`scripts/run_answer_eval.py`, answers saved in `eval/answers.json`). Current result: all 23 in-scope answers cite an expected paragraph, both out-of-scope questions are refused, no false refusals or invented source numbers, and 87% of sentences carry a citation
- Serves the pipeline over HTTP: `POST /ask` returns the answer plus a structured sources list, `GET /health` reports status, and questions are validated (1–500 characters) before any model call (`src/api.py`)
- Unit tests for loading and chunking, run offline with the standard-library `unittest` (`tests/test_loader_chunker.py`)
- Runs in Docker: a `python:3.13-slim` image with dependencies installed from `uv.lock`, running as a non-root user with a health check. The API key and the index stay outside the image (`Dockerfile`, `compose.yaml`)

## Roadmap

- [x] Generate and store embeddings (`src/embedder.py`)
- [x] Index chunks in Chroma (`src/vector_store.py`)
- [x] Retrieval + answer generation (`src/retriever.py`, `src/generator.py`)
- [x] Build and run self-generated eval set for retrieval (`eval/eval_set.json`, `scripts/run_eval.py`)
- [x] Improve retrieval on the eval misses (chunking fixes + MMR)
- [x] Add answer-level eval checks (citation coverage, right source, refusals) (`scripts/run_answer_eval.py`)
- [ ] Faithfulness check (LLM judge: is each sentence supported by the paragraph it cites?)
- [ ] Handle multi-part questions (q22 retrieved only the closed-system half of an open-vs-closed question)
- [x] FastAPI serving layer (`src/api.py`)
- [x] Docker containerization (`Dockerfile`, `compose.yaml`)

## License

This project is open source and available under the [MIT License](LICENSE).

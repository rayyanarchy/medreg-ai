# MedReg AI

RAG (retrieval-augmented generation) Q&A assistant over **21 CFR Part 11** (FDA rules for electronic records and electronic signatures). Portfolio project targeting entry-level AI Engineer roles in regulated healthcare/medtech.

## How to work with me — learning mode (read this first)

My main goal is to **understand** the concepts that make a strong AI Engineer, not just ship code. I'm also rusty with Python and rebuilding fluency.

- **Plan before code.** For anything non-trivial, explain the approach step by step and wait for my go-ahead before editing files.
- **Flag new concepts.** When you use an idea, library feature, or Python construct I may not know, mark it as `New concept: <name>` and explain it in 1–3 plain sentences *before* the code that uses it (e.g. generators, context managers, dataclasses, cosine similarity, HNSW, dependency injection in FastAPI).
- **Show your reasoning on hard problems** — trade-offs, what you ruled out, and why.
- **Small steps.** One file or one function at a time, small reviewable diffs. Explain *why* each change, not just *what*.
- **Give me reps.** When a task is small and a good learning exercise, offer me the choice to write it myself with hints first.
- **Idiomatic, readable Python.** Type hints, `pathlib`, docstrings, clear names. Point out the idiom when you use one.
- **Always tell me how to run and verify** what you just wrote.
- **Ask before scope forks.** If a choice meaningfully changes scope or architecture (e.g. swap a library, add a framework, restructure folders), present the options and let me decide. Don't decide silently.
- Don't commit, push, or install new dependencies without asking.

## Pipeline

```
eCFR API ──fetch──▶ data/raw (XML) ──parse──▶ data/processed ──load──▶ chunk ──▶ embed ──▶ Chroma
                                                                                             │
                              user question ──▶ FastAPI ──▶ retrieve top-k ──▶ LLM answer ◀──┘
```

## Status

**Working**
- Ingestion: `ingestion/fetch_ecfr.py`, `ingestion/parse_ecfr.py`
- Chunking: `src/loader.py`, `src/chunker.py` (inspect with `scripts/inspect_chunks.py`)
- Embedding: `src/embedder.py` — OpenAI `text-embedding-3-small`
- Vector store: `src/vector_store.py` — Chroma, persisted to `db/chroma`
- Index build + smoke test: `scripts/build_index.py`, `scripts/query_index.py`
- Retrieval: `src/retriever.py` — top-k chunks as plain dicts
- Answer generation: `src/generator.py` — grounded answer with `[n]` references; end to end via `scripts/ask.py`

**Next up (in order)**
1. Evaluation set + eval script
2. FastAPI serving
3. Docker

When something moves from "Next up" to "Working", also update the README: strike it off **Roadmap** and add it to **What's Working**.

## Settled decisions — don't re-open without asking

- **Corpus:** only 21 CFR Part 11, fetched as XML from the eCFR API. The old 8-PDF pipeline was removed on purpose — do not reintroduce PDF loaders.
- **eCFR gotcha:** the `/api/versioner/v1/full/{date}/...` endpoint returns **404 for `current`**. Resolve an explicit date (YYYY-MM-DD) first, then fetch.
- **Chunking:** by regulatory structure using the XML's `SECTION` / `SECTNO` / `SUBJECT` tags, not fixed word counts. Long sections are split by lettered paragraph — (a), (b), (c)…; short sections stay as a single chunk. Keep section number and subject as chunk metadata so answers can be traced to the regulation.
- **Stack:** OpenAI `text-embedding-3-small`, Chroma, FastAPI, Docker.
- **Eval set:** self-generated from the Part 11 text (LLM-drafted, then hand-reviewed by me), not an off-the-shelf benchmark.
- **Data layout:** raw fetched files → `data/raw/`, parsed output → `data/processed/`. `ingestion/` holds scripts only.
- **README sections:** Tech Stack, How to Run, What's Working, Roadmap (checklist), License. License is MIT.
- **Chroma:** collection `part11_chunks`, persisted to `db/chroma` (git-ignored). Chunk IDs are `21cfr_<section>` for a whole section, `21cfr_<section>_<letter>` for a lettered paragraph, and `21cfr_<section>_intro` for a lead-in — e.g. `21cfr_11.10_e`. Metadata per chunk: `section`, `subpart`, `citation`.

- **Answer generation:** OpenAI `gpt-4o-mini`, temperature 0. The OpenAI project behind the key only allows models enabled under its Limits settings (currently `text-embedding-3-small` and `gpt-4o-mini`).
- **Citation format:** numbered references — `[1]`, `[2]` in the answer, then a `Sources:` list mapping each number to its CFR citation. The list is built by code from the retrieved chunks, never written by the LLM.
- **Retrieval:** top-k = 6, no similarity threshold, no reranking. Revisit threshold/reranking only once the eval set can measure them.

## Open decisions — ask me when we get there

- Whether to add a similarity threshold or reranking (decide from eval results)
- Eval metrics (e.g. retrieval hit rate, answer faithfulness) and how many questions

## Conventions

- Secrets (`OPENAI_API_KEY`) live in `.env`, loaded at runtime. Never hard-code or commit keys.
- Don't commit generated embeddings or the Chroma persistence directory unless I ask.
- Keep modules small and single-purpose; each script should be runnable on its own for testing.

## Commands

Run everything from the repo root. Scripts under `scripts/` import from `src`, so run them as modules (`-m`), not as files.

- Setup: `uv sync`, then put `OPENAI_API_KEY=...` in `.env`
- Fetch + parse: `uv run python ingestion/fetch_ecfr.py` then `uv run python ingestion/parse_ecfr.py`
- Chunk (inspect): `uv run python -m scripts.inspect_chunks`
- Build index: `uv run python -m scripts.build_index`
- Query index: `uv run python -m scripts.query_index "your question"`
- Ask (retrieve + answer): `uv run python -m scripts.ask "your question"`
- Run API: `...`

"""
HTTP API: serves the RAG pipeline as a web service.
POST /ask answers a question about 21 CFR Part 11 with numbered sources;
GET /health reports that the service is up.

Run: uvicorn src.api:app --reload   (then open http://127.0.0.1:8000/docs)
"""

import logging

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from openai import OpenAIError
from pydantic import BaseModel, ConfigDict, Field

from src.generator import cited_sources, generate_answer
from src.retriever import retrieve

MAX_QUESTION_CHARS = 500

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MedReg AI",
    description="Answers questions about 21 CFR Part 11 with citations to the regulation.",
)


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # "   " counts as empty

    question: str = Field(
        min_length=1,
        max_length=MAX_QUESTION_CHARS,
        examples=["What are the requirements for audit trails?"],
    )


class Source(BaseModel):
    number: int
    citation: str


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[Source]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask")
def ask(request: AskRequest) -> AskResponse:
    try:
        chunks = retrieve(request.question)
        answer = generate_answer(request.question, chunks)
    except OpenAIError:
        # Log the details for us; don't send OpenAI's error text to the caller.
        logger.exception("OpenAI request failed")
        raise HTTPException(status_code=502, detail="The language model service failed. Try again.")

    return AskResponse(
        question=request.question,
        answer=answer,
        sources=[Source(number=n, citation=c) for n, c in cited_sources(answer, chunks)],
    )

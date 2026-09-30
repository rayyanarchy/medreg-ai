"""
Answer generation: asks the LLM to answer a question using only the
retrieved chunks, citing them as [1], [2], ... The sources list shown to
the user is built here from the retrieved chunks, never written by the LLM,
so a citation can only point at text that was actually retrieved.
"""

import os
import re

from openai import OpenAI

MODEL = "gpt-4o-mini"
CITATION_MARKER = re.compile(r"\[(\d+)\]")

SYSTEM_PROMPT = """\
You answer questions about 21 CFR Part 11, the FDA rules on electronic \
records and electronic signatures.

Rules:
- Use only the numbered sources in the user's message. Do not use outside knowledge.
- After each claim, cite the source it came from in square brackets, like [1] or [2][3].
- If the sources do not contain the answer, say so plainly and do not guess.
- Be concise. Do not write a sources list; one is added separately."""

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Add it to a .env file or your environment."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def build_context(chunks: list[dict]) -> str:
    """Numbers the chunks from 1 so the LLM can cite them as [1], [2], ..."""
    return "\n\n".join(
        f"[{number}] {chunk['citation']}\n{chunk['text']}"
        for number, chunk in enumerate(chunks, start=1)
    )


def generate_answer(question: str, chunks: list[dict]) -> str:
    """Returns the LLM's answer, with [n] markers pointing at `chunks`."""
    response = _get_client().chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Sources:\n{build_context(chunks)}\n\nQuestion: {question}",
            },
        ],
    )
    return response.choices[0].message.content.strip()


def cited_sources(answer: str, chunks: list[dict]) -> list[tuple[int, str]]:
    """
    Returns (number, citation) for each source the answer actually cites,
    in number order. Markers that don't match a retrieved chunk are dropped.
    """
    numbers = {int(n) for n in CITATION_MARKER.findall(answer)}
    return [
        (n, chunks[n - 1]["citation"])
        for n in sorted(numbers)
        if 1 <= n <= len(chunks)
    ]

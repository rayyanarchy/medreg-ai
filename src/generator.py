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
- End every sentence that states a fact with the source(s) that sentence \
relies on, in square brackets, like [1] or [2][3]. Cite only the sources \
that support that sentence.
- Never collect citations at the end of the answer or of a paragraph.
- If the sources do not contain the answer, say so plainly and do not guess.
- Be concise. Do not write a sources list; one is added separately.

Example of the citation format. The topic is made up; only copy the format.
Sources:
[1] Policy 2(a) Members may borrow up to five books at a time.
[2] Policy 2(b) Loans last three weeks and can be renewed once.
[3] Policy 4 Overdue items are fined daily.
Question: What are the borrowing rules?
Correct: Members can borrow up to five books at a time [1]. Each loan \
lasts three weeks and can be renewed once [2]. Late returns are fined daily [3].
Wrong: Members can borrow up to five books for three weeks, with renewals \
and fines for late returns [1][2][3]."""

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

"""
Asks a question end to end: retrieve the closest chunks, generate a
grounded answer, and print it with its sources. Run scripts/build_index.py first.

Usage: python -m scripts.ask "your question here"
"""

import sys

from dotenv import load_dotenv

load_dotenv()

from src.generator import cited_sources, generate_answer
from src.retriever import retrieve

DEFAULT_QUESTION = "What are the requirements for audit trails?"


def ask(question: str) -> None:
    chunks = retrieve(question)
    answer = generate_answer(question, chunks)

    print(f"Q: {question}\n")
    print(answer)

    sources = cited_sources(answer, chunks)
    print("\nSources:")
    if not sources:
        print("(none cited)")
    for number, citation in sources:
        print(f"[{number}] {citation}")


if __name__ == "__main__":
    ask(" ".join(sys.argv[1:]) or DEFAULT_QUESTION)

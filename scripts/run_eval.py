"""
Retrieval eval: runs every eval question through retrieve() and checks
whether an expected citation came back. Reports hit rate and MRR.
Questions with no expected citations (out-of-scope ones) are skipped here;
they test answer refusal, not retrieval.

Usage: python -m scripts.run_eval [path/to/eval_set.json]
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.retriever import TOP_K, retrieve

DEFAULT_PATH = Path("eval/eval_set.json")


def first_hit_rank(expected: list[str], retrieved: list[str]) -> int | None:
    """Rank (1 = top result) of the first retrieved citation that is expected, or None."""
    for rank, citation in enumerate(retrieved, start=1):
        if citation in expected:
            return rank
    return None


def run(path: Path) -> None:
    eval_set = json.loads(path.read_text(encoding="utf-8"))
    questions = [q for q in eval_set if q["expected_citations"]]
    skipped = len(eval_set) - len(questions)

    ranks = []
    for q in questions:
        retrieved = [chunk["citation"] for chunk in retrieve(q["question"])]
        rank = first_hit_rank(q["expected_citations"], retrieved)
        ranks.append(rank)

        result = f"rank {rank}" if rank else "MISS"
        expected = q["expected_citations"][0]
        if len(q["expected_citations"]) > 1:
            expected += f" +{len(q['expected_citations']) - 1}"
        print(f"{q['id']}  {result:<7} {expected:<22} {q['question'][:70]}")

    hits = [rank for rank in ranks if rank]
    hit_rate = len(hits) / len(ranks)
    mrr = sum(1 / rank for rank in hits) / len(ranks)

    print(f"\n{path}: {len(ranks)} questions ({skipped} without expected citations skipped)")
    print(f"Hit rate @ {TOP_K}: {hit_rate:.0%}  ({len(hits)}/{len(ranks)})")
    print(f"MRR:          {mrr:.3f}")


if __name__ == "__main__":
    run(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH)

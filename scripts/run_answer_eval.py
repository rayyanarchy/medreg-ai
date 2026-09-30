"""
Answer-level eval: runs every eval question through the full pipeline
(retrieve -> generate) and scores the answers:
- citation coverage: share of sentences that end with a [n] marker
- right source: in-scope answers that cite at least one expected paragraph
- refusals: out-of-scope answers should cite nothing; an in-scope answer
  that cites nothing counts as a false refusal
- invalid markers: [n] numbers that don't match any retrieved chunk

Answers are saved to eval/answers.json so they can be re-scored for free.

Usage:
  python -m scripts.run_answer_eval            # fresh run: 1 embedding + 1 chat call per question
  python -m scripts.run_answer_eval --rescore  # score eval/answers.json again, no API calls
"""

import argparse
import json
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.generator import CITATION_MARKER, generate_answer
from src.retriever import retrieve

EVAL_SET_PATH = Path("eval/eval_set.json")
ANSWERS_PATH = Path("eval/answers.json")

# Whitespace after . ! or ? — except after abbreviations like "docket No. 92S-0251"
SENTENCE_BREAK = re.compile(r"(?<=[.!?])(?<!\bNo\.)(?<!e\.g\.)(?<!i\.e\.)\s+")
ENDS_WITH_CITATION = re.compile(r"(\[\d+\])+[.!?]?$")  # "... records [1]." or "[2][3]."
MIN_SENTENCE_WORDS = 4  # skips list numbers like "1." and other fragments


def generate_answers() -> list[dict]:
    """Runs every eval question through the pipeline and saves the results."""
    records = []
    for q in json.loads(EVAL_SET_PATH.read_text(encoding="utf-8")):
        chunks = retrieve(q["question"])
        records.append({
            "id": q["id"],
            "question": q["question"],
            "expected_citations": q["expected_citations"],
            "retrieved": [chunk["citation"] for chunk in chunks],  # [n] = retrieved[n - 1]
            "answer": generate_answer(q["question"], chunks),
        })
        print(f"answered {q['id']}")

    ANSWERS_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {len(records)} answers to {ANSWERS_PATH}\n")
    return records


def split_sentences(answer: str) -> list[str]:
    """Rough sentence split: by line first (lists), then after . ! or ?"""
    sentences = []
    for line in answer.splitlines():
        for sentence in SENTENCE_BREAK.split(line.strip()):
            if len(sentence.split()) >= MIN_SENTENCE_WORDS and not sentence.endswith(":"):
                sentences.append(sentence)
    return sentences


def score_answer(record: dict) -> dict:
    numbers = {int(n) for n in CITATION_MARKER.findall(record["answer"])}
    valid = {n for n in numbers if 1 <= n <= len(record["retrieved"])}
    cited = {record["retrieved"][n - 1] for n in valid}
    sentences = split_sentences(record["answer"])

    return {
        "in_scope": bool(record["expected_citations"]),
        "refused": not numbers,
        "right_source": bool(cited & set(record["expected_citations"])),
        "invalid_markers": len(numbers - valid),
        "sentences": len(sentences),
        "cited_sentences": sum(bool(ENDS_WITH_CITATION.search(s)) for s in sentences),
    }


def report(records: list[dict]) -> None:
    scores = [score_answer(r) for r in records]

    for record, s in zip(records, scores):
        if s["in_scope"]:
            verdict = "FALSE REFUSAL" if s["refused"] else ("right source" if s["right_source"] else "WRONG SOURCE")
        else:
            verdict = "refused" if s["refused"] else "ANSWERED OUT-OF-SCOPE"
        coverage = f"{s['cited_sentences']}/{s['sentences']}"
        invalid = f"  {s['invalid_markers']} invalid" if s["invalid_markers"] else ""
        print(f"{record['id']}  cited {coverage:<5} {verdict:<22}{invalid}  {record['question'][:55]}")

    in_scope = [s for s in scores if s["in_scope"]]
    out_of_scope = [s for s in scores if not s["in_scope"]]
    sentences = sum(s["sentences"] for s in in_scope)
    cited_sentences = sum(s["cited_sentences"] for s in in_scope)

    print(f"\n{len(in_scope)} in-scope, {len(out_of_scope)} out-of-scope answers")
    print(f"Citation coverage:  {cited_sentences / sentences:.0%}  ({cited_sentences}/{sentences} sentences, in-scope answers)")
    print(f"Right source:       {sum(s['right_source'] for s in in_scope)}/{len(in_scope)} in-scope answers")
    print(f"Refused correctly:  {sum(s['refused'] for s in out_of_scope)}/{len(out_of_scope)} out-of-scope answers")
    print(f"False refusals:     {sum(s['refused'] for s in in_scope)}")
    print(f"Invalid markers:    {sum(s['invalid_markers'] for s in scores)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score answers on the eval set.")
    parser.add_argument(
        "--rescore", action="store_true", help=f"score {ANSWERS_PATH} again without calling the API"
    )
    args = parser.parse_args()

    if args.rescore:
        records = json.loads(ANSWERS_PATH.read_text(encoding="utf-8"))
    else:
        records = generate_answers()
    report(records)

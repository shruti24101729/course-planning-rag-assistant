"""
main.py — Entry point for the MIT Course Planning RAG Assistant.

Usage:
  # Build index only
  python main.py --build-index

  # Run sample interactions
  python main.py --demo

  # Run full evaluation set
  python main.py --eval

  # Interactive mode
  python main.py --interactive
"""

import argparse
import json
import os
import sys

# Ensure src is on path
sys.path.insert(0, os.path.dirname(__file__))

from src.ingest import get_or_build_index
from src.chain import CoursePlanningAssistant


# ---------------------------------------------------------------------------
# Sample Interactions (3 required transcripts)
# ---------------------------------------------------------------------------

SAMPLE_INTERACTIONS = [

    # Transcript 1: Correct eligibility decision with citations
    {
        "label": "Transcript 1 — Prereq Eligibility Check (with citations)",
        "mode": "prereq",
        "completed_courses": ["6.009", "6.042J"],
        "grades": {"6.009": "B", "6.042J": "A"},
        "question": "Can I take 6.006 Introduction to Algorithms this semester?",
    },

    # Transcript 2: Course plan output with justification + citations
    {
        "label": "Transcript 2 — Course Plan Generation",
        "mode": "plan",
        "user_input": (
            "I am a sophomore in 6-3. I have completed 6.009 (A), 6.042J (B), "
            "18.01 (A), 18.02 (B), and 6.004 (B). I want to plan my Fall 2026 "
            "semester. My max load is 48 units. Catalog year 2025-2026. "
            "No transfer credits."
        ),
    },

    # Transcript 3: Correct abstention + guidance
    {
        "label": "Transcript 3 — Safe Abstention (not in catalog)",
        "mode": "auto",
        "user_input": "Is 6.006 definitely being offered in Fall 2026 and who is the professor?",
    },
]


def run_demo(assistant: CoursePlanningAssistant):
    """Run the 3 required sample transcripts."""
    print("\n" + "=" * 70)
    print("COURSE PLANNING ASSISTANT — SAMPLE INTERACTIONS")
    print("=" * 70)

    for i, sample in enumerate(SAMPLE_INTERACTIONS, 1):
        print(f"\n{'─' * 70}")
        print(f"  {sample['label']}")
        print(f"{'─' * 70}")

        if sample["mode"] == "prereq":
            result = assistant.run_prereq_check(
                completed_courses=sample["completed_courses"],
                grades=sample["grades"],
                question=sample["question"],
            )
            print(f"QUESTION: {sample['question']}")
            print(f"COMPLETED: {sample['completed_courses']}")
        else:
            result = assistant.run(sample["user_input"], mode=sample["mode"])
            print(f"INPUT: {sample['user_input'][:200]}...")

        print(f"\nRESPONSE:\n{result['response']}")
        print(f"\nAUDIT RESULT: {result.get('audit_result', 'N/A')}")
        citations = result.get("citations", result.get("citations_retrieved", []))
        print(f"CITATIONS RETRIEVED: {len(citations)}")
        for c in citations[:4]:
            print(f"  • {c}")
        print()


def run_evaluation(assistant: CoursePlanningAssistant):
    """Run the full 25-query evaluation set."""
    from evaluation.eval_queries import run_evaluation as _run_eval
    _run_eval(assistant, save_results=True)


def run_interactive(assistant: CoursePlanningAssistant):
    """Interactive REPL."""
    print("\n" + "=" * 60)
    print("MIT Course Planning Assistant — Interactive Mode")
    print("Type 'quit' to exit.")
    print("=" * 60 + "\n")

    completed: list[str] = []
    grades: dict = {}

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        # Simple mode detection
        if any(k in user_input.lower() for k in
               ["can i take", "eligible", "prerequisite", "prereq"]):
            result = assistant.run_prereq_check(
                completed_courses=completed,
                grades=grades,
                question=user_input,
            )
        else:
            result = assistant.run(user_input)

        if result.get("needs_clarification"):
            print(f"\nAssistant:\n{result['response']}\n")
            answer = input("Your answer: ").strip()
            result = assistant.run(user_input + "\n" + answer)

        print(f"\nAssistant:\n{result['response']}\n")
        citations = result.get("citations", result.get("citations_retrieved", []))
        if citations:
            print("Citations:")
            for c in citations[:4]:
                print(f"  • {c}")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="MIT Course Planning RAG Assistant"
    )
    parser.add_argument("--build-index", action="store_true",
                        help="Build (or rebuild) the FAISS vector index")
    parser.add_argument("--demo", action="store_true",
                        help="Run sample interactions (3 transcripts)")
    parser.add_argument("--eval", action="store_true",
                        help="Run the 25-query evaluation set")
    parser.add_argument("--interactive", action="store_true",
                        help="Launch interactive REPL")
    args = parser.parse_args()

    if args.build_index:
        print("[main] Building index...")
        get_or_build_index()
        print("[main] Done.")
        return

    print("[main] Initializing assistant...")
    assistant = CoursePlanningAssistant()

    if args.demo:
        run_demo(assistant)
    elif args.eval:
        run_evaluation(assistant)
    elif args.interactive:
        run_interactive(assistant)
    else:
        # Default: run demo
        run_demo(assistant)


if __name__ == "__main__":
    main()

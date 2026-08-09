"""Command-line interface.

Usage:
    python -m support_agent.cli "My scheduled exports stopped..." [--verbose] [--no-reranker]
    python -m support_agent.cli --all [--verbose]
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="support-agent", description="Pulseboard support agent network (fully local).")
    parser.add_argument("question", nargs="*", help="The support question to answer.")
    parser.add_argument("--all", action="store_true", help="Run all sample questions from data/sample_questions.json.")
    parser.add_argument("--verbose", action="store_true", help="Print per-node trace to stdout.")
    parser.add_argument("--no-reranker", action="store_true", help="Disable the cross-encoder reranker.")
    args = parser.parse_args(argv)

    from support_agent.runtime import SupportAgentRuntime, load_sample_questions

    runtime = SupportAgentRuntime(use_reranker=not args.no_reranker)

    if args.all:
        samples = load_sample_questions()
        for s in samples:
            print("\n" + "=" * 70)
            print(f"Q: {s['question']}")
            out = runtime.answer(s["question"], verbose=args.verbose)
            print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if not args.question:
        parser.print_help()
        return 2

    question = " ".join(args.question)
    out = runtime.answer(question, verbose=args.verbose)
    print("\n--- human-readable answer ---")
    print(out.get("answer", ""))
    print("\n--- structured output ---")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
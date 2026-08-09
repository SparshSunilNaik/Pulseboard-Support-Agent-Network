"""Run the CLI against all sample questions, saving genuine output to sample_outputs/.

This script drives the exact same code path as the CLI and writes, for each
question: a .json file (structured output) and a .txt file (readable answer).
Output is real program output — nothing is fabricated.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from support_agent import config
from support_agent.runtime import SupportAgentRuntime, load_sample_questions


def main() -> int:
    config.SAMPLE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    samples = load_sample_questions()
    runtime = SupportAgentRuntime(use_reranker=True)

    for s in samples:
        qid = s["id"]
        print(f"[{qid}] {s['question']}")
        out = runtime.answer(s["question"], verbose=True)

        json_path = config.SAMPLE_OUTPUT_DIR / f"{qid}.json"
        txt_path = config.SAMPLE_OUTPUT_DIR / f"{qid}.txt"
        json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        txt_path.write_text(
            f"QUESTION:\n{s['question']}\n\nANSWER:\n{out.get('answer', '')}\n\n"
            f"CLASSIFICATION: {out.get('classification')}\n"
            f"CONFIDENCE: {out.get('confidence')}\n"
            f"REQUIRES_HUMAN: {out.get('requires_human')}\n",
            encoding="utf-8",
        )
        print(f"  -> wrote {json_path.name}, {txt_path.name}")

    print("\nDone. See sample_outputs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
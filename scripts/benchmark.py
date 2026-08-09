"""Measure approximate model load time and per-query latency on this machine.

Writes results to benchmarks.md at the repo root and prints a summary. Can be
run with HF_HUB_OFFLINE=1 after the first model load to prove the pipeline is
fully offline-capable.
"""

from __future__ import annotations

import json
import time

from support_agent import config
from support_agent.models import LocalModels


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    write_benchmarks_md(result)
    print("-> benchmarks.md written")


def run_benchmark() -> dict:
    loader = LocalModels(use_reranker=True)
    bundle = loader.load()

    from support_agent.graph import SupportAgentGraph

    graph = SupportAgentGraph(bundle, use_reranker=True)

    samples = json.loads(config.SAMPLE_QUESTIONS_FILE.read_text(encoding="utf-8"))
    latencies = {}
    for s in samples:
        t0 = time.time()
        _ = graph.run(s["question"])
        latencies[s["id"]] = round(time.time() - t0, 2)

    return {
        "device": bundle.device,
        "models": {
            "embedding": config.EMBEDDING_MODEL,
            "reranker": config.RERANKER_MODEL,
            "llm": config.LLM_MODEL,
        },
        "load_seconds": bundle.load_seconds,
        "per_query_seconds": latencies,
        "mean_query_seconds": round(sum(latencies.values()) / len(latencies), 2),
        "llm_params": count_params(bundle),
    }


def count_params(bundle) -> int | None:
    try:
        return sum(p.numel() for p in bundle.llm_pipeline.parameters())
    except Exception:
        return None


def write_benchmarks_md(result: dict) -> None:
    lines = [
        "# Benchmarks",
        "",
        "Captured on this machine during development. All timings are real "
        "measurements from local runs (see `scripts/benchmark.py`).",
        "",
        f"- **Device**: `{result['device']}`",
        f"- **Embedding model**: `{result['models']['embedding']}`",
        f"- **Reranker**: `{result['models']['reranker']}`",
        f"- **LLM**: `{result['models']['llm']}`",
        f"- **LLM params**: `{result['llm_params']:,}`",
        "",
        "## Model load time (seconds)",
        "",
        "| model | seconds |",
        "|-------|---------|",
    ]
    for k, v in result["load_seconds"].items():
        lines.append(f"| {k} | {v:.2f} |")
    lines += ["", "## Per-query latency (seconds, warm, end-to-end)", ""]
    lines.append("| sample | seconds |")
    lines.append("|---|---|")
    for qid, sec in result["per_query_seconds"].items():
        lines.append(f"| {qid} | {sec} |")
    lines.append(f"| **mean** | **{result['mean_query_seconds']}** |")
    lines += [
        "",
        "_Method: models loaded once via `LocalModels.load()`, then the five "
        "sample questions answered end-to-end through the compiled LangGraph. "
        "Latency includes causal-LM generation on the detected device. To "
        "re-run offline: `set HF_HUB_OFFLINE=1` before launching._",
        "",
    ]
    (config.ROOT_DIR / "benchmarks.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
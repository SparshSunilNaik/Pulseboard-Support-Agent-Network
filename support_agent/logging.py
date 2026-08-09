"""Structured logging for every node run.

Two outputs per run:
  1. A human-readable line to stdout for each node that executed plus the
     conditional branch that was taken.
  2. A machine-readable JSONL run file under ``logs/run_<timestamp>.jsonl``
     containing one record per node event, including timings.

Pure infrastructure: no dependency on any model.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class RunLogger:
    """Collects one record per node execution and flushes it to disk."""

    def __init__(self, log_dir: Path, run_id: str, verbose: bool = False) -> None:
        self.run_id = run_id
        self.verbose = verbose
        log_dir.mkdir(parents=True, exist_ok=True)
        self.path = log_dir / f"run_{run_id}.jsonl"
        self._records: list[dict] = []

    def log(self, node: str, branch: str, extra: dict | None = None) -> None:
        entry = {
            "timestamp": _now(),
            "run_id": self.run_id,
            "node": node,
            "branch": branch,
            **(extra or {}),
        }
        self._records.append(entry)
        if self.verbose:
            print(f"  [node] {node}\t\tbranch={branch}")
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def finalize(self, final_output: dict) -> None:
        entry = {
            "timestamp": _now(),
            "run_id": self.run_id,
            "node": "run.end",
            "branch": "final",
            "final_output": final_output,
        }
        self._records.append(entry)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def make_run_id() -> str:
    return time.strftime("%Y%m%dT%H%M%S")
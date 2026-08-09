"""High-level runtime assembly: models + graph + per-question execution.

Kept separate from the node code so the CLI, scripts, and tests share a
single code path.
"""

from __future__ import annotations

import json

from support_agent import config
from support_agent.graph import SupportAgentGraph
from support_agent.models import LocalModelBundle, LocalModels


def load_bundle(use_reranker: bool = True) -> LocalModelBundle:
    loader = LocalModels(use_reranker=use_reranker)
    return loader.load()


class SupportAgentRuntime:
    """High-level facade: owns models + graph and answers one question."""

    def __init__(self, use_reranker: bool = True) -> None:
        self.bundle = load_bundle(use_reranker=use_reranker)
        self.graph = SupportAgentGraph(self.bundle, use_reranker=use_reranker)

    def answer(self, query: str, verbose: bool = False) -> dict:
        return self.graph.run(query, verbose=verbose)

    def answer_many(self, questions: list[str], verbose: bool = False) -> list[dict]:
        return [self.graph.run(q, verbose=verbose) for q in questions]


def load_sample_questions() -> list[dict]:
    return json.loads(config.SAMPLE_QUESTIONS_FILE.read_text(encoding="utf-8"))
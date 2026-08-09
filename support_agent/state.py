"""Typed graph state for the LangGraph orchestration.

The state is a ``TypedDict`` describing every field nodes may read or write.
Each node receives (and may return) a partial state update that LangGraph
merges into the shared, immutable-per-step state object. Every field required
by the brief is present: query, classification, retrieved_evidence,
draft_answer, verification_result, revision_count, final_output and
node_trace.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict
from operator import add


def merge_trace(left: list, right: list) -> list:
    """Reducer for node_trace: append (never overwrite) trace entries."""
    if left is None:
        left = []
    if right is None:
        right = []
    return list(left) + list(right)


class AgentState(TypedDict, total=False):
    # --- input ---
    query: str
    # --- triage ---
    classification: str              # one of the CLASSIFICATION_LABELS
    classification_reason: str
    triage_confidence: float
    # --- retrieval ---
    retrieved_evidence: list          # list[dict] passages {document, passage, score, doc_type}
    # --- generation ---
    draft_answer: str
    revision_count: int              # how many times generation has re-run
    # --- verification ---
    verification_result: dict        # {passed: bool, checks: {...}, reason: str}
    # --- output ---
    final_output: dict               # structured JSON adhering to the output schema
    requires_human: bool
    reason: str
    # --- tracing ---
    node_trace: Annotated[list, add]
    step_index: int
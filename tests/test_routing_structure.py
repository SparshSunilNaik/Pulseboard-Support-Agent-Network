"""Automated tests for graph routing & structure WITHOUT any model output.

These assert which nodes exist, which conditional edges were taken, and the
loop-guard behavior — using the real node code but a scripted model bundle.
No exact LLM wording is ever asserted; assertions are on node_trace contents
and classification labels only.

Fast, no HF downloads -> doubles as the CI "graph structure" gate.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from support_agent import config
from support_agent import generation as generation_mod
from support_agent.graph import SupportAgentGraph


class StubEmbedder:
    """Deterministic fake embedding model (hash-based) — no torch needed."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def encode(self, texts, normalize_embeddings=True, batch_size=32):
        if isinstance(texts, str):
            texts = [texts]
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            h = hashlib.blake2b(t.encode("utf-8"), digest_size=self.dim).digest()
            arr = np.frombuffer(h, dtype=np.uint8).astype(np.float32)
            out[i, : min(self.dim, len(arr))] = arr[: self.dim]
        if normalize_embeddings:
            norms = np.linalg.norm(out, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            out = out / norms
        return out


class StubBundle:
    device = "cpu"

    class _Token:
        eos_token_id = 0

    embed_model = StubEmbedder()
    llm_tokenizer = _Token()
    llm_pipeline = None


def _good_generate(query, evidence, bundle):
    doc = evidence[0]["document"] if evidence else "none"
    return f"A grounded answer about the user's question. [Source: {doc}]", 0.001


def _bad_generate(query, evidence, bundle):
    return "Ungrounded answer without any source markers at all.", 0.001


def _labels(out) -> list[str]:
    return [t.split(":")[0] for t in out.get("node_trace", [])]


def _branches(out) -> list[str]:
    return [t.split(":", 1)[1] for t in out.get("node_trace", [])]


def _make_graph(monkeypatch, generator):
    monkeypatch.setattr(generation_mod, "generate_answer", generator)
    return SupportAgentGraph(StubBundle(), use_reranker=False)


def test_graph_nodes_exist(monkeypatch):
    g = _make_graph(monkeypatch, _good_generate)
    nodes = set(g.graph.get_graph().nodes)
    assert {
        "triage",
        "retrieval",
        "generate",
        "verify",
        "safe_response",
        "finalize",
    }.issubset(nodes)


def test_answerable_routing(monkeypatch):
    g = _make_graph(monkeypatch, _good_generate)
    out = g.run("Can a read-only user create API credentials?")
    assert out["classification"] == "answerable"
    assert _labels(out) == ["triage", "retrieval", "generate", "verify", "finalize"]
    assert _branches(out)[0] == "answerable"


def test_out_of_scope_routing(monkeypatch):
    g = _make_graph(monkeypatch, _good_generate)
    out = g.run("Write a refund for my subscription.")
    assert out["classification"] == "out_of_scope"
    assert _labels(out) == ["triage", "safe_response"]
    assert out["requires_human"] is True


def test_requires_clarification_routing(monkeypatch):
    g = _make_graph(monkeypatch, _good_generate)
    out = g.run("Which plan am I on?")
    assert out["classification"] == "requires_clarification"
    assert _labels(out) == ["triage", "safe_response"]
    assert out["requires_human"] is True


def test_requires_escalation_routing(monkeypatch):
    g = _make_graph(monkeypatch, _good_generate)
    out = g.run("Please escalate this to a human support agent.")
    assert out["classification"] == "requires_escalation"
    assert _labels(out) == ["triage", "safe_response"]
    assert out["requires_human"] is True


def test_loop_guard_never_infinite(monkeypatch):
    """A generation that ALWAYS fails verification must terminate via
    safe_response after at most MAX_REVISIONS retries (hard loop guard)."""
    g = _make_graph(monkeypatch, _bad_generate)
    out = g.run("My export failed. What should I check?")
    labels = _labels(out)
    assert labels[0] == "triage"
    assert labels[-1] == "safe_response"
    assert labels.count("generate") == config.MAX_REVISIONS + 1
    assert out["requires_human"] is True


def test_retry_path_taken_once(monkeypatch):
    """First generation fails verification, second passes -> exactly one retry."""
    calls = {"n": 0}

    def flaky(query, evidence, bundle):
        calls["n"] += 1
        if calls["n"] == 1:
            return _bad_generate(query, evidence, bundle)
        return _good_generate(query, evidence, bundle)

    g = _make_graph(monkeypatch, flaky)
    out = g.run("My export failed. What should I check?")
    labels = _labels(out)
    assert labels == ["triage", "retrieval", "generate", "verify", "generate", "verify", "finalize"]
    assert calls["n"] == 2
    assert out["requires_human"] is False


def test_evidence_present_on_answerable(monkeypatch):
    g = _make_graph(monkeypatch, _good_generate)
    out = g.run("My scheduled exports stopped after a timezone change.")
    assert out["sources"]  # non-empty
    assert all("document" in s and "passage" in s for s in out["sources"])
"""End-to-end integration tests for the five required scenarios.

These run the real pipeline (local embeddings + local causal LM) and assert on
node_trace contents, classification labels and structure — NOT on the exact
wording of the LLM's prose (per the assignment's requirement that tests not
depend on model-generated text).

Scenario mapping:
  1. test_directly_answerable          -> directly answerable question
  2. test_two_kb_documents             -> requires info from two KB docs
  3. test_ambiguous_needs_clarification -> ambiguous question
  4. test_out_of_scope                 -> out-of-scope refund request
  5. test_verification_retry_and_safe  -> engineered verification failure
                                          triggers retry / safe-failure path
"""

from __future__ import annotations

import pytest

from support_agent.runtime import SupportAgentRuntime


@pytest.fixture(scope="module")
def runtime():
    rt = SupportAgentRuntime(use_reranker=True)
    yield rt
    del rt


def _node_labels(output: dict) -> list[str]:
    return [t.split(":")[0] for t in output.get("node_trace", [])]


def test_directly_answerable_question(runtime):
    out = runtime.answer("Can a read-only user create API credentials?")
    assert out["classification"] == "answerable"
    assert out["answer"]
    assert out["requires_human"] is False
    docs = {s["document"] for s in out["sources"]}
    assert "user-roles-and-permissions.md" in docs
    trace = _node_labels(out)
    assert trace == ["triage", "retrieval", "generate", "verify", "finalize"]


def test_two_kb_documents(runtime):
    out = runtime.answer(
        "My scheduled exports stopped after I changed my workspace timezone. What should I check?"
    )
    assert out["classification"] == "answerable"
    docs = {s["document"] for s in out["sources"]}
    assert "scheduled-exports.md" in docs and "workspace-settings.md" in docs, docs
    assert out["requires_human"] is False


def test_ambiguous_needs_clarification(runtime):
    out = runtime.answer("Is my plan eligible for scheduled exports? Which tier covers it?")
    assert out["classification"] == "requires_clarification"
    trace = _node_labels(out)
    assert trace == ["triage", "safe_response"]
    assert out["requires_human"] is True


def test_out_of_scope(runtime):
    out = runtime.answer("Write a refund for my subscription.")
    assert out["classification"] == "out_of_scope"
    assert out["requires_human"] is True
    trace = _node_labels(out)
    assert trace == ["triage", "safe_response"]


def test_verification_retry_and_safe(runtime, monkeypatch):
    """Engineer a verification failure: first generation returns an
    unverifiable stub. The graph must regenerate once (retry path), and the
    final node_trace must show the second attempt. We then force a *second*
    failure to assert the safe-failure branch produces requires_human=True.

    Uses monkeypatch on the generation function so the test is deterministic
    and independent of what the local LM would actually say.
    """
    import support_agent.generation as generation_mod

    state = {"calls": 0}

    def flaky_generate(query, evidence, bundle):
        state["calls"] += 1
        if state["calls"] == 1:
            return "I do not know anything. Ungrounded with no sources.", 0.01
        if state["calls"] == 2:
            # valid grounding, sources from evidence
            doc = evidence[0]["document"]
            return f"Check the export log and the workspace timezone. [Source: {doc}]", 0.01
        return "still failing", 0.01

    monkeypatch.setattr(generation_mod, "generate_answer", flaky_generate)

    # First attempt fails verification -> graph regenerates once and passes.
    out = runtime.answer("Why did my exports stop?")
    trace = _node_labels(out)
    assert trace == ["triage", "retrieval", "generate", "verify", "generate", "verify", "finalize"]
    assert out["requires_human"] is False

    # Now force every generation to fail -> safe failure path with human.
    monkeypatch.setattr(generation_mod, "generate_answer", lambda q, e, b: ("bad stub again", 0.01))
    out2 = runtime.answer("Why did my exports stop?")
    trace2 = _node_labels(out2)
    assert trace2[-1] == "safe_response"
    assert out2["requires_human"] is True
"""Safe-response node for non-answerable classifications.

Pure deterministic module: produces safe, human-required fallback responses
for the three non-answerable classes and for the post-revision failure path.
No model is invoked here (by design — the graph routes these classes away
from the retrieval/generation pipeline entirely). All responses are explicit
front-coded text plus a ``requires_human=True`` flag and no fabricated facts.
"""

from __future__ import annotations

from support_agent import config


def response_for_class(classification: str, query: str, reason: str) -> dict:
    """Return the final_output dict for a non-answerable classification."""
    if classification == "out_of_scope":
        answer = (
            "I can't take that action: '%s' is outside what Pulseboard Support "
            "can do. Refunds and account changes are handled by our billing "
            "team and are never issued directly by automated support. Please "
            "open a billing ticket via Settings -> Billing, or email "
            "billing@pulseboard.example. A human will follow up."
            % query
        )
        requires_human = True
        sources: list[dict] = [
            {"document": "billing-subscriptions.md", "passage": "Refunds and invoices"}
        ]
        confidence = 0.95
    elif classification == "requires_escalation":
        answer = (
            "I understand; let's get this to a human. Before escalating, please "
            "collect exactly the diagnostic packet: (1) the workspace slug and "
            "your email, (2) the original suggested solution and the outcome, "
            "(3) the run ID or correlation ID from Help -> Diagnostic log, "
            "(4) the exact error text / reason code, (5) the workspace "
            "timezone and plan. An Agent will need all five items or the "
            "escalation is returned."
        )
        sources: list[dict] = [
            {"document": "escalation-procedure.md", "passage": "Information to collect before escalating"}
        ]
        confidence = 0.92
        requires_human = True
    elif classification == "requires_clarification":
        answer = (
            "To help you accurately, I need a bit more context. Which "
            "Pulseboard workspace are you referring to, and which plan is it "
            "on (Starter, Workspace, Enterprise)? Knowing the plan and feature "
            "you mean lets me give a precise answer — describing the plan "
            "often decides whether something like exports or data retention "
            "applies."
        )
        sources: list[dict] = []
        confidence = 0.6
        requires_human = True
    else:  # safety fallback (should not happen)
        answer = "Your case requires a human review. Please include your workspace and question and a support agent will pick it up."
        sources = []
        confidence = 0.5
        requires_human = True

    return {
        "classification": classification,
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "requires_human": requires_human,
        "reason": reason,
        "content_warning": "This is a safe-response path; no grounding retrieval ran.",
    }


def failure_after_revision(classification: str, reason: str) -> dict:
    """Safe, explicit failure produced once verification fails after retry."""
    return {
        "classification": classification,
        "answer": (
            "I could not produce a response that passes automatic verification "
            "after a retry, so I am deliberately not answering rather than "
            "risking misinformation. This case has been flagged for a human "
            "support agent with the full diagnostic context."
        ),
        "sources": [],
        "confidence": 0.0,
        "requires_human": True,
        "reason": reason,
    }
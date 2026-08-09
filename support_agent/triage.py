"""Triage node: classify the request into exactly one of four classes.

Hybrid, fully local classifier (justification documented in README):

1. **Keyword / rule signals** (deterministic, zero-latency) catch the
   near-deterministic cases: escalation language, refund/billing demands,
   plan-scoped questions, out-of-scope chit-chat.
2. **Embedding-similarity** against prototype sentences per class, computed
   with the local sentence-transformers model. The label with the highest
   mean cosine similarity wins when no rule fired. A confidence floor guards
   ambiguous / under-specified intents and routes them to
   ``requires_clarification`` instead of guessing.

No remote model call is involved: only the local embedding model + numpy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from support_agent import config

# (regex, label) pairs evaluated in order. First match wins -> deterministic.
RULE_BASED_LABELS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b(refund|chargeback|money\s?back|write a refund|invoice me)\b", re.I),
        "out_of_scope",
    ),
    (
        re.compile(r"\b(escalat|speak to (a |the )?human|contact .* manager|ticket to support)\b", re.I),
        "requires_escalation",
    ),
    (
        re.compile(r"\b(which plan|which version|what plan|what version|is that on my plan)\b", re.I),
        "requires_clarification",
    ),
]

# Prototype (embedding) examples for the similarity-based residual. These are
# generic phrasings of intent across the KB and the resolved cases.
PROTOTYPES: dict[str, list[str]] = {
    "answerable": [
        "how do I create an api credential",
        "my export failed with an error message",
        "can read-only users create api credentials",
        "changing the workspace timezone broke scheduled exports",
        "where do I check when my export next runs",
        "is two factor authentication mandatory for admins",
        "how long is my data retained",
        "why did my daily digest email stop arriving",
        "rotating expired api keys",
        "what happens when my card payment fails",
        "legal hold and region pinning for enterprise",
    ],
    "requires_clarification": [
        "does my plan include this feature",
        "which subscription tier am I on",
        "can you tell me what plan version I have",
        "which workspace does this change apply to",
    ],
    "requires_escalation": [
        "please escalate this to the support team",
        "what information do I collect before escalating",
        "the suggested solution did not work",
        "get a human support agent to look at this ticket",
    ],
    "out_of_scope": [
        "write a refund for my subscription",
        "give me a discount coupon for my account",
        "help me build a landing page in wordpress",
        "write me a resignation letter",
    ],
}


@dataclass
class TriageResult:
    label: str
    confidence: float
    method: str
    reason: str


def _rule_match(query: str) -> str | None:
    for rx, label in RULE_BASED_LABELS:
        if rx.search(query):
            return label
    return None


def _embed_one(model, text: str) -> list[float]:
    return model.encode([text], normalize_embeddings=True)[0].tolist()


def _cosine_sim(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def classify(query: str, model) -> TriageResult:
    """Classify ``query`` into one of config.CLASSIFICATION_LABELS.

    ``model`` is the local sentence-transformers embed model (anything with
    ``encode([text]) -> numpy (1, d)``).
    """
    rule_label = _rule_match(query)

    # 1) Similarity scores per class using prototypes.
    q_emb = _embed_one(model, query)
    scores: dict[str, float] = {}
    for cls, prototypes in PROTOTYPES.items():
        best = 0.0
        for proto in prototypes:
            sim = _cosine_sim(q_emb, _embed_one(model, proto))
            best = max(best, sim)
        scores[cls] = best

    wins = max(scores, key=lambda k: scores[k])
    best_sim = scores[wins]

    # 2) Rule signal, if any, wins for the cases classifiers get wrong.
    if rule_label is not None:
        # Hard overrides for clearly out-of-scope/escalation wording.
        if rule_label == "out_of_scope" or rule_label == "requires_escalation":
            return TriageResult(
                label=rule_label,
                confidence=scores.get(rule_label, best_sim),
                method="rules",
                reason=f"matched rule {rule_label!r} (deterministic)",
            )
        # Clarification requests win when the "which plan/version" wording is
        # present even if similarity leans answerable.
        return TriageResult(
            label=rule_label,
            confidence=scores.get("requires_clarification", best_sim),
            method="rules",
            reason=f"matched rule {rule_label!r} (requires plan/version disambiguation)",
        )

    # 3) Confidence floor: if nothing strongly matches one of the tags, ask
    #    for clarification rather than guessing next behavior.
    if best_sim < config.CLARIFICATION_SIM_FLOOR:
        return TriageResult(
            label="requires_clarification",
            method="embedding+floor",
            confidence=best_sim,
            reason=(
                f"best prototype similarity {best_sim:.3f} below floor "
                f"{config.CLARIFICATION_SIM_FLOOR}"
            ),
        )

    # 4) Plain winner-takes-all among the four class prototypes.
    return TriageResult(
        label=wins,
        method="embedding",
        confidence=best_sim,
        reason=f"winner={wins} sim={best_sim:.3f} among prototypes",
    )
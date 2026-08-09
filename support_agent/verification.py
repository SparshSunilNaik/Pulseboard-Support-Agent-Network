"""Verification node (deterministic, no model-driven reasoning).

Checks the generated answer for:

  (a) support by retrieved evidence,
  (b) presence of source references,
  (c) conformance to the required output schema,
  (d) no invented / unsupported instructions.

Source references are bound deterministically by ``generation.bind_sources``
and appear as ``[Source: doc1.md, doc2.md]``. The parser here accepts both
that format and inline ``[Source: filename]`` markers.

If the checks fail, the graph routes back to the generation node for exactly
one more attempt (see config.MAX_REVISIONS). If the second attempt also
fails, a safe, explicit failure response (requires_human=True) is returned
instead of looping forever. A hard loop guard at the graph level finishes the
safety net (see graph.py).
"""

from __future__ import annotations

import re

from support_agent import config

_SOURCE_MARKER = re.compile(r"\[[Ss]ource:\s*([^\]]+)\]")
_MIN_ANSWER_LEN = 24
_UNSUPPORTED_TOKENS = ("refund", "invoice you", "coupon", "password reset link")


def _extract_cited_sources(answer: str) -> set[str]:
    """Return normalized doc names cited anywhere in the answer."""
    cited: set[str] = set()
    for m in _SOURCE_MARKER.findall(answer):
        # markers may hold a comma- or semicolon-separated list.
        # NOTE: we must NOT split on "and": filenames like
        # user-roles-and-permissions.md contain it as a substring.
        for part in re.split(r"[,;]", m):
            part = part.strip()
            if not part:
                continue
            part = re.sub(r"\.+$", "", part)
            if "/" in part:  # passage qualifier like "doc.md / section"
                part = part.split("/")[0].strip()
            if part and part.lower() != "none":
                cited.add(part.upper())
    return cited


def check_answer(answer: str, evidence: list[dict]) -> dict:
    """Return a dict of pass/fail details for the generated answer."""
    checks: dict[str, bool] = {}

    answer = (answer or "").strip()
    ev_text = " ".join(ev["text"] for ev in evidence).lower()

    # (b) presence of source references
    cited = _extract_cited_sources(answer)
    checks["has_source_markers"] = len(cited) > 0

    # (a) every cited source must exist among the retrieved evidence
    provided = {ev["document"].upper() for ev in evidence}
    unsupported = cited - provided
    checks["citations_in_evidence"] = len(unsupported) == 0
    checks["unsupported_source_list"] = sorted(unsupported)

    # (a2) evidence grounding: word-overlap between answer and evidence.
    #      Two sub-conditions (min-shared content words OR fraction) keep the
    #      check robust to the 0.5B model adding verbosity while still
    #      rejecting answers that share almost nothing with the evidence.
    ev_words = set(_significant_words(ev_text))
    ans_words = _significant_words(answer)
    shared = len(ev_words & set(ans_words))
    overlap = shared / max(len(ans_words), 1)
    checks["lexical_grounding_minshared"] = shared >= 8
    checks["lexical_grounding_frac"] = overlap >= 0.15
    checks["lexical_grounding"] = shared >= 8 or overlap >= 0.15

    # (c) schema conformance: a non-trivial string answer
    checks["schema_conforms"] = len(answer) >= _MIN_ANSWER_LEN

    # (d) no invented / unsupported instructions
    lower = answer.lower()
    invented = [t for t in _UNSUPPORTED_TOKENS if t in lower and t not in ev_text]
    checks["no_invented_instructions"] = len(invented) == 0
    checks["invented_tokens"] = invented

    # Aggregate. Sub-metrics (names ending in _minsubset/_frac) are reported
    # but not gated independently - only the parent check decides.
    gated = {
        k for k in checks
        if not k.endswith("_list")
        and not k.endswith("_tokens")
    }
    gated -= {"lexical_grounding_minshared", "lexical_grounding_frac"}
    fail_keys = [k for k in gated if checks[k] is False]
    passed = len(fail_keys) == 0

    return {
        "passed": passed,
        "checks": checks,
        "reason": ("all checks passed" if passed else "failed: " + ", ".join(fail_keys)),
        "cited_sources": sorted(cited),
    }


def confidence_from_evidence(evidence: list[dict]) -> float:
    """Score in [0, 1] from retrieval similarity using a softmax over top hits."""
    if not evidence:
        return 0.0
    sims = [max(0.0, float(e.get("score", 0.0))) for e in evidence[:3]]
    weights = [0.5, 0.3, 0.2][: len(sims)]
    total = sum(w * _clamp(_scale(sim), 0.0, 1.0) for sim, w in zip(sims, weights))
    return float(round(total, 2))


def _scale(s) -> float:
    """Map a cosine similarity (~0.2..0.9) onto [0.25, 0.9]."""
    return 0.25 + 0.65 * max(0.0, min(1.0, (float(s) - 0.3) / 0.5))


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "to", "of", "in", "on", "for", "with",
    "that", "this", "is", "are", "was", "were", "be", "been", "have", "has",
    "had", "do", "does", "did", "will", "would", "can", "could", "should",
    "not", "no", "yes", "i", "you", "your", "my", "it", "we", "they", "at",
    "by", "from", "as", "if", "so", "about", "than", "then", "them", "their",
    "there", "how", "what", "when", "why", "which", "who", "whom", "into",
    "just", "may", "might", "must", "shall", "very", "s", "t", "up", "out",
    "its", "are", "each", "between", "through", "during", "before", "after",
    "such", "because", "also", "our", "us", "any", "all", "most", "other",
    "over", "under", "again", "further", "once", "here", "too", "only",
    "own", "same", "some", "first", "please", "seem", "seems", "ensure",
}


def _significant_words(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]
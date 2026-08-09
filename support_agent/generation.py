"""Response generation node: model-driven answer generation.

This is the only place a causal LM is invoked. The prompt is built strictly
from the retrieved evidence (KB passages + resolved cases) and the user query.
The model is instructed to ground every claim in the cited passages.

Because a 0.5B instruction-tuned model is not reliable at emitting the exact
``[Source: file.md]`` syntax on demand, we post-process its output: the answer
is kept as generated, and ``bind_sources`` deterministically appends the
filenames of every retrieved passage that actually overlaps with the answer's
content. This keeps citation attachment deterministic (grounded) instead of
leaving it to the model's mood.

Model: ``Qwen/Qwen2.5-0.5B-Instruct`` (pinned revision in config), chosen
because it is instruction-tuned, small enough to run on CPU in a few seconds,
and adequate for this task where *correct integration* matters more than
fluency (see README trade-offs).
"""

from __future__ import annotations

import re
import time

from support_agent import config


def build_prompt(query: str, evidence: list[dict]) -> str:
    """Compose the grounding prompt from retrieved passages."""
    if not evidence:
        return (
            "You are Pulseboard Support. The knowledge base did not return any "
            "passages relevant to the question. Do not guess. Reply with a "
            "short customer-facing message saying the information is not "
            "available and that a human agent should follow up."
        )

    ctx_lines = []
    for i, ev in enumerate(evidence, 1):
        doc = ev["document"]
        sec = ev["passage"]
        text = ev["text"]
        ctx_lines.append(f"[{i}] ({doc} / {sec})\n{text}")

    system = (
        "You are Pulseboard Support, an expert customer-facing assistant for "
        "the Pulseboard workspace analytics SaaS. Write a short, friendly "
        "answer (2-6 sentences) to the user's question, using the provided "
        "context passages as your ONLY source of facts. Rules:\n"
        "1. Start directly with the answer. Do NOT repeat the context, do NOT "
        "add prefaces, labels, headers, notes, or a 'conclusion' section, and "
        "do not add chatter after the final sentence.\n"
        "2. Never invent instructions, credentials, pricing, or features.\n"
        "3. If the context does not contain the answer, say so in one sentence "
        "and suggest a human follow-up.\n"
        "4. Answer the reader faithfully; stop when done.\n"
        f"\n\nContext:\n{chr(10).join(ctx_lines)}\n\nUser question: {query}\n\nAnswer:"
    )
    return system


def generate_answer(query: str, evidence: list[dict], bundle, seed: int | None = None) -> tuple[str, float]:
    """Run local causal LM; return (final_grounded_answer, generation_seconds).

    ``seed`` is optional and only used by tests/benchmarks; real traffic keeps
    stochastic sampling (temperature/top-p).
    """
    prompt = build_prompt(query, evidence)
    tokenizer = bundle.llm_tokenizer
    model = bundle.llm_pipeline

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=config.GENERATION_MAX_INPUT_TOKENS)
    inputs = {k: v.to(bundle.device) for k, v in inputs.items()}

    gen_kwargs = dict(
        max_new_tokens=config.MAX_OUTPUT_TOKENS,
        do_sample=True,
        top_p=0.9,
        temperature=0.3,
        pad_token_id=tokenizer.eos_token_id,
    )
    if seed is not None:
        import torch

        torch.manual_seed(seed)

    t0 = time.time()
    with _disable_grad():
        outputs = model.generate(**inputs, **gen_kwargs)
    elapsed = time.time() - t0

    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    if not text:
        text = "[No answer generated]"
    text = _cleanup(text)
    text = bind_sources(text, evidence)
    return text, elapsed


def _cleanup(text: str) -> str:
    """Remove common 0.5B-model meta-chatter wrappers."""
    text = text.strip()
    text = re.sub(r"^(Answer|Response|Output|Here is|Sure|Great)[:.\s]*", "", text, flags=re.I).strip()
    text = re.sub(r"\n?\[?[Ss]ource:\s*none\]?\s*$", "", text).strip()
    # cut any trailing meta-sections the small model likes to add
    cut = re.split(
        r"\b(Note|Follow\-?up|Explanation|Conclusion|Analysis|Suggested|Warning|Reminder|Do not provide|Is there a way):?\s",
        text,
        flags=re.I,
    )
    text = cut[0].strip()
    # collapse stray blank lines
    text = re.sub(r"\n{2,}", "\n", text).strip()
    return text


_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "to", "of", "in", "on", "for", "with",
    "that", "this", "is", "are", "was", "were", "be", "been", "have", "has",
    "had", "do", "does", "did", "will", "would", "can", "could", "should",
    "not", "no", "yes", "i", "you", "your", "my", "it", "we", "they", "at",
    "by", "from", "as", "if", "so", "about", "than", "then", "them", "their",
    "there", "how", "what", "when", "why", "which", "who", "whom",
}


def bind_sources(answer: str, evidence: list[dict]) -> str:
    """Deterministically append source references to the answer.

    A document is bound when a meaningful fraction of its distinctive words
    also appear in the answer (paraphrase-tolerant overlap). This turns the
    fragile "ask the model to cite" step into a deterministic post-processing
    rule grounded in retrieval. It never appends a document the model didn't
    actually echo; if nothing overlaps, no citations are added and the
    verification node will reject the answer as unsupported.
    """
    ans_words = _significant(answer)
    if not ans_words:
        return answer
    ans_set = set(ans_words)

    hits = []
    for ev in evidence:
        ev_words = set(_significant(ev["text"]))
        if not ev_words:
            continue
        overlap = len(ans_set & ev_words) / len(ans_set)
        # any overlap at all => consider bound; multiple docs can be bound
        if len(ans_set & ev_words) >= 3 or overlap >= 0.15:
            hits.append((ev["document"], round(overlap, 3)))

    if not hits:
        return answer  # ungrounded; leave for verification to reject

    # dedupe keep order by strongest overlap
    seen = set()
    ordered: list[tuple[str, float]] = []
    for doc, ov in sorted(hits, key=lambda t: -t[1]):
        if doc not in seen:
            seen.add(doc)
            ordered.append((doc, ov))

    lines = answer + "\n\n" + "; ".join(doc for doc, _ in ordered) + "."
    lines += "\n[Source: " + ", ".join(doc for doc, _ in ordered) + "]"
    return lines


def _significant(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def _disable_grad():
    import torch

    return torch.no_grad()
"""Retrieval node: deterministic retrieval math over local embeddings.

The knowledge base markdown docs are chunked into passages (per section) and
combined with the resolved-cases JSON entries. Each passage is embedded once
with the local sentence-transformers model and cached to ``data/cache`` so
subsequent runs (including fully-offline runs) skip re-embedding.

At query time we embed the user question and return the top-k passages by
cosine similarity, optionally re-ranked by the local cross-encoder.

This module contains NO model-driven reasoning; the only model access is the
embedding encoder (a deterministic map) which keeps "retrieval math" and
"response generation" cleanly separated.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

import numpy as np

from support_agent import config


@dataclass
class Passage:
    document: str   # filename, e.g. "workspace-settings.md" or "resolved_cases.json"
    passage: str    # section heading or case id
    text: str
    source_type: str  # "kb" | "case"


class RetrievalIndex:
    """In-memory dense index over KB sections + resolved cases."""

    def __init__(self, embed_model, use_reranker: bool = True) -> None:
        self.embed_model = embed_model
        self.use_reranker = use_reranker
        self.passages: list[Passage] = []
        self._embeddings: np.ndarray | None = None
        self.reranker = None

    # -- construction -----------------------------------------------------
    def build(self, force_recompute: bool = False) -> None:
        self.passages = self._collect_passages()
        if not force_recompute and self._load_cache():
            pass  # embeddings restored from cache
        else:
            self._embeddings = self._embed_passages(self.passages)
            self._save_cache()
        if self.use_reranker:
            from sentence_transformers import CrossEncoder

            self.reranker = CrossEncoder(
                config.RERANKER_MODEL, revision=config.RERANKER_REVISION
            )

    def _collect_passages(self) -> list[Passage]:
        out: list[Passage] = []
        for md in sorted(config.KB_DIR.glob(config.KB_GLOB)):
            raw = md.read_text(encoding="utf-8")
            for section in _split_markdown_sections(raw):
                out.append(
                    Passage(
                        document=md.name,
                        passage=section[0],
                        text=section[1].strip(),
                        source_type="kb",
                    )
                )
        cases = json.loads(config.RESOLVED_CASES_FILE.read_text(encoding="utf-8"))
        for case in cases:
            q = case.get("question", "")
            res = case.get("resolution", "")
            tags = ", ".join(case.get("tags", []))
            text = f"Question: {q}\nResolution: {res}\nTags: {tags}"
            out.append(
                Passage(
                    document="resolved_cases.json",
                    passage=case.get("id", ""),
                    text=text,
                    source_type="case",
                )
            )
        return out

    def _embed_passages(self, passages: list[Passage]) -> np.ndarray:
        texts = [p.text for p in passages]
        emb = self.embed_model.encode(texts, normalize_embeddings=True, batch_size=32)
        return np.asarray(emb, dtype=np.float32)

    def _cache_key(self, n_passages: int) -> str:
        digest = hashlib.sha256()
        for p in sorted(self.passages, key=lambda p: (p.document, p.passage)):
            digest.update(f"{p.document}|{p.passage}|{p.text}".encode("utf-8"))
        return digest.hexdigest()[:16] + f"_{n_passages}"

    def _load_cache(self) -> bool:
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if not config.EMBEDDINGS_CACHE_FILE.exists():
            return False
        try:
            data = np.load(config.EMBEDDINGS_CACHE_FILE, allow_pickle=False)
            if data["ids"].tolist() != self._cache_key(len(self.passages)) or data["embs"].shape[0] != len(self.passages):
                return False
            self._embeddings = data["embs"]
            return True
        except Exception:
            return False

    def _save_cache(self) -> None:
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(
            config.EMBEDDINGS_CACHE_FILE,
            ids=self._cache_key(len(self.passages)),
            embs=self._embeddings,
        )

    # -- query -------------------------------------------------------------
    def search(self, query: str, top_k: int = 6) -> list[dict]:
        q_emb = self.embed_model.encode([query], normalize_embeddings=True)[0]
        sims = self._embeddings @ np.asarray(q_emb, dtype=np.float32)
        idx = np.argsort(-sims)[: max(top_k, len(self.passages))]
        hits = []
        for i in idx:
            hits.append(
                {
                    "document": self.passages[i].document,
                    "passage": self.passages[i].passage,
                    "text": self.passages[i].text,
                    "score": float(sims[i]),
                    "source_type": self.passages[i].source_type,
                }
            )
        return hits[:top_k]

    def search_reranked(self, query: str, top_k: int = 3) -> list[dict]:
        """Retrieve more candidates, then re-rank with the cross-encoder."""
        cands = self.search(query, top_k=top_k * 4)
        pairs = [(query, c["text"]) for c in cands]
        scores = self.reranker.predict(pairs)
        ranked = sorted(zip(cands, scores), key=lambda t: -float(t[1]))
        out = []
        for cand, sc in ranked[:top_k]:
            cand = dict(cand)
            cand["rerank_score"] = float(sc)
            out.append(cand)
        return out

    def retrieve(self, query: str, top_k: int = 6) -> list[dict]:
        if self.reranker is not None:
            return self.search_reranked(query, top_k=top_k)
        return self.search(query, top_k=top_k)


_SECTION_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.M)


def _split_markdown_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) tuples per section."""
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        return [("body", text)]
    sections: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        heading = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append((heading, body))
    return sections
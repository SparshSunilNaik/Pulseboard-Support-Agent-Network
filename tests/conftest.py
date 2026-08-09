"""Shared test fixtures.

The routing/structure tests use a stub embedder and must NOT overwrite the
production embeddings cache (data/cache/) that the real pipeline writes. We
redirect the cache to a per-test tmp dir.
"""

from __future__ import annotations

import pytest

from support_agent import config


@pytest.fixture(autouse=True)
def isolate_cache(tmp_path, monkeypatch):
    """Redirect the embeddings cache so tests never clobber production data."""
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(config, "EMBEDDINGS_CACHE_FILE", tmp_path / "cache" / "corpus_embeddings.npz")
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    yield
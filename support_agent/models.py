"""Local model loading. No hosted/remote LLM APIs anywhere in the pipeline.

Three models, all loaded from the Hugging Face Hub and cached locally in
``~/.cache/huggingface``:

- ``sentence-transformers/all-MiniLM-L6-v2``  → embeddings for retrieval/triage
- ``cross-encoder/ms-marco-MiniLM-L-6-v2``    → optional reranker (small, CPU-friendly)
- ``Qwen/Qwen2.5-0.5B-Instruct``              → causal LM for grounded generation

Device selection (CUDA if available and enabled, else CPU) and dtype
(fp16 on CUDA, fp32 on CPU) are automatic. After first download, inference
works fully offline with ``HF_HUB_OFFLINE=1``; no API keys are read and no
websites are contacted.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from support_agent import config

log = logging.getLogger("support-agent.models")


def pick_device() -> str:
    """Return 'cuda' when a GPU is available and enabled, else 'cpu'."""
    import torch  # deferred so the module can be inspected without torch installed

    if config.ENABLE_GPU and torch.cuda.is_available():
        return "cuda"
    return "cpu"


def auto_dtype(device: str):
    import torch  # deferred import keeps import-time lightweight

    return torch.float16 if device == "cuda" else torch.float32


def _version_tuple(v: str) -> tuple:
    parts = []
    for p in v.split("."):
        digits = ""
        for ch in p:
            if ch.isdigit():
                digits += ch
            else:
                break
        try:
            parts.append(int(digits or 0))
        except ValueError:
            parts.append(0)
    return tuple(parts[:3])


@dataclass
class LocalModelBundle:
    """Container for all loaded local models plus timing bookkeeping."""

    device: str
    embed_model: object = None              # sentence_transformers.SentenceTransformer
    reranker_model: object = None          # sentence_transformers.CrossEncoder
    llm_model: object = None               # transformers.AutoModelForCausalLM
    llm_tokenizer: object = None           # transformers.AutoTokenizer
    load_seconds: dict = field(default_factory=dict)


class LocalModels:
    """Loads and caches the local model bundle (singleton-style holder)."""

    def __init__(self, use_reranker: bool = True) -> None:
        self.use_reranker = use_reranker
        self._bundle: LocalModelBundle | None = None

    def load(self) -> LocalModelBundle:
        """Load everything exactly once; subsequent calls return the cache."""
        if self._bundle is not None:
            return self._bundle

        from sentence_transformers import CrossEncoder, SentenceTransformer
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = pick_device()
        bundle = LocalModelBundle(device=device)

        log.info("Loading local models on device=%s (use_reranker=%s)", device, self.use_reranker)

        t = time.time()
        bundle.embed_model = SentenceTransformer(
            config.EMBEDDING_MODEL, revision=config.EMBEDDING_REVISION, device=device
        )
        bundle.load_seconds["embed"] = time.time() - t

        if self.use_reranker:
            t = time.time()
            bundle.reranker_model = CrossEncoder(
                config.RERANKER_MODEL, revision=config.RERANKER_REVISION
            )
            bundle.load_seconds["reranker"] = time.time() - t

        t = time.time()
        bundle.llm_tokenizer = AutoTokenizer.from_pretrained(
            config.LLM_MODEL, revision=config.LLM_REVISION
        )
        kwargs = {
            "revision": config.LLM_REVISION,
            "torch_dtype": auto_dtype(device),
        }
        # transformers>=5 renamed torch_dtype->dtype; be compatible with both
        try:
            import transformers

            if hasattr(transformers, "__version__") and _version_tuple(transformers.__version__) >= (5, 0):
                kwargs.pop("torch_dtype", None)
                kwargs["dtype"] = auto_dtype(device)
        except Exception:
            pass
        bundle.llm_pipeline = AutoModelForCausalLM.from_pretrained(config.LLM_MODEL, **kwargs)
        bundle.llm_pipeline.to(device)
        bundle.llm_pipeline.eval()
        bundle.load_seconds["llm"] = time.time() - t

        log.info(
            "Model bundle ready. device=%s load_seconds=%s",
            device,
            {k: round(v, 2) for k, v in bundle.load_seconds.items()},
        )
        self._bundle = bundle
        return bundle
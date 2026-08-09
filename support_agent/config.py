"""Configuration and pinned model identities for the support agent network.

All model references are pinned to exact Hugging Face repo revision
(commit) hashes rather than "latest", so inference is fully reproducible and
can run with ``HF_HUB_OFFLINE=1`` after the first download. See MODELS.md.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
KB_DIR = DATA_DIR / "kb"
CACHE_DIR = DATA_DIR / "cache"
LOG_DIR = ROOT_DIR / "logs"
SAMPLE_OUTPUT_DIR = ROOT_DIR / "sample_outputs"

KB_GLOB = "*.md"
RESOLVED_CASES_FILE = DATA_DIR / "resolved_cases.json"
SAMPLE_QUESTIONS_FILE = DATA_DIR / "sample_questions.json"

EMBEDDINGS_CACHE_FILE = CACHE_DIR / "corpus_embeddings.npz"
INDEX_CACHE_FILE = CACHE_DIR / "index_manifest.json"

# ---------------------------------------------------------------------------
# Pinned model identities (repo:revision). Revised after download in MODELS.md.
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANKER_REVISION = "c5ee24cb16019beea0893ab7796b1df96625c6b8"

LLM_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
LLM_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"

# ---------------------------------------------------------------------------
# Pipeline tuning
# ---------------------------------------------------------------------------
RETRIEVAL_TOP_K = 6                 # combined passages retrieved from KB + cases
RERANK_TOP_K = 3                   # kept after optional cross-encoder rerank
MAX_REVISIONS = 1                  # hard loop guard: max regenerate attempts
MAX_OUTPUT_TOKENS = 220
GENERATION_MAX_INPUT_TOKENS = 1200

ENABLE_RERANKER = True
ENABLE_GPU = True                  # auto-detected at runtime; CPU fallback built in

# Keyword / embedding signals that override the class prior in triage.
TRIAGE_TOP_K = 3

CLASSIFICATION_LABELS = (
    "answerable",
    "requires_clarification",
    "requires_escalation",
    "out_of_scope",
)

# Confidence floor for the answerable route; below it triage asks for
# clarification instead of guessing.
CLARIFICATION_SIM_FLOOR = 0.45
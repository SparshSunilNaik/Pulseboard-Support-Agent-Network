# Models used and their pinned revisions
#
# Every model is hosted on the Hugging Face Hub and cached locally in
# `~/.cache/huggingface` after the first download. Revisions are pinned to
# exact commit hashes (NOT "latest") so results are reproducible and the
# pipeline can run fully offline afterwards (`HF_HUB_OFFLINE=1`).
#
# The exact commit hash for each repo is recorded below as captured on this
# machine during setup. To re-verify, use:
#   python - <<'PY'
#   from huggingface_hub import HfApi
#   for repo in ["sentence-transformers/all-MiniLM-L6-v2",
#                "cross-encoder/ms-marco-MiniLM-L-6-v2",
#                "Qwen/Qwen2.5-0.5B-Instruct"]:
#       print(repo, HfApi().model_info(repo).sha)
#   PY

## 1. Embedding model (retrieval + triage features)
- repo: `sentence-transformers/all-MiniLM-L6-v2`
- revision (commit): `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
- framework: sentence-transformers (backend: transformers + torch)
- size: ~90 MB; 6 layers, 384-dim embeddings
- role: deterministic passage & query embedding for cosine retrieval; also
  drives the prototype-similarity triage signal.

## 2. Reranker (optional, small cross-encoder)
- repo: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- revision (commit): `c5ee24cb16019beea0893ab7796b1df96625c6b8`
- framework: sentence-transformers (CrossEncoder)
- size: ~60 MB
- role: re-scores the top-k candidate passages from the bi-encoder so the
  final evidence list is better ranked. Disabled with `--no-reranker`.

## 3. Causal LM for generation
- repo: `Qwen/Qwen2.5-0.5B-Instruct`
- revision (commit): `7ae557604adf67be50417f59c2c2f167def9a775`
- framework: transformers (AutoModelForCausalLM)
- size: ~1.0 GB (fp16 on CUDA; fp32 on CPU)
- role: grounded response generation. Instruction-tuned, small enough for
  CPU in reasonable time; "model quality is less important than correct
  integration" per the brief.

## Verification of the "no network at inference" guarantee
After the models are downloaded once, run inference with:

    set HF_HUB_OFFLINE=1          # PowerShell
    # or
    HF_HUB_OFFLINE=1 python -m support_agent.cli "..." --verbose

The pipeline contacts no hosted API at any point. The only network use that
ever happens is the initial model download. `LocalModels` reads no API keys
and config.py contains no endpoint URLs besides Hugging Face repo ids.
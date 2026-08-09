# Pulseboard Support Agent Network

A **graph-based (LangGraph) AI agent network** that answers support questions
for a fictional B2B SaaS product — **Pulseboard**, a workspace analytics &
scheduled-export platform. Everything runs **fully locally**: no hosted LLM
API (no OpenAI / Anthropic / Gemini / Groq / Cohere) is used anywhere in the
pipeline. Only Hugging Face models running via `transformers` /
`sentence-transformers` are used, pinned to exact revisions, and able to run
offline after first download.

**This is a submission for the assignment brief. It is fabricated ground-up:
an invented product, an invented knowledge base, invented resolved cases, and
invented sample questions (the test questions come verbatim from the brief).**

---

## 1. Project overview

```
support-agent-network/
├── data/
│   ├── kb/                      # 10 fabricated Markdown knowledge-base docs (150-400 words each)
│   ├── resolved_cases.json      # 12 previously resolved support cases
│   ├── cache/                   # precomputed passage embeddings (rebuilt automatically)
│   └── sample_questions.json    # the five brief questions + one invented
├── support_agent/
│   ├── config.py                # paths, pinned model revisions, tuning knobs
│   ├── state.py                 # typed (TypedDict) shared graph state
│   ├── models.py                # local model loading (embed, rerank, causal LM)
│   ├── triage.py                # node: classify into 4 classes (hybrid local classifier)
│   ├── retrieval.py             # node: deterministic cosine retrieval math
│   ├── generation.py            # node: grounded answer generation (local causal LM)
│   ├── verification.py          # node: deterministic evidence/schema checks
│   ├── safe_responses.py        # node: safe fallbacks for non-answerable classes
│   ├── graph.py                 # LangGraph assembly + conditional routing + loop guard
│   ├── logging.py               # structured node trace -> stdout + logs/run_<ts>.jsonl
│   └── cli.py                   # command-line interface
├── scripts/
│   ├── run_all_cases.py         # runs the 5 sample questions -> sample_outputs/
│   ├── benchmark.py             # load + latency numbers -> benchmarks.md
│   └── draw_graph.py            # renders graph_diagram.png
├── tests/
│   ├── conftest.py              # cache/log isolation per run
│   ├── test_routing_structure.py# routing/structure tests (no real models needed)
│   └── test_end_to_end.py      # 5 required scenarios (real local models)
├── sample_outputs/              # genuine outputs of the 5-run scripts
├── graph_diagram.png            # rendered graph sketch (committed)
├── MODELS.md                    # exact model names + revision commit hashes
├── benchmarks.md                # measured load/latency on this machine
├── requirements.txt / pyproject.toml
└── .gitignore
```

## 2. Architecture (per node)

The graph is a typed LangGraph state machine. State is an
`AgentState` TypedDict with `query`, `classification`, `retrieved_evidence`,
`draft_answer`, `verification_result`, `revision_count`, `final_output`,
`requires_human`, `reason`, and a trailing `node_trace`.

```
START -> triage
  triage ──(answerable)──▶ retrieval -> generate -> verify
  triage ──(clarify/out-of-scope/escalate)──▶ safe_response
  verify ──(passed)──▶ finalize → END
  verify ──(failed, retries left)──▶ generate   # exactly one retry
  verify ──(failed, retries exhausted)──▶ safe_response   # requires_human=True
```

### Node responsibilities

- **Triage** (`triage.py`) — classifies into exactly one of
  `answerable`, `requires_clarification`, `requires_escalation`, `out_of_scope`.
  Justification for the local (non-LLM) approach: a **hybrid of deterministic
  keyword rules + embedding similarity** to prototype sentences using the local
  sentence-transformers model. This is *fast, deterministic, reproducible, and
  cheap off-GPU* — and classification quality is more than adequate for 4
  coarse intents. A real MLLM adds latency and nondeterminism for no accuracy
  gain at this granularity.
- **`retrieval`** (`retrieval.py`) — embeds the query with the local
  `all-MiniLM-L6-v2`, computes cosine similarity against precomputed passage
  embeddings (KB sections + resolved-case records), returns top-k, optionally
  re-ranks with the local cross-encoder `ms-marco-MiniLM-L-6-v2`. Purely
  deterministic math; model only provides the mapping.
- **`generate`** (`generation.py`) — retrieves the context, builds a grounding
  prompt, and runs the local causal LM `Qwen/Qwen2.5-0.5B-Instruct`
  (instruction-tuned, ~0.5B, CPU-friendly). The model is instructed to answer
  strictly from context and to include `[Source: file.md]` markers; a
  post-processing step binds deterministic source passages and clips model
  chatter / repetition loops.
- **`verify`** (`verification.py`) — deterministic checks: (a) cited sources
  exist in the evidence, (b) source references present, (c) schema conformance
  (non-trivial string), (d) lexical grounding + no invented instructions. On
  failure the graph regenerates **once** (config `MAX_REVISIONS=1`); if it
  fails again the graph returns a safe explicit failure with
  `requires_human=True` instead of looping.
- **`safe_response`** (`safe_responses.py`) — pure template module used for
  the three non-answerable classes and for the post-revision failure path.
  Returns safe, human-flagged output with no fabricated facts.
- **`finalize`** (`graph.py`) — assembles the structured output JSON adhering
  to the schema and computes confidence from retrieval similarity.

### Orchestration properties (explicitly implemented)

- **Conditional routing**: `triage → retrieval` only for `answerable`;
  all other classes route directly to the safe-response node (they skip
  retrieval and generation entirely).
- **Retry/fallback path**: `verify → generate` once, then `safe_response`.
- **Hard loop guard**: `_route_after_verify` compares `revision_count` to
  `config.MAX_REVISIONS` and the graph never regenerates more than
  `MAX_REVISIONS` times (`graph.py:127`) — no infinite loops.
- **Deterministic vs. model-driven separation**:
  - deterministic modules: `retrieval.py` (math), `verification.py` (checks),
    `safe_responses.py` (templates), `graph.py` (routing/schema assembly),
    `triage.py`'s rules.
  - model-driven modules: `generation.py` (causal LM), `models.py` (weight
    loading) and the embedding similarity part of `triage.py`.
- **Structured logging**: every executed node + the conditional branch taken
  is recorded to stdout (with `--verbose`) and appended to
  `logs/run_<YYYYmmddTHHMMSS>.jsonl` (`logging.py`).

## 3. Output schema

```json
{
  "classification": "answerable",
  "answer": "Suggested response",
  "sources": [{"document": "workspace-settings.md", "passage": "Relevant excerpt or passage identifier"}],
  "confidence": 0.82,
  "requires_human": false,
  "reason": "Brief explanation",
  "node_trace": ["triage:answerable", "data_retrieval or retrieval:top_k", "..."]
}
```

The only addition over the proposed schema is `node_trace`, which the brief's
tests demand — it is strictly informative (used for the structure test) and
does not change the semantic contract.

## 4. Interface

CLI (primary). Two modes:

```bash
# answer one question
python -m support_agent.cli "My scheduled exports stopped after I changed my workspace timezone. What should I check?" --verbose

# run all sample questions produces sample_outputs/
python scripts/run_all_cases.py
```

`--verbose` also prints the per-node execution trace
(`triage → retrieval → generate → verify → finalize`) and writes JSONL run logs.

## 5. Local models (exact pins)

| Purpose | Model | Revision (commit) |
|---|---|---|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| Rerank | `cross-encoder/ms-marco-MiniLM-L-6-v2` | `c5ee24cb160f19beea0893ab7796b1df96625c6b8` |
| Generation | `Qwen/Qwen2.5-0.5B-Instruct` | `7ae557604adf67be50417f59c2c2f167def9a775` |

Full details in MODELS.md.

## 6. Setup / install

```bash
git clone <repo>
cd support-agent-network
python -m venv .venv
.\.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

**Python version**: 3.11+. Models download to `~/.cache/huggingface` on first
run; after that the code can run with `HF_HUB_OFFLINE=1` and **no network**.

Verification that no API is hit: grep for `api.openai|anthropic|bard|gemini|cohere`
— none exist. `config.py` contains no endpoint URLs other than Hugging Face
repo ids. `models.py` reads no API keys.

Loading the bundle takes ~10 s on this machine (see benchmarks.md). Qwen
generation on CPU is ~15 s/query; GPU (if the torch build provides CUDA) will
be marked down in benchmarks. If a CUDA wheel is installed, the code
auto-detects `torch.cuda.is_available()` and moves the models to the GPU.

## 7. Tests

```bash
python -m pytest tests/ -v
```

- `test_routing_structure.py` — asserts nodes exist, conditional edges fire
  correctly, the loop guard terminates, and retry happens **exactly once** —
  all without loading any real models (stubbed embedder + scripted classifier).
- `test_end_to_end.py` — the five required scenarios against the **real
  local models**:
  1. directly answerable question
  2. requires info from two KB documents (timezone + exports)
  3. ambiguous → clarification path
  4. out-of-scope (refund) → safe / human-required
  5. engineered verification failure → retry; forced repeat → `requires_human`

Tests never depend on the exact prose the LLM emits; they assert
`classification`, `node_trace`, `revision_count`, and `requires_human`.

## 8. Benchmarks

See `benchmarks.md` (measured on this machine with the CPUs available at test
time). Model load ~3.5s + 5.0s + 1.4s (embed+rerank+LLM). Answerable
queries ~15-16 s/query on CPU fp32; non-answerable paths complete in <0.2 s
(no LLM call).

## 9. Known limitations & trade-offs

- **Generation model is small (0.5B)**: quality is capped. It will answer
  correctly in the standard cases but occasionally echoes pseudo-claims,
  hedges, or prefers a wrong "yes"/"identity" answer if a real case is buried
  lower in the evidence. The verification node is intentionally conservative,
  which is why several sample answers legitimately fall back to
  `requires_human=True`.
- **Verification is heuristic, not semantic.** Grounding is lexical/word-overlap
  and citation-in-evidence; it does **not** run a second model to check factual
  entailment. A stronger generation model + an entailment-style rerank would
  strengthen this materially.
- **No persistent state / no chat memory**: each request is independent.
- **Windows-only tested**; the venv was created outside the repo (long-path
  constraint) so `requirements/venv` paths documented are generic.

### A single concrete design trade-off (asked for)

**Deterministic rule+embedding triage instead of an LLM triage.** I chose
speed + reproducibility over nuance: with four coarse classes a set of
keyword rules plus prototype-similarity margins over the free local embedding
model is enough to place the vast majority of support mail correctly, it runs
in milliseconds, and it is fully deterministic for CI. An LLM classifier
would be nicer in the ~5% of cases that need deeper domain reasoning, but it
triples engine latency on every call, burns tokens on trivial messages, and
risks crossing the "no hosted API" rule. So the design makes the four-way
gate cheap and deterministic and defers all nuanced judgment to the
generation/verification stage where it matters.

## 10. AI-assistant usage disclosure

This repository was produced with the assistance of an AI coding agent
(opencode). All authored content — the fictional product KB, resolved-case
data, the graph code, tests, and docs — was verified and reviewed by the
human submitter. No hosted or commercial model was invoked anywhere in the
pipeline; only the local Hugging Face checkpoints listed above.

## 11. What I would improve with more time

- Use a 1B–2B quantized instruction model (e.g.
  `HuggingFaceTB/SmolLM2-1.7B-Instruct` or 4-bit `Qwen2.5`) so answers are
  less brusque and the confidence gate can be lowered.
- Build a small evaluation harness with 50 fabricated golden pairs and report
  end-to-end pass rates, not just node-latency.
- Add a `extract-resolver` step (a second local model) that reads the
  evidence and scores answer⇒text overlap semantically.
- Persist conversation so a follow-up "did that work?" can reuse the prior run.
- Convert the retrieval index to FAISS for a larger corpus with the same math
  (the code already keeps the numpy fallback).

## 12. Copyright & data provenance

All knowledge-base content, resolved-case data, sample questions, and the
fictional product "Pulseboard" are original material fabricated for this
exercise. Nothing is copied from a real product or company. This repo has
no runtime dependency on any hosted model, API, or proprietary backend.
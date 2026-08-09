# Benchmarks

Captured on this machine during development. All timings are real measurements from local runs (see `scripts/benchmark.py`).

- **Device**: `cpu`
- **Embedding model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **LLM**: `Qwen/Qwen2.5-0.5B-Instruct`
- **LLM params**: `494,032,768`

## Model load time (seconds)

| model | seconds |
|-------|---------|
| embed | 2.32 |
| reranker | 4.54 |
| llm | 1.43 |

## Per-query latency (seconds, warm, end-to-end)

| sample | seconds |
|---|---|
| q-01-timezone-export | 15.39 |
| q-02-readonly-api | 15.78 |
| q-03-escalation | 0.15 |
| q-04-refund | 0.14 |
| q-05-ambiguous | 0.15 |
| **mean** | **6.32** |

_Method: models loaded once via `LocalModels.load()`, then the five sample questions answered end-to-end through the compiled LangGraph. Latency includes causal-LM generation on the detected device. To re-run offline: `set HF_HUB_OFFLINE=1` before launching._

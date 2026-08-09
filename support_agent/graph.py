"""LangGraph graph assembly for the Pulseboard support agent network.

Nodes (each a callable over the shared typed AgentState):

  triage        -> classify into 4 classes (hybrid rule + local embeddings)
  retrieval     -> embed query, top-k cosine over KB + cases (local index)
  generate      -> local causal LM answer grounded in retrieved evidence
  verify        -> deterministic checks; may route back to generate (once)
  safe_response -> deterministic safe fallback for non-answerable classes
  finalize      -> assemble the structured output schema dict

Conditional edges implement: routing by classification (out_of_scope /
requires_clarification / requires_escalation skip retrieval+generation), the
single verification->regenerate->safe-failure retry path, and a hard
iteration guard (MAX_REVISIONS=1) so the graph can never loop forever.

Deterministic logic (retrieval math, verification, routing, schema assembly)
lives in retrieval.py / verification.py / safe_responses.py / this module.
Model-driven reasoning (generation; the embedding classifier) lives in
generation.py / models.py / triage.py.
"""

from __future__ import annotations

import json
import time

from langgraph.graph import END, START, StateGraph

from support_agent import config
from support_agent.logging import RunLogger
from support_agent.models import LocalModelBundle
from support_agent.retrieval import RetrievalIndex
from support_agent.safe_responses import failure_after_revision, response_for_class
from support_agent.state import AgentState
from support_agent import triage
from support_agent import verification


class SupportAgentGraph:
    """Wires nodes + conditional edges and executes a query end-to-end."""

    def __init__(self, models: LocalModelBundle, use_reranker: bool = True) -> None:
        self.models = models
        self.index = RetrievalIndex(models.embed_model, use_reranker=use_reranker)
        self.index.build()
        self.logger: RunLogger | None = None
        self.graph = self._build()

    # -- node implementations -------------------------------------------------
    def _node_triage(self, state: AgentState) -> AgentState:
        q = state["query"]
        t0 = time.time()
        result = triage.classify(q, self.models.embed_model)
        if self.logger:
            self.logger.log("triage", result.label, {"seconds": round(time.time() - t0, 3)})
        return {
            "classification": result.label,
            "classification_reason": result.reason,
            "triage_confidence": result.confidence,
            "requires_human": False,
        }

    def _node_retrieval(self, state: AgentState) -> AgentState:
        q = state["query"]
        t0 = time.time()
        evidence = self.index.retrieve(q, top_k=config.RETRIEVAL_TOP_K)
        if self.logger:
            self.logger.log("retrieval", "top_k", {"seconds": round(time.time() - t0, 3), "hits": len(evidence)})
        return {"retrieved_evidence": evidence}

    def _node_generate(self, state: AgentState) -> AgentState:
        from support_agent.generation import generate_answer

        q = state["query"]
        evidence = state.get("retrieved_evidence", [])
        t0 = time.time()
        answer, gen_seconds = generate_answer(q, evidence, self.models)
        revision_count = state.get("revision_count", 0) + 1
        if self.logger:
            self.logger.log("generate", "attempt_" + str(revision_count), {"seconds": round(gen_seconds, 3)})
        return {"draft_answer": answer, "revision_count": revision_count}

    def _node_verify(self, state: AgentState) -> AgentState:
        answer = state.get("draft_answer", "")
        evidence = state.get("retrieved_evidence", [])
        result = verification.check_answer(answer, evidence)
        if self.logger:
            self.logger.log(
                "verify",
                "passed" if result["passed"] else "failed",
                {"reason": result["reason"]},
            )
        return {"verification_result": result}

    def _node_safe_response(self, state: AgentState) -> AgentState:
        classification = state.get("classification", "requires_clarification")
        reason = state.get("classification_reason", "classified non-answerable")
        if state.get("revision_count", 0) > 0 or state.get("verification_result", {}).get("passed") is False:
            out = failure_after_revision(classification, reason)
        else:
            out = response_for_class(classification, state.get("query", ""), reason)
        if self.logger:
            self.logger.log("safe_response", classification)
        return {"final_output": out, "requires_human": out["requires_human"], "reason": out["reason"]}

    def _node_finalize(self, state: AgentState) -> AgentState:
        classification = state.get("classification", "answerable")
        answer = state.get("draft_answer", "")
        evidence = state.get("retrieved_evidence", [])
        vres = state.get("verification_result", {})
        confidence = verification.confidence_from_evidence(evidence)
        if vres.get("passed"):
            confidence = round(min(1.0, confidence + 0.1), 2)

        sources = []
        for ev in evidence:
            sources.append({"document": ev["document"], "passage": ev["passage"]})
        sources = _dedupe_sources(sources)

        final = {
            "classification": classification,
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "requires_human": False,
            "reason": vres.get("reason", "answer generated and verified"),
        }
        if self.logger:
            self.logger.log("finalize", "answerable")
        return {"final_output": final, "requires_human": False, "reason": final["reason"]}

    # -- conditional routing --------------------------------------------------
    def _route_after_triage(self, state: AgentState) -> str:
        cls = state.get("classification", "requires_clarification")
        if cls == "answerable":
            return "retrieval"
        return "safe_response"

    def _route_after_verify(self, state: AgentState) -> str:
        vres = state.get("verification_result", {})
        passed = vres.get("passed", False)
        revisions = state.get("revision_count", 0)
        if passed:
            return "finalize"
        if revisions <= config.MAX_REVISIONS:
            # loop guard: retry at most MAX_REVISIONS times, then safe-fail
            return "generate"
        return "safe_response"

    def _build(self):
        g = StateGraph(AgentState)

        g.add_node("triage", self._node_triage)
        g.add_node("retrieval", self._node_retrieval)
        g.add_node("generate", self._node_generate)
        g.add_node("verify", self._node_verify)
        g.add_node("safe_response", self._node_safe_response)
        g.add_node("finalize", self._node_finalize)

        g.add_edge(START, "triage")
        g.add_conditional_edges(
            "triage", self._route_after_triage, {"retrieval": "retrieval", "safe_response": "safe_response"}
        )
        g.add_edge("retrieval", "generate")
        g.add_edge("generate", "verify")
        g.add_conditional_edges(
            "verify", self._route_after_verify, {"finalize": "finalize", "generate": "generate", "safe_response": "safe_response"}
        )
        g.add_edge("finalize", END)
        g.add_edge("safe_response", END)
        return g.compile()

    # -- execution ------------------------------------------------------------
    def run(self, query: str, verbose: bool = False) -> dict:
        run_id = _make_run_id()
        self.logger = RunLogger(config.LOG_DIR, run_id, verbose=verbose)
        if verbose:
            print(f"run_id={run_id}  query={query!r}")

        state = self.graph.invoke(
            {"query": query, "revision_count": 0, "requires_human": False, "reason": ""}
        )
        final_output = state.get("final_output")
        if final_output is None:
            final_output = {
                "classification": state.get("classification", "unknown"),
                "answer": "No final output produced.",
                "sources": [],
                "confidence": 0.0,
                "requires_human": True,
                "reason": "graph terminated without finalize/safe_response",
            }
        final_output["node_trace"] = _build_trace(self.logger)
        self.logger.finalize(final_output)
        if verbose:
            print(json.dumps(final_output, ensure_ascii=False, indent=2))
        return final_output


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for s in sources:
        key = (s["document"], s["passage"])
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def _build_trace(logger: RunLogger) -> list[str]:
    return [f"{r['node']}:{r['branch']}" for r in logger._records if r.get("node") not in ("run.end",)]


def _make_run_id() -> str:
    return time.strftime("%Y%m%dT%H%M%S") + str(abs(hash(time.time())) % 10000).zfill(4)
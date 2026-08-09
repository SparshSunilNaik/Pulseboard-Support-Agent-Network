"""Render graph_diagram.png from the compiled LangGraph.

Tries, in order:
  1. LangGraph's built-in ``draw_mermaid_png()`` (requires the optional
     `graphviz`-free mermaid renderer; on Windows this usually needs the
     `mermaid` npm CLI, so we fall through).
  2. A hand-built Graphviz DOT file rendered through the `graphviz` package
     (requires the Graphviz binary on PATH; we fall back to step 3 if absent).
  3. A pure-python renderer using `matplotlib` to draw the node/edge diagram
     (no external binaries, always works).

The PNG is committed to the repo so reviewers never need graphviz/mermaid.
"""

from __future__ import annotations

import sys

from support_agent import config
from support_agent.models import LocalModels
from support_agent.graph import SupportAgentGraph


def draw() -> None:
    target = config.ROOT_DIR / "graph_diagram.png"

    print("Compiling graph (loading models may take a moment)...")
    bundle = LocalModels(use_reranker=False).load()
    g = SupportAgentGraph(bundle, use_reranker=False)

    # Try method 1: langgraph's built-in mermaid png.
    try:
        data = g.graph.get_graph().draw_mermaid_png()
        if data and len(data) > 100:
            target.write_bytes(data)
            print(f"graph_diagram.png written via langgraph draw_mermaid_png ({len(data)} bytes)")
            return
    except Exception as e:  # noqa: BLE001
        print(f"  langgraph mermaid png unavailable: {e.__class__.__name__}: {e}")

    # Try method 2: graphviz python package.
    try:
        import graphviz  # type: ignore

        dot = graphviz.Digraph(format="png")
        dot.attr(rankdir="TB", fontname="Helvetica")
        dot.attr("node", shape="box", style="rounded,filled", fillcolor="#eef3ff", fontname="Helvetica")
        dot.attr("edge", fontname="Helvetica", fontsize="10")
        dot.node("START", "START", shape="oval", fillcolor="#dff0d8")
        dot.node("triage", "triage\n(classify request)")
        dot.node("retrieval", "retrieval\n(top-k cosine + rerank)")
        dot.node("generate", "generate\n(local causal LM)")
        dot.node("verify", "verify\n(deterministic checks)")
        dot.node("finalize", "finalize\n(assemble schema)")
        dot.node("safe_response", "safe_response\n(no model)")
        dot.node("END", "END", shape="oval", fillcolor="#f2dede")
        dot.edge("START", "triage")
        dot.edge("triage", "retrieval", label="answerable")
        dot.edge("triage", "safe_response", label="clarify/out-of-scope/escalate")
        dot.edge("retrieval", "generate")
        dot.edge("generate", "verify")
        dot.edge("verify", "finalize", label="passed")
        dot.edge("verify", "generate", label="fail (retry ≤ 1)")
        dot.edge("verify", "safe_response", label="fail after retry")
        dot.edge("finalize", "END")
        dot.edge("safe_response", "END")
        dot.render(str(target.with_suffix("")))
        print("graph_diagram.png written via graphviz")
        return
    except Exception as e:  # noqa: BLE001
        print(f"  graphviz unavailable: {e.__class__.__name__}: {e}")

    # Try method 3: matplotlib fallback.
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch

        fig, ax = plt.subplots(figsize=(9, 7))
        ax.axis("off")

        pos = {
            "START": (0.5, 0.97),
            "triage": (0.5, 0.84),
            "retrieval": (0.18, 0.62),
            "generate": (0.5, 0.40),
            "verify": (0.82, 0.62),
            "finalize": (0.5, 0.16),
            "safe_response": (0.9, 0.16),
            "END": (0.5, 0.02),
        }

        def box(name, text, color="#eef3ff"):
            x, y = pos[name]
            p = FancyBboxPatch((x - 0.13, y - 0.05), 0.26, 0.10, boxstyle="round,pad=0.01", fc=color, ec="#666")
            ax.add_patch(p)
            ax.text(x, y, text, ha="center", va="center", fontsize=9, wrap=True)

        box("START", "START", "#dff0d8")
        box("triage", "triage\nclassify request", "#fff3cd")
        box("retrieval", "retrieval\ntop-k cosine + rerank")
        box("generate", "generate\nlocal causal LM")
        box("verify", "verify\ndeterministic checks")
        box("finalize", "finalize\nschema assembly", "#d9edf7")
        box("safe_response", "safe_response\nno model", "#f2dede")
        box("END", "END", "#dff0d8")

        def edge(a, b, label=""):
            ax.annotate(
                "",
                xy=pos[b],
                xytext=pos[a],
                arrowprops=dict(arrowstyle="->", color="#555", lw=1.2),
            )
            if label:
                mx = (pos[a][0] + pos[b][0]) / 2 + 0.02
                my = (pos[a][1] + pos[b][1]) / 2 + 0.02
                ax.text(mx, my, label, fontsize=7.5, color="#444", ha="center")

        edge("START", "triage")
        edge("triage", "retrieval", "answerable")
        edge("triage", "safe_response", "clarify / out-of-scope / escalate")
        edge("retrieval", "generate")
        edge("generate", "verify")
        edge("verify", "finalize", "passed")
        edge("verify", "generate", "fail (retry <= 1)")
        edge("verify", "safe_response", "fail after retry")
        edge("finalize", "END")
        edge("safe_response", "END")

        fig.suptitle("Pulseboard Support Agent Network — LangGraph", fontsize=12)
        fig.savefig(target, dpi=150, bbox_inches="tight")
        print("graph_diagram.png written via matplotlib fallback")
        return
    except Exception as e:  # noqa: BLE001
        print(f"  matplotlib fallback failed: {e.__class__.__name__}: {e}")

    raise RuntimeError("Could not render graph diagram with any available backend.")


if __name__ == "__main__":
    sys.exit(draw())
"""LangGraph state machine for the research agent workflow.

Graph topology::

    START → discover_publications → retrieve_evidence → generate_report → END

Each node updates the shared ``ResearchState`` and returns a partial state
patch that LangGraph merges into the running state.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from packages.agents.research.nodes import (
    discover_publications,
    generate_report,
    retrieve_evidence,
)
from packages.agents.research.state import ResearchState


def build_research_graph() -> Any:
    """Build and compile the LangGraph research agent state machine.

    Returns a compiled LangGraph graph ready to be invoked with an initial
    ``ResearchState`` dictionary.
    """
    builder = StateGraph(ResearchState)

    builder.add_node("discover_publications", discover_publications)
    builder.add_node("retrieve_evidence", retrieve_evidence)
    builder.add_node("generate_report", generate_report)

    builder.set_entry_point("discover_publications")
    builder.add_edge("discover_publications", "retrieve_evidence")
    builder.add_edge("retrieve_evidence", "generate_report")
    builder.add_edge("generate_report", END)

    return builder.compile()


# Module-level compiled graph instance (lazy, safe to import).
research_graph = build_research_graph()


async def run_research_agent(
    query: str,
    topic: str | None = None,
    crisis_context: str | None = None,
    max_publications: int = 10,
    max_evidence_per_publication: int = 3,
) -> dict[str, Any]:
    """Run the full research agent workflow.

    Args:
        query: Search query for publication discovery.
        topic: Human-readable topic name (defaults to query).
        crisis_context: Optional humanitarian crisis context.
        max_publications: Maximum number of publications to retrieve.
        max_evidence_per_publication: Maximum evidence snippets per publication.

    Returns:
        The final state dict after graph execution, including ``report``,
        ``status``, ``publications``, ``evidence``, and ``run_id``.
    """
    initial_state: ResearchState = {
        "query": query,
        "topic": topic or query,
        "crisis_context": crisis_context,
        "status": "pending",
        "publications": [],
        "evidence": [],
        "report": None,
        "error": None,
        "run_id": None,
        "max_publications": max_publications,
        "max_evidence_per_publication": max_evidence_per_publication,
    }

    final_state = await research_graph.ainvoke(initial_state)
    return dict(final_state)

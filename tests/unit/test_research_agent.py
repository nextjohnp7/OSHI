"""Unit tests for the research agent (no network required)."""

import pytest

from packages.agents.research.graph import build_research_graph, run_research_agent
from packages.agents.research.nodes import generate_report
from packages.agents.research.state import ResearchState


def test_graph_builds_successfully():
    graph = build_research_graph()
    assert graph is not None


def test_generate_report_basic():
    state: ResearchState = {
        "query": "climate change agriculture",
        "topic": "Climate Change",
        "crisis_context": "Drought in East Africa",
        "publications": [
            {
                "id": "pub-1",
                "title": "Climate Impacts on Crop Yields",
                "authors": ["Alice Smith", "Bob Jones"],
                "abstract": "Rising temperatures reduce maize yields by 15%.",
                "source": "openalex",
                "url": "https://openalex.org/pub-1",
                "published_date": "2023-01-01",
                "relevance_score": 0.95,
            }
        ],
        "evidence": [
            {
                "publication_id": "pub-1",
                "publication_title": "Climate Impacts on Crop Yields",
                "quote": "Rising temperatures reduce maize yields by 15%.",
                "relevance_to_query": 0.95,
            }
        ],
    }

    result = generate_report(state)

    assert result["status"] == "completed"
    report = result["report"]
    assert report is not None
    assert "Climate Change" in report
    assert "climate change agriculture" in report
    assert "Drought in East Africa" in report
    assert "Climate Impacts on Crop Yields" in report
    assert "Rising temperatures reduce maize yields by 15%." in report


def test_generate_report_empty():
    state: ResearchState = {
        "query": "nonexistent topic",
        "topic": "Nonexistent",
        "publications": [],
        "evidence": [],
    }

    result = generate_report(state)

    assert result["status"] == "completed"
    assert result["report"] is not None
    assert "0 publications" in result["report"]


@pytest.mark.asyncio
async def test_run_research_agent_returns_dict(monkeypatch):
    """run_research_agent should return a dict even if network fails (graceful degradation)."""
    # We cannot mock network easily here; just verify it returns a dict with expected keys.
    # If network is unavailable, nodes will catch exceptions and return empty results.
    result = await run_research_agent(
        query="test query",
        topic="Test Topic",
        max_publications=2,
        max_evidence_per_publication=1,
    )

    assert isinstance(result, dict)
    assert "status" in result
    assert "publications" in result
    assert "evidence" in result
    assert "report" in result
    assert "run_id" in result
    assert result["query"] == "test query"
    assert result["topic"] == "Test Topic"

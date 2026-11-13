"""LangGraph state definition for the research agent workflow.

The state tracks the progress of a research run from publication discovery
through evidence retrieval to report generation.
"""

from typing import Any, List, Optional, TypedDict


class PublicationResult(TypedDict):
    """A single publication discovered during research."""
    id: str
    title: str
    authors: List[str]
    abstract: str
    source: str  # "openalex" or "crossref"
    url: str
    published_date: Optional[str]
    relevance_score: float


class EvidenceItem(TypedDict):
    """A piece of evidence extracted from a publication."""
    publication_id: str
    publication_title: str
    quote: str
    relevance_to_query: float


class ResearchState(TypedDict, total=False):
    """State carried through the LangGraph research agent workflow.

    Fields marked total=False are optional; the graph populates them
    progressively as nodes execute.
    """

    # Input
    query: str
    topic: str
    crisis_context: Optional[str]

    # Intermediate results
    publications: List[PublicationResult]
    evidence: List[EvidenceItem]

    # Final output
    report: Optional[str]

    # Status tracking
    status: str  # "pending", "discovering", "retrieving", "generating", "completed", "failed"
    error: Optional[str]
    run_id: Optional[str]

    # Configuration
    max_publications: int
    max_evidence_per_publication: int

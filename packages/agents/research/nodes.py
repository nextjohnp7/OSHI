"""LangGraph nodes for the research agent workflow.

Nodes:
- discover_publications: search OpenAlex + Crossref for publications matching the query
- retrieve_evidence: extract evidence snippets from discovered publications
- generate_report: compile a research report from publications and evidence
"""

from __future__ import annotations

import uuid
from typing import Any

from apps.api.service import PublicationService
from packages.document_processing.embeddings import (
    cosine_similarity,
    embed_text,
)
from packages.agents.research.state import (
    EvidenceItem,
    PublicationResult,
    ResearchState,
)


async def discover_publications(state: ResearchState) -> dict[str, Any]:
    """Search OpenAlex and Crossref for publications matching the query.

    Updates state with:
    - ``status`` = "discovering"
    - ``publications`` = list of discovered publications (deduped, relevance-scored)
    - ``run_id`` = generated UUID if not already set
    """
    query = state.get("query", "")
    topic = state.get("topic", "")
    max_publications = state.get("max_publications", 10)
    run_id = state.get("run_id") or str(uuid.uuid4())

    service = PublicationService()
    all_publications: list[PublicationResult] = []

    # Search both OpenAlex and Crossref
    for source in ("openalex", "crossref"):
        try:
            stored = await service.search_and_store(
                query=query,
                limit=max_publications // 2 + 1,
                source=source,
            )
            for pub in stored:
                all_publications.append(
                    {
                        "id": str(pub.id),
                        "title": pub.title or "",
                        "authors": pub.authors or [],
                        "abstract": pub.abstract or "",
                        "source": pub.source_name or source,
                        "url": pub.source_url or "",
                        "published_date": (
                            pub.publication_date.isoformat()
                            if pub.publication_date
                            else None
                        ),
                        "relevance_score": 0.0,  # filled below
                    }
                )
        except Exception:  # pragma: no cover - network failure, one source may fail
            continue

    # Dedupe by title (case-insensitive)
    seen_titles: set[str] = set()
    deduped: list[PublicationResult] = []
    for pub in all_publications:
        key = pub["title"].lower().strip()
        if key and key not in seen_titles:
            seen_titles.add(key)
            deduped.append(pub)

    # Score relevance using embedding cosine similarity against the query
    if deduped and query:
        query_vector = embed_text(query)
        for pub in deduped:
            text = f"{pub['title']} {pub['abstract']}"
            pub_vector = embed_text(text)
            pub["relevance_score"] = cosine_similarity(query_vector, pub_vector)

    # Sort by relevance descending, take top N
    deduped.sort(key=lambda p: p["relevance_score"], reverse=True)
    top = deduped[:max_publications]

    return {
        "run_id": run_id,
        "status": "discovering",
        "publications": top,
    }


async def retrieve_evidence(state: ResearchState) -> dict[str, Any]:
    """Extract evidence snippets from discovered publications.

    Updates state with:
    - ``status`` = "retrieving"
    - ``evidence`` = list of evidence items with quotes and relevance scores
    """
    publications = state.get("publications", [])
    query = state.get("query", "")
    max_evidence = state.get("max_evidence_per_publication", 3)

    if not publications:
        return {"status": "retrieving", "evidence": []}

    query_vector = embed_text(query) if query else None
    evidence: list[EvidenceItem] = []

    for pub in publications:
        abstract = pub.get("abstract", "") or ""
        title = pub.get("title", "") or ""

        # Split abstract into sentences as candidate evidence snippets
        sentences = [s.strip() for s in abstract.replace("? ", "?\n").replace(". ", ".\n").split("\n") if s.strip()]

        scored: list[tuple[float, str]] = []
        for sentence in sentences:
            if query_vector is not None:
                vec = embed_text(sentence)
                score = cosine_similarity(query_vector, vec)
            else:
                score = 0.0
            scored.append((score, sentence))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_sentences = scored[:max_evidence]

        for score, sentence in top_sentences:
            evidence.append(
                {
                    "publication_id": pub.get("id", ""),
                    "publication_title": title,
                    "quote": sentence,
                    "relevance_to_query": float(score),
                }
            )

    return {"status": "retrieving", "evidence": evidence}


def generate_report(state: ResearchState) -> dict[str, Any]:
    """Compile a research report from publications and evidence.

    Updates state with:
    - ``status`` = "completed"
    - ``report`` = markdown-formatted research report
    """
    query = state.get("query", "")
    topic = state.get("topic", "")
    crisis_context = state.get("crisis_context")
    publications = state.get("publications", [])
    evidence = state.get("evidence", [])

    lines: list[str] = []
    lines.append(f"# Research Report: {topic or query}")
    lines.append("")
    lines.append(f"**Query:** {query}")
    if crisis_context:
        lines.append(f"**Crisis Context:** {crisis_context}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"This report presents findings from {len(publications)} publications "
        f"discovered across OpenAlex and Crossref, with {len(evidence)} evidence "
        f"snippets extracted for query: '{query}'."
    )
    lines.append("")

    lines.append("## Publications")
    lines.append("")
    for i, pub in enumerate(publications, 1):
        lines.append(f"### {i}. {pub.get('title', 'Untitled')}")
        lines.append("")
        lines.append(f"- **Source:** {pub.get('source', 'unknown')}")
        if pub.get("published_date"):
            lines.append(f"- **Published:** {pub['published_date']}")
        if pub.get("url"):
            lines.append(f"- **URL:** {pub['url']}")
        if pub.get("authors"):
            authors = ", ".join(pub["authors"][:5])
            lines.append(f"- **Authors:** {authors}")
        relevance = pub.get("relevance_score", 0.0)
        lines.append(f"- **Relevance Score:** {relevance:.3f}")
        abstract = pub.get("abstract", "")
        if abstract:
            lines.append(f"- **Abstract:** {abstract[:500]}{'...' if len(abstract) > 500 else ''}")
        lines.append("")

    lines.append("## Evidence")
    lines.append("")
    if evidence:
        for i, ev in enumerate(evidence, 1):
            lines.append(f"{i}. **{ev.get('publication_title', 'Unknown')}**")
            lines.append(f"   - Quote: {ev.get('quote', '')}")
            lines.append(f"   - Relevance: {ev.get('relevance_to_query', 0.0):.3f}")
            lines.append("")
    else:
        lines.append("No evidence snippets extracted.")
        lines.append("")

    lines.append("## Conclusion")
    lines.append("")
    lines.append(
        f"The research identified {len(publications)} relevant publications "
        f"for the query '{query}'. Evidence was extracted from the most "
        f"relevant sections to support further analysis."
    )
    lines.append("")

    return {
        "status": "completed",
        "report": "\n".join(lines),
    }

"""OpenAlex publication connector.

OpenAlex is an open scholarly index (https://api.openalex.org). Basic usage does not
require an API key; providing a `mailto` query parameter joins the polite pool and
raises rate limits. See https://docs.openalex.org/ for the full contract.

Fields retrieved per work:
- id            : OpenAlex work URL (e.g. https://openalex.org/W2741809807)
- doi           : DOI (may be None)
- title         : display title
- publication_date : ISO date string
- authorships   : list of { author: { display_name } }
- primary_location : { landing_page_url, pdf_url, ... }
- abstract_inverted_index : dict word -> [positions]
- license       : SPDX-ish license string (may be None)
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

import httpx

from packages.connectors.scientific.schemas import NormalizedPublication


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Rebuild plain-text abstract from OpenAlex inverted index."""
    if inverted_index is None:
        return None
    positioned: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for position in positions:
            positioned.append((position, word))
    positioned.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned)


def _extract_authors(authorships: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    authors: list[dict[str, str]] = []
    for authorship in authorships or []:
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if name:
            authors.append({"name": name})
    return authors


def _extract_source_url(work: dict[str, Any]) -> str | None:
    primary_location = work.get("primary_location") or {}
    url = primary_location.get("landing_page_url")
    if url:
        return url
    return work.get("id")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _work_id(work: dict[str, Any]) -> str:
    """Return the bare OpenAlex work identifier (last segment of the id URL)."""
    work_id = work.get("id") or ""
    return work_id.rstrip("/").split("/")[-1]


def _content_hash(normalized: dict[str, Any]) -> str:
    payload = f"{normalized['source_name']}:{normalized['source_id']}:{normalized['title']}"
    return sha256(payload.encode("utf-8")).hexdigest()


class OpenAlexConnector:
    """Thin client over the OpenAlex works endpoint."""

    base_url = "https://api.openalex.org/works"

    def __init__(self, mailto: str | None = None, timeout: float = 30.0) -> None:
        self.mailto = mailto
        self.timeout = timeout

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "search": query,
            "per-page": max(1, min(limit, 100)),
            "page": 1,
        }
        if self.mailto:
            params["mailto"] = self.mailto

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])

    def normalize(self, work: dict[str, Any]) -> NormalizedPublication:
        source_id = _work_id(work)
        abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
        authors = _extract_authors(work.get("authorships"))
        source_url = _extract_source_url(work)
        publication_date = _parse_date(work.get("publication_date"))

        normalized = NormalizedPublication(
            source_name="openalex",
            source_id=source_id,
            title=work.get("display_name") or work.get("title") or "",
            abstract=abstract,
            authors=authors,
            publication_date=publication_date,
            source_url=source_url,
            license=work.get("license"),
        )
        normalized.content_hash = _content_hash(
            {
                "source_name": normalized.source_name,
                "source_id": normalized.source_id,
                "title": normalized.title,
            }
        )
        return normalized

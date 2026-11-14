"""arXiv publication connector.

arXiv is an open preprint repository for STEM disciplines
(https://arxiv.org). The API returns Atom XML and does not require an API key.
See https://info.arxiv.org/help/api/index.html for the full contract.

Fields retrieved per entry:
- id          : arXiv identifier URL (e.g. http://arxiv.org/abs/2301.00001v1)
- title       : paper title
- authors     : list of { name }
- summary     : abstract plain text
- published   : ISO date string
- link        : HTML and PDF URLs
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
import re
import xml.etree.ElementTree as ET

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from packages.connectors.scientific.schemas import NormalizedPublication

_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # arXiv publishes dates like 2023-01-15T00:00:00Z
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _arxiv_id(url: str | None) -> str:
    """Return the bare arXiv identifier (last path segment, version stripped)."""
    if not url:
        return ""
    path = url.rstrip("/").split("/")[-1]
    # Strip version suffix like v1, v2
    return re.sub(r"v\d+$", "", path)


def _content_hash(normalized: dict[str, Any]) -> str:
    payload = f"{normalized['source_name']}:{normalized['source_id']}:{normalized['title']}"
    return sha256(payload.encode("utf-8")).hexdigest()


class ArxivConnector:
    """Thin client over the arXiv API query endpoint.

    Supports an optional ``mailto`` parameter for the polite pool
    (https://info.arxiv.org/help/api/index.html).
    """

    base_url = "https://export.arxiv.org/api/query"

    def __init__(self, mailto: str | None = None, timeout: float = 30.0) -> None:
        self.mailto = mailto
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (
                httpx.HTTPStatusError,
                httpx.RequestError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
            )
        ),
    )
    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "search_query": f'all:{query}',
            "start": 0,
            "max_results": max(1, min(limit, 100)),
        }
        if self.mailto:
            params["mailto"] = self.mailto

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            return self._parse_atom(response.text)

    def _parse_atom(self, xml_text: str) -> list[dict[str, Any]]:
        """Parse arXiv Atom XML into a list of raw entry dicts."""
        root = ET.fromstring(xml_text)
        entries: list[dict[str, Any]] = []

        for entry in root.findall(f"{_ATOM_NS}entry"):
            id_elem = entry.find(f"{_ATOM_NS}id")
            title_elem = entry.find(f"{_ATOM_NS}title")
            summary_elem = entry.find(f"{_ATOM_NS}summary")
            published_elem = entry.find(f"{_ATOM_NS}published")
            updated_elem = entry.find(f"{_ATOM_NS}updated")

            authors: list[dict[str, str]] = []
            for author in entry.findall(f"{_ATOM_NS}author"):
                name_elem = author.find(f"{_ATOM_NS}name")
                if name_elem is not None and name_elem.text:
                    authors.append({"name": name_elem.text.strip()})

            links: list[dict[str, str]] = []
            for link in entry.findall(f"{_ATOM_NS}link"):
                links.append(
                    {
                        "href": link.get("href", ""),
                        "rel": link.get("rel", ""),
                        "type": link.get("type", ""),
                    }
                )

            entries.append(
                {
                    "id": id_elem.text if id_elem is not None else "",
                    "title": " ".join((title_elem.text or "").split())
                    if title_elem is not None
                    else "",
                    "summary": " ".join((summary_elem.text or "").split())
                    if summary_elem is not None
                    else "",
                    "published": published_elem.text if published_elem is not None else "",
                    "updated": updated_elem.text if updated_elem is not None else "",
                    "authors": authors,
                    "links": links,
                }
            )

        return entries

    def normalize(self, entry: dict[str, Any]) -> NormalizedPublication:
        source_id = _arxiv_id(entry.get("id"))
        title = entry.get("title", "")
        abstract = entry.get("summary", "")
        authors = entry.get("authors", [])
        published = _parse_date(entry.get("published"))

        # Prefer the HTML landing page link; fall back to the id URL.
        source_url = entry.get("id")
        for link in entry.get("links", []):
            if link.get("rel") == "alternate":
                source_url = link.get("href", source_url)
                break

        normalized = NormalizedPublication(
            source_name="arxiv",
            source_id=source_id,
            title=title,
            abstract=abstract,
            authors=authors,
            publication_date=published,
            source_url=source_url,
            license=None,
        )
        normalized.content_hash = _content_hash(
            {
                "source_name": normalized.source_name,
                "source_id": normalized.source_id,
                "title": normalized.title,
            }
        )
        return normalized

"""PubMed / Europe PMC publication connector.

Europe PMC is an open biomedical and life sciences literature database
(https://europepmc.org). The REST API returns JSON and does not require an
API key for basic usage. See https://europepmc.org/docs/Web_Services_Guide.

Fields retrieved per result:
- id            : Europe PMC / PubMed ID
- title         : article title
- authorString  : semicolon-separated author names
- abstractText  : abstract plain text (may contain XML tags)
- pubDate       : publication date string
- doi           : DOI (may be None)
- pmcid         : PubMed Central ID (may be None)
- isOpenAccess  : boolean
- inEPMC        : boolean
- hasPDF        : boolean
- citedByCount  : integer
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
import re

import httpx

from packages.connectors.scientific.schemas import NormalizedPublication

_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_DATE_NAMED_RE = re.compile(r"(\d{4})\s+([A-Za-z]{3})\s+(\d{1,2})")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str | None) -> str | None:
    if not value:
        return None
    text = _HTML_TAG_RE.sub(" ", value)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    match = _DATE_RE.search(value)
    if match:
        try:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return datetime(year, month, day, tzinfo=timezone.utc)
        except ValueError:
            return None
    match = _DATE_NAMED_RE.search(value)
    if match:
        try:
            year = int(match.group(1))
            month = _MONTH_NAMES.get(match.group(2).lower()[:3])
            day = int(match.group(3))
            if month is None:
                return None
            return datetime(year, month, day, tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _extract_authors(author_string: str | None) -> list[dict[str, str]]:
    if not author_string:
        return []
    authors: list[dict[str, str]] = []
    for raw in author_string.split(";"):
        name = raw.strip()
        if name:
            authors.append({"name": name})
    return authors


def _content_hash(normalized: dict[str, Any]) -> str:
    payload = f"{normalized['source_name']}:{normalized['source_id']}:{normalized['title']}"
    return sha256(payload.encode("utf-8")).hexdigest()


class PubMedConnector:
    """Thin client over the Europe PMC REST search endpoint."""

    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "query": query,
            "format": "json",
            "pageSize": max(1, min(limit, 100)),
            "page": 1,
            "resultType": "core",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("resultList", {}).get("result", [])

    def normalize(self, item: dict[str, Any]) -> NormalizedPublication:
        source_id = str(item.get("id") or item.get("pmid") or "")
        title = item.get("title") or ""
        abstract = _strip_html(item.get("abstractText"))
        authors = _extract_authors(item.get("authorString"))
        publication_date = _parse_date(item.get("pubDate"))

        # Prefer DOI as a stable URL; fall back to Europe PMC article URL.
        source_url = item.get("doi")
        if not source_url:
            source_url = f"https://europepmc.org/article/{source_id}" if source_id else None

        license_str = item.get("license") if isinstance(item.get("license"), str) else None

        normalized = NormalizedPublication(
            source_name="pubmed",
            source_id=source_id,
            title=title,
            abstract=abstract,
            authors=authors,
            publication_date=publication_date,
            source_url=source_url,
            license=license_str,
        )
        normalized.content_hash = _content_hash(
            {
                "source_name": normalized.source_name,
                "source_id": normalized.source_id,
                "title": normalized.title,
            }
        )
        return normalized

"""Crossref publication connector.

Crossref is an open scholarly DOI registration agency (https://api.crossref.org).
Basic usage does not require an API key; providing a `mailto` query parameter joins
the polite pool and raises rate limits. See https://github.com/CrossRef/rest-api-doc
for the full contract.

Fields retrieved per work:
- DOI            : persistent identifier (used as source_id)
- title          : list, first element is the display title
- author         : list of { given, family, sequence }
- published      : { date-parts: [[year, month, day]] }
- published-online : { date-parts: [...] } (fallback when published missing)
- abstract       : HTML string (may contain <jats> markup)
- URL            : https://doi.org/...
- license        : list of { URL, ... } (may be None)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from packages.connectors.scientific.schemas import NormalizedPublication

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str | None) -> str | None:
    if not value:
        return None
    text = _HTML_TAG_RE.sub(" ", value)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _extract_authors(authors: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for author in authors or []:
        given = author.get("given") or ""
        family = author.get("family") or ""
        name = f"{given} {family}".strip() or given or family
        if name:
            result.append({"name": name})
    return result


def _parse_date(parts: list[list[int]] | None) -> datetime | None:
    if not parts:
        return None
    try:
        date_parts = parts[0]
        year = date_parts[0]
        month = date_parts[1] if len(date_parts) > 1 else 1
        day = date_parts[2] if len(date_parts) > 2 else 1
        return datetime(year, month, day, tzinfo=timezone.utc)
    except (IndexError, ValueError, TypeError):
        return None


class CrossrefConnector:
    """Thin client over the Crossref works endpoint."""

    base_url = "https://api.crossref.org/works"

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
            "query.bibliographic": query,
            "rows": max(1, min(limit, 100)),
            "select": "DOI,title,author,published,published-online,abstract,URL,license",
        }
        if self.mailto:
            params["mailto"] = self.mailto

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            items = data.get("message", {}).get("items", [])
            return items

    def normalize(self, item: dict[str, Any]) -> NormalizedPublication:
        doi = item.get("DOI") or ""
        title_list = item.get("title") or []
        title = title_list[0] if title_list else ""

        # Prefer published, fall back to published-online.
        published = item.get("published") or item.get("published-online") or {}
        date_parts = published.get("date-parts")
        publication_date = _parse_date(date_parts)

        abstract = _strip_html(item.get("abstract"))
        authors = _extract_authors(item.get("author"))
        source_url = item.get("URL")

        license_list = item.get("license")
        license_str = None
        if license_list and isinstance(license_list, list) and len(license_list) > 0:
            license_str = license_list[0].get("URL")

        normalized = NormalizedPublication(
            source_name="crossref",
            source_id=doi,
            title=title,
            abstract=abstract,
            authors=authors,
            publication_date=publication_date,
            source_url=source_url,
            license=license_str,
        )
        normalized.content_hash = self._content_hash(normalized)
        return normalized

    @staticmethod
    def _content_hash(normalized: NormalizedPublication) -> str:
        payload = f"{normalized.source_name}:{normalized.source_id}:{normalized.title}"
        return sha256(payload.encode("utf-8")).hexdigest()

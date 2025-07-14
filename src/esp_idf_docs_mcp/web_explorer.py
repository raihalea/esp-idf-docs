"""Online ESP-IDF Documentation Explorer.

This module provides online documentation search capabilities by fetching
content from the official ESP-IDF documentation website.
"""

import logging
import re
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from .config import ServerConfig
from .exceptions import DocumentNotFoundError, SearchError
from .util import ValidationUtils

logger = logging.getLogger(__name__)


class OnlineESPIDFExplorer:
    """Online ESP-IDF Documentation Explorer."""

    def __init__(self, config: ServerConfig):
        """Initialize the online explorer with configuration."""
        self.config = config
        self.base_url = config.base_url
        self.version = config.esp_idf_version
        self.chip_target = config.chip_target

        # Build versioned base URL with chip target
        if self.version == "latest":
            self.docs_url = f"{self.base_url}/en/latest/{self.chip_target}"
        else:
            self.docs_url = f"{self.base_url}/en/{self.version}/{self.chip_target}"

        # HTTP client with timeout and retries
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={"User-Agent": "ESP-IDF-MCP-Server/0.3.0 (Documentation Search Bot)"},
        )

        # Cache for fetched pages
        self._page_cache: dict[str, tuple[str, float]] = {}
        self._cache_ttl = 3600  # 1 hour cache

    async def search_docs(self, query: str, limit: int | None = None) -> dict[str, Any]:
        """Search ESP-IDF documentation online."""
        start_time = time.time()

        try:
            ValidationUtils.validate_query(query, self.config.max_query_length)
            effective_limit = min(limit or self.config.max_results, self.config.max_results)

            logger.info(f"Starting online search for: '{query}' (limit={effective_limit})")

            # Get search results from official site
            results = await self._search_official_docs(query, effective_limit)

            search_time = (time.time() - start_time) * 1000

            return {
                "query": query,
                "results": results,
                "metadata": {
                    "total_results": len(results),
                    "search_time_ms": round(search_time, 2),
                    "source": "esp-idf-online",
                    "version": self.version,
                    "base_url": self.docs_url,
                },
            }

        except Exception as e:
            logger.error(f"Online search failed: {e}")
            raise SearchError(f"Online search failed: {e}", query=query)

    async def _search_official_docs(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Search the official ESP-IDF documentation."""
        results: list[dict[str, Any]] = []

        # Common ESP-IDF documentation sections to search
        search_sections = [
            "",  # Main index
            "api-reference/",
            "api-guides/",
            "get-started/",
            "hw-reference/",
            "security/",
            "api-reference/system/",
            "api-reference/wifi/",
            "api-reference/bluetooth/",
            "api-reference/peripherals/",
            "api-reference/protocols/",
            "api-reference/storage/",
        ]

        # Search each section
        for section in search_sections:
            if len(results) >= limit:
                break

            try:
                section_url = urljoin(self.docs_url + "/", section)
                section_results = await self._search_section(
                    section_url, query, limit - len(results)
                )
                results.extend(section_results)

            except Exception as e:
                logger.warning(f"Failed to search section {section}: {e}")

        # Sort by relevance
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return results[:limit]

    async def _search_section(
        self, section_url: str, query: str, limit: int
    ) -> list[dict[str, Any]]:
        """Search a specific documentation section."""
        try:
            content = await self._fetch_page(section_url)
            soup = BeautifulSoup(content, "lxml")

            results: list[dict[str, Any]] = []
            query_lower = query.lower()

            # Find relevant links and content
            for link in soup.find_all("a", href=True):
                if len(results) >= limit:
                    break

                # Type check to ensure we have a Tag
                if not isinstance(link, Tag):
                    continue

                href_attr = link.get("href", "")
                href = str(href_attr) if href_attr else ""
                text = link.get_text(strip=True)

                # Skip non-documentation links
                if not href or href.startswith(("http://", "https://", "#", "mailto:")):
                    continue

                # Calculate relevance
                relevance_score = 0

                # Check link text
                if query_lower in text.lower():
                    relevance_score += 10

                # Check href
                if query_lower in href.lower():
                    relevance_score += 5

                if relevance_score > 0:
                    # Build full URL
                    full_url = urljoin(section_url, href)

                    # Get surrounding context
                    context = self._extract_context(link, query)

                    results.append(
                        {
                            "title": text or href,
                            "url": full_url,
                            "relevance_score": relevance_score,
                            "context": context,
                            "snippet": context,  # Add snippet field for compatibility
                            "section": self._get_section_name(section_url),
                        }
                    )

            # Also search page content
            content_matches = await self._search_page_content(soup, query, section_url)
            results.extend(content_matches[: limit - len(results)])

            return results

        except Exception as e:
            logger.warning(f"Failed to search section {section_url}: {e}")
            return []

    async def _search_page_content(
        self, soup: BeautifulSoup, query: str, page_url: str
    ) -> list[dict[str, Any]]:
        """Search within page content for query matches."""
        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        # Search in headings
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            if not isinstance(heading, Tag):
                continue

            heading_text = heading.get_text(strip=True)
            if query_lower in heading_text.lower():
                heading_id = heading.get("id", "")
                results.append(
                    {
                        "title": heading_text,
                        "url": page_url + f"#{heading_id if heading_id else ''}",
                        "relevance_score": 15,  # Higher score for headings
                        "context": heading_text,
                        "snippet": heading_text,  # Add snippet field for compatibility
                        "section": self._get_section_name(page_url),
                        "type": "heading",
                    }
                )

        # Search in paragraphs
        for para in soup.find_all("p"):
            para_text = para.get_text(strip=True)
            if query_lower in para_text.lower():
                # Extract context around match
                context = self._extract_text_context(para_text, query)
                results.append(
                    {
                        "title": f"Content match in {self._get_section_name(page_url)}",
                        "url": page_url,
                        "relevance_score": 8,
                        "context": context,
                        "snippet": context,  # Add snippet field for compatibility
                        "section": self._get_section_name(page_url),
                        "type": "content",
                    }
                )

        return results

    async def _fetch_page(self, url: str) -> str:
        """Fetch page content with caching."""
        # Check cache
        if url in self._page_cache:
            content, cached_time = self._page_cache[url]
            if time.time() - cached_time < self._cache_ttl:
                return content

        # Fetch from web
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            content = response.text

            # Cache the content
            self._page_cache[url] = (content, time.time())

            return content

        except httpx.HTTPError as e:
            raise DocumentNotFoundError(f"Failed to fetch {url}: {e}")

    def _extract_context(self, element: Tag, query: str) -> str:
        """Extract context around an element."""
        # Get parent context
        parent = element.parent
        if parent:
            context_text = parent.get_text(strip=True)
            return self._extract_text_context(context_text, query)
        return element.get_text(strip=True)

    def _extract_text_context(self, text: str, query: str, context_size: int = 150) -> str:
        """Extract context around query match in text."""
        text_lower = text.lower()
        query_lower = query.lower()

        match_index = text_lower.find(query_lower)
        if match_index == -1:
            return text[:context_size] + "..." if len(text) > context_size else text

        # Calculate context window
        start = max(0, match_index - context_size // 2)
        end = min(len(text), match_index + len(query) + context_size // 2)

        context = text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."

        return context

    def _get_section_name(self, url: str) -> str:
        """Extract section name from URL."""
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]

        if len(path_parts) >= 3:  # e.g., /projects/esp-idf/en/latest/api-reference/
            return path_parts[-1] if path_parts[-1] else path_parts[-2]

        return "documentation"

    async def read_doc(self, doc_url: str) -> dict[str, Any] | None:
        """Read a specific documentation page."""
        try:
            # Validate URL is from ESP-IDF docs
            if not doc_url.startswith(self.docs_url) and not doc_url.startswith("http"):
                # Assume relative URL
                doc_url = urljoin(self.docs_url + "/", doc_url)

            content = await self._fetch_page(doc_url)
            soup = BeautifulSoup(content, "lxml")

            # Extract main content
            main_content = soup.find("div", {"class": "document"}) or soup.find("main") or soup.body

            if main_content:
                # Clean and extract text
                text_content = main_content.get_text(separator="\n", strip=True)

                # Get title
                title_elem = soup.find("h1") or soup.find("title")
                title = title_elem.get_text(strip=True) if title_elem else "ESP-IDF Documentation"

                return {
                    "url": doc_url,
                    "title": title,
                    "content": text_content,
                    "content_length": len(text_content),
                    "section": self._get_section_name(doc_url),
                }

            return None

        except Exception as e:
            logger.error(f"Failed to read document {doc_url}: {e}")
            return None

    async def get_doc_structure(self) -> dict[str, Any]:
        """Get the structure of ESP-IDF documentation."""
        start_time = time.time()

        try:
            # Fetch main documentation index
            index_content = await self._fetch_page(self.docs_url)
            soup = BeautifulSoup(index_content, "lxml")

            sections: list[dict[str, str]] = []
            structure = {
                "sections": sections,
                "metadata": {
                    "version": self.version,
                    "base_url": self.docs_url,
                    "scan_time_ms": 0,
                },
            }

            # Find main navigation or table of contents
            nav_sections = soup.find_all(["nav", "div"], class_=re.compile(r"toc|navigation|menu"))

            for nav in nav_sections:
                if not isinstance(nav, Tag):
                    continue

                for link in nav.find_all("a", href=True):
                    if not isinstance(link, Tag):
                        continue

                    href_attr = link.get("href", "")
                    href = str(href_attr) if href_attr else ""
                    text = link.get_text(strip=True)

                    if href and text and not href.startswith(("http://", "https://", "#")):
                        full_url = urljoin(self.docs_url + "/", href)
                        sections.append(
                            {
                                "name": text,
                                "url": full_url,
                                "path": href,
                            }
                        )

            # If no navigation found, get from main content links
            if not structure["sections"]:
                for link in soup.find_all("a", href=True)[:20]:  # Limit to first 20
                    if not isinstance(link, Tag):
                        continue

                    href_attr = link.get("href", "")
                    href = str(href_attr) if href_attr else ""
                    text = link.get_text(strip=True)

                    if (
                        href
                        and text
                        and not href.startswith(("http://", "https://", "#", "mailto:"))
                    ):
                        full_url = urljoin(self.docs_url + "/", href)
                        sections.append(
                            {
                                "name": text,
                                "url": full_url,
                                "path": href,
                            }
                        )

            metadata = structure["metadata"]
            if isinstance(metadata, dict):
                metadata["scan_time_ms"] = round((time.time() - start_time) * 1000, 2)
                metadata["total_sections"] = len(sections)

            return structure

        except Exception as e:
            logger.error(f"Failed to get documentation structure: {e}")
            return {
                "sections": [],
                "metadata": {
                    "error": str(e),
                    "version": self.version,
                    "base_url": self.docs_url,
                },
            }

    async def find_api_references(self, component: str) -> dict[str, Any]:
        """Find API references for a specific component."""
        try:
            # Search in API reference section
            api_url = urljoin(self.docs_url + "/", "api-reference/")
            results = await self._search_section(api_url, component, self.config.max_results)

            return {
                "component": component,
                "results": results,
                "metadata": {
                    "total_results": len(results),
                    "search_url": api_url,
                    "version": self.version,
                },
            }

        except Exception as e:
            logger.error(f"Failed to find API references for {component}: {e}")
            return {"component": component, "results": [], "metadata": {"error": str(e)}}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

"""ESP-IDF Documentation Explorer with online search capabilities.

This module provides online documentation exploration functionality,
fetching content from the official ESP-IDF documentation website.
"""

import logging
from typing import Any

from .config import ServerConfig
from .web_explorer import OnlineESPIDFExplorer

logger = logging.getLogger(__name__)


class ESPIDFDocsExplorer:
    """ESP-IDF Documentation Explorer with online capabilities."""

    def __init__(self, config: ServerConfig):
        """Initialize the explorer with configuration."""
        self.config = config
        self.online_explorer = OnlineESPIDFExplorer(config)

    async def search_docs(
        self, query: str, limit: int | None = None, offset: int = 0
    ) -> dict[str, Any]:
        """Search ESP-IDF documentation online."""
        return await self.online_explorer.search_docs(query, limit)

    async def get_doc_structure(self) -> dict[str, Any]:
        """Get the structure of ESP-IDF documentation."""
        return await self.online_explorer.get_doc_structure()

    async def read_doc(self, file_path: str) -> dict[str, Any] | None:
        """Read a specific documentation page."""
        return await self.online_explorer.read_doc(file_path)

    async def find_api_references(self, component: str) -> dict[str, Any]:
        """Find API references for a specific component."""
        return await self.online_explorer.find_api_references(component)

    async def close(self):
        """Close resources."""
        await self.online_explorer.close()

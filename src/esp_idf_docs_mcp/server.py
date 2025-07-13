"""ESP-IDF Documentation Explorer MCP Server using FastMCP."""

import logging
from typing import Any

from fastmcp import FastMCP

from .config import get_config
from .explorer import ESPIDFDocsExplorer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

# Load configuration
config = get_config()

# Create FastMCP server
mcp: FastMCP = FastMCP(
    name="esp-idf-docs-explorer", dependencies=["httpx", "beautifulsoup4", "lxml"]
)

# Initialize explorer
explorer = ESPIDFDocsExplorer(config)


@mcp.tool()
async def search_docs(query: str) -> dict[str, Any]:
    """Search ESP-IDF documentation for keywords (case-insensitive).

    Args:
        query: Search query string

    Returns:
        Dictionary containing search results
    """
    return await explorer.search_docs(query)


@mcp.tool()
async def get_doc_structure() -> dict[str, Any]:
    """Get the directory structure of ESP-IDF documentation.

    Returns:
        Dictionary containing documentation structure
    """
    return await explorer.get_doc_structure()


@mcp.tool()
async def read_doc(file_path: str) -> dict[str, Any] | None:
    """Read the contents of a specific documentation file.

    Args:
        file_path: Relative path to the documentation file

    Returns:
        Dictionary containing document content
    """
    return await explorer.read_doc(file_path)


@mcp.tool()
async def find_api_references(component: str) -> dict[str, Any]:
    """Find API references for a specific ESP-IDF component.

    Args:
        component: Component or API name to search for

    Returns:
        Dictionary containing API references
    """
    return await explorer.find_api_references(component)


def main():
    """Run the MCP server with proper error handling."""
    try:
        logger.info(f"Starting {config.server_name} v{config.server_version}")
        logger.info(f"Documentation URL: {config.base_url}/{config.esp_idf_version}")
        logger.info(f"Server configuration: {len(config.to_dict())} settings loaded")

        mcp.run()

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        logger.error(f"Server crashed: {e}")
        raise


def run():
    """Entry point for the MCP server."""
    main()


if __name__ == "__main__":
    run()

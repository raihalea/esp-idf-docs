"""MCP Server handlers for ESP-IDF Documentation MCP Server.

This module contains all the request handlers for the MCP server,
separated for better organization and maintainability.
"""

import json
import logging
import time
from typing import Any

from mcp.types import (
    AnyUrl,
    Resource,
    ResourceTemplate,
    TextContent,
    TextResourceContents,
    Tool,
)

from .explorer import ESPIDFDocsExplorer

logger = logging.getLogger(__name__)


class MCPHandlers:
    """Centralized MCP request handlers."""

    def __init__(self, explorer: ESPIDFDocsExplorer):
        """Initialize handlers with explorer instance."""
        self.explorer = explorer

    async def list_tools(self) -> list[Tool]:
        """List available tools with detailed descriptions and examples."""
        tools = [
            Tool(
                name="search_docs",
                description="""Search ESP-IDF documentation with advanced features.

Features:
- Case-insensitive search with relevance scoring
- Context extraction with highlighted matches
- Pagination support (limit/offset)
- Fuzzy search and query expansion
- Performance metrics included in response

Example usage:
- search_docs({"query": "wifi station mode"})
- search_docs({"query": "gpio", "limit": 5, "offset": 0})

Returns: Enhanced response with results, metadata, and performance info.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (case-insensitive, max 100 chars)",
                            "minLength": 1,
                            "maxLength": 100,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 20, max: 50)",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 20,
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Number of results to skip for pagination (default: 0)",
                            "minimum": 0,
                            "default": 0,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_doc_structure",
                description="""Get the hierarchical structure of ESP-IDF documentation.

Returns:
- Directory tree with file counts and sizes
- File listings with metadata (size, type, modification time)
- Summary statistics (total files, directories, size)
- Performance metrics

Example: get_doc_structure({})

Useful for understanding documentation organization and finding relevant sections.""",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="read_doc",
                description="""Read the complete contents of a specific documentation file.

Features:
- File validation and security checks
- Size limits to prevent memory issues
- Enhanced metadata extraction (size, line count, word count, hash)
- Document analysis (if enabled)
- Support for multiple file formats

Example usage:
- read_doc({"file_path": "api-reference/wifi/esp_wifi.rst"})
- read_doc({"file_path": "get-started/index.md"})

Security: Only allows relative paths within the docs directory.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative path to documentation file",
                            "pattern": "^[^/\\\\].+\\.(rst|md|txt)$",
                        }
                    },
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="find_api_references",
                description="""Find comprehensive API references for ESP-IDF components.

Searches for:
- Doxygen directives (functions, structs, enums, defines)
- Code references and examples
- Heading references
- Related function families

Features:
- Multiple pattern matching for complete coverage
- Line number and context information
- Match type classification
- Enhanced search patterns
- Performance metrics

Example usage:
- find_api_references({"component": "esp_wifi"})
- find_api_references({"component": "gpio"})

Returns: Detailed matches with context and metadata.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component": {
                            "type": "string",
                            "description": "ESP-IDF component or API name to search for",
                            "minLength": 1,
                            "maxLength": 50,
                        }
                    },
                    "required": ["component"],
                },
            ),
        ]

        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls with comprehensive error handling."""
        operation_start = time.time()

        try:
            logger.info(f"Tool called: {name} with arguments: {arguments}")

            if name == "search_docs":
                return await self._handle_search_docs(arguments)
            elif name == "get_doc_structure":
                return await self._handle_get_doc_structure()
            elif name == "read_doc":
                return await self._handle_read_doc(arguments)
            elif name == "find_api_references":
                return await self._handle_find_api_references(arguments)
            else:
                return self._handle_unknown_tool(name)

        except ValueError as e:
            return self._handle_validation_error(e, name, arguments)
        except Exception as e:
            return self._handle_internal_error(e, name, operation_start)

    async def _handle_search_docs(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle search_docs tool call."""
        query = arguments["query"]
        limit = arguments.get("limit")
        offset = arguments.get("offset", 0)

        response = await self.explorer.search_docs(query, limit, offset)

        return [TextContent(type="text", text=json.dumps(response, indent=2, ensure_ascii=False))]

    async def _handle_get_doc_structure(self) -> list[TextContent]:
        """Handle get_doc_structure tool call."""
        structure = await self.explorer.get_doc_structure()

        return [TextContent(type="text", text=json.dumps(structure, indent=2, ensure_ascii=False))]

    async def _handle_read_doc(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle read_doc tool call."""
        file_path = arguments["file_path"]
        result = await self.explorer.read_doc(file_path)

        if result:
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        else:
            error_msg = f"Could not read file: {file_path}"
            logger.warning(error_msg)
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": error_msg, "file_path": file_path}, indent=2),
                )
            ]

    async def _handle_find_api_references(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle find_api_references tool call."""
        component = arguments["component"]
        result = await self.explorer.find_api_references(component)

        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    def _handle_unknown_tool(self, name: str) -> list[TextContent]:
        """Handle unknown tool error."""
        error_msg = f"Unknown tool: {name}"
        logger.error(error_msg)

        available_tools = ["search_docs", "get_doc_structure", "read_doc", "find_api_references"]

        return [
            TextContent(
                type="text",
                text=json.dumps({"error": error_msg, "available_tools": available_tools}, indent=2),
            )
        ]

    def _handle_validation_error(
        self, error: ValueError, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle validation error."""
        error_msg = f"Invalid input: {error!s}"
        logger.warning(error_msg)

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"error": error_msg, "tool": name, "arguments": arguments}, indent=2
                ),
            )
        ]

    def _handle_internal_error(
        self, error: Exception, name: str, operation_start: float
    ) -> list[TextContent]:
        """Handle internal server error."""
        operation_time = (time.time() - operation_start) * 1000
        error_msg = f"Internal error: {error!s}"
        logger.error(f"Tool {name} failed after {operation_time:.2f}ms: {error}")

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": error_msg,
                        "tool": name,
                        "operation_time_ms": round(operation_time, 2),
                    },
                    indent=2,
                ),
            )
        ]

    async def list_resources(self) -> list[Resource]:
        """List available resources."""
        return [
            Resource(
                uri=AnyUrl("docs://structure"),
                name="ESP-IDF Documentation Structure",
                description="Complete overview of the ESP-IDF documentation structure with enhanced metadata",
                mimeType="application/json",
            )
        ]

    async def list_resource_templates(self) -> list[ResourceTemplate]:
        """List resource templates."""
        return [
            ResourceTemplate(
                uriTemplate="docs://file/{path}",
                name="Documentation File",
                description="Read a specific ESP-IDF documentation file with enhanced metadata",
                mimeType="text/plain",
            )
        ]

    async def read_resource(self, uri: str) -> TextResourceContents:
        """Read a resource with enhanced error handling."""
        try:
            logger.debug(f"Reading resource: {uri}")

            if uri == "docs://structure":
                structure = await self.explorer.get_doc_structure()
                return TextResourceContents(
                    uri=AnyUrl(uri),
                    mimeType="application/json",
                    text=json.dumps(structure, indent=2, ensure_ascii=False),
                )

            elif uri.startswith("docs://file/"):
                file_path = uri[len("docs://file/") :]
                result = await self.explorer.read_doc(file_path)

                if result:
                    return TextResourceContents(
                        uri=AnyUrl(uri), mimeType="text/plain", text=result["content"]
                    )

            raise ValueError(f"Unknown resource: {uri}")

        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            raise

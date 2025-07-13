import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
    TextResourceContents,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("esp-idf-docs-explorer")


class ESPIDFDocsExplorer:
    """ESP-IDF Documentation Explorer."""
    
    def __init__(self, docs_path: Optional[Path] = None):
        self.docs_path = docs_path or Path.cwd()
        self._cache: Dict[str, Any] = {}
    
    def search_docs(self, query: str) -> List[Dict[str, Any]]:
        """Search ESP-IDF documentation for a given query."""
        results = []
        
        # Search for .rst and .md files
        for pattern in ["**/*.rst", "**/*.md"]:
            for file_path in self.docs_path.rglob(pattern):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if query.lower() in content.lower():
                        # Extract context around the match
                        lines = content.split('\n')
                        matches = []
                        
                        for i, line in enumerate(lines):
                            if query.lower() in line.lower():
                                start = max(0, i - 2)
                                end = min(len(lines), i + 3)
                                context = '\n'.join(lines[start:end])
                                matches.append({
                                    'line': i + 1,
                                    'context': context
                                })
                        
                        if matches:
                            results.append({
                                'file': str(file_path.relative_to(self.docs_path)),
                                'matches': matches[:3]  # Limit to first 3 matches
                            })
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
        
        return results[:10]  # Limit total results
    
    def get_doc_structure(self) -> Dict[str, Any]:
        """Get the structure of ESP-IDF documentation."""
        structure = {
            'directories': {},
            'files': []
        }
        
        # Find all documentation directories
        for item in self.docs_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                doc_files = list(item.rglob("*.rst")) + list(item.rglob("*.md"))
                if doc_files:
                    structure['directories'][item.name] = len(doc_files)
            elif item.suffix in ['.rst', '.md']:
                structure['files'].append(item.name)
        
        return structure
    
    def read_doc(self, file_path: str) -> Optional[str]:
        """Read a specific documentation file."""
        try:
            full_path = self.docs_path / file_path
            if full_path.exists() and full_path.suffix in ['.rst', '.md']:
                return full_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
        return None
    
    def find_api_references(self, component: str) -> List[Dict[str, Any]]:
        """Find API references for a specific ESP-IDF component."""
        results = []
        api_patterns = [
            rf".. doxygenfunction::\s+{component}",
            rf".. doxygenstruct::\s+{component}",
            rf".. doxygenenum::\s+{component}",
            rf"`{component}`",
            rf"## {component}",
            rf"### {component}",
        ]
        
        for pattern in ["**/*.rst", "**/*.md"]:
            for file_path in self.docs_path.rglob(pattern):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    for api_pattern in api_patterns:
                        if re.search(api_pattern, content, re.IGNORECASE):
                            results.append({
                                'file': str(file_path.relative_to(self.docs_path)),
                                'type': 'api_reference'
                            })
                            break
                except Exception:
                    pass
        
        return results


# ドキュメントパスを環境変数から取得
docs_path = os.getenv('ESP_IDF_DOCS_PATH', str(Path.cwd()))
explorer = ESPIDFDocsExplorer(Path(docs_path))


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_docs",
            description="Search ESP-IDF documentation for a specific query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (case-insensitive)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_doc_structure",
            description="Get the structure of ESP-IDF documentation",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="read_doc",
            description="Read a specific documentation file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative path to the documentation file"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="find_api_references",
            description="Find API references for a specific ESP-IDF component",
            inputSchema={
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "Component or API name to search for"
                    }
                },
                "required": ["component"]
            }
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "search_docs":
            results = explorer.search_docs(arguments["query"])
            return [TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )]
        
        elif name == "get_doc_structure":
            structure = explorer.get_doc_structure()
            return [TextContent(
                type="text",
                text=json.dumps(structure, indent=2)
            )]
        
        elif name == "read_doc":
            content = explorer.read_doc(arguments["file_path"])
            if content:
                return [TextContent(
                    type="text",
                    text=content
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Error: Could not read file {arguments['file_path']}"
                )]
        
        elif name == "find_api_references":
            results = explorer.find_api_references(arguments["component"])
            return [TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )]
        
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="docs://structure",
            name="ESP-IDF Documentation Structure",
            description="Overview of the ESP-IDF documentation structure",
            mimeType="application/json"
        )
    ]


@server.list_resource_templates()
async def handle_list_resource_templates() -> List[ResourceTemplate]:
    """List resource templates."""
    return [
        ResourceTemplate(
            uriTemplate="docs://file/{path}",
            name="Documentation File",
            description="Read a specific ESP-IDF documentation file",
            mimeType="text/plain"
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> TextResourceContents:
    """Read a resource."""
    if uri == "docs://structure":
        structure = explorer.get_doc_structure()
        return TextResourceContents(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(structure, indent=2)
        )
    
    elif uri.startswith("docs://file/"):
        file_path = uri[len("docs://file/"):]
        content = explorer.read_doc(file_path)
        if content:
            return TextResourceContents(
                uri=uri,
                mimeType="text/plain",
                text=content
            )
    
    raise ValueError(f"Unknown resource: {uri}")


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="esp-idf-docs-explorer",
                server_version="0.1.0"
            )
        )


def run():
    """Entry point for uvx."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
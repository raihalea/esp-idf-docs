"""Refactored ESP-IDF Documentation MCP Server.

This is the main server module with improved organization,
better separation of concerns, and enhanced maintainability.
"""

import asyncio
import logging

from mcp.server import Server
from mcp.server.models import InitializationOptions

from .config import get_config
from .exceptions import ConfigurationError
from .explorer import ESPIDFDocsExplorer
from .handlers import MCPHandlers

# Initialize configuration and logging
try:
    config = get_config()

    logging.basicConfig(level=getattr(logging, config.log_level), format=config.log_format)
    logger = logging.getLogger(__name__)

except Exception as e:
    # Fallback logging configuration
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to load configuration: {e}")
    raise ConfigurationError(f"Configuration initialization failed: {e}")

# Initialize server
server = Server(config.server_name)

# Initialize explorer and handlers
try:
    explorer = ESPIDFDocsExplorer(config)
    handlers = MCPHandlers(explorer)

    logger.info(f"Initialized {config.server_name} v{config.server_version}")

except Exception as e:
    logger.error(f"Failed to initialize server components: {e}")
    raise ConfigurationError(f"Server initialization failed: {e}")


@server.list_tools()
async def handle_list_tools():
    """Handle list_tools request."""
    try:
        return await handlers.list_tools()
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Handle call_tool request."""
    try:
        return await handlers.call_tool(name, arguments)
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        raise


@server.list_resources()
async def handle_list_resources():
    """Handle list_resources request."""
    try:
        return await handlers.list_resources()
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        raise


@server.list_resource_templates()
async def handle_list_resource_templates():
    """Handle list_resource_templates request."""
    try:
        return await handlers.list_resource_templates()
    except Exception as e:
        logger.error(f"Error listing resource templates: {e}")
        raise


@server.read_resource()
async def handle_read_resource(uri: str):
    """Handle read_resource request."""
    try:
        return await handlers.read_resource(uri)
    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}")
        raise


async def main():
    """Run the MCP server with proper error handling."""
    try:
        logger.info(f"Starting {config.server_name} v{config.server_version}")
        logger.info(f"Documentation path: {config.docs_path}")
        logger.info(f"Server configuration: {len(config.to_dict())} settings loaded")

        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=config.server_name, server_version=config.server_version
                ),
            )

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        raise


def run():
    """Entry point for uvx and direct execution."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server crashed: {e}")
        raise


if __name__ == "__main__":
    run()

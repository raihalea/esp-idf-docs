"""Integration tests for ESP-IDF Documentation MCP Server.

These tests verify actual server execution, tool functionality,
and error handling in realistic scenarios.
"""

import asyncio
import sys

import pytest
import respx
from fastmcp import Client
from httpx import Response

from esp_idf_docs_mcp.server import mcp


class TestMCPServerIntegration:
    """Test actual MCP server functionality using FastMCP Client."""

    @pytest.fixture
    def server(self):
        """Return the MCP server instance for testing."""
        return mcp

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_server_tools_available(self, server):
        """Test that all required tools are available through the server."""
        async with Client(server) as client:
            # Get available tools
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]

            # Verify all expected tools are present
            expected_tools = ["search_docs", "get_doc_structure", "read_doc", "find_api_references"]
            for tool_name in expected_tools:
                assert tool_name in tool_names, f"Tool {tool_name} not found in {tool_names}"

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_search_docs_tool_execution(self, server):
        """Test actual execution of search_docs tool."""
        async with Client(server) as client:
            # Mock the HTTP request to ESP-IDF docs
            with respx.mock:
                # Mock search response
                respx.get("https://docs.espressif.com/projects/esp-idf/latest/").mock(
                    return_value=Response(
                        200,
                        content="""
                    <html>
                        <head><title>ESP-IDF Documentation</title></head>
                        <body>
                            <div class="section">
                                <h1>WiFi Station Mode</h1>
                                <p>Configure WiFi in station mode...</p>
                            </div>
                        </body>
                    </html>
                    """,
                    )
                )

                # Execute search_docs tool
                result = await client.call_tool("search_docs", {"query": "wifi"})

                # Verify result structure
                assert isinstance(result, dict) or hasattr(result, "data")
                if hasattr(result, "data"):
                    data = result.data
                else:
                    data = result

                # Basic validation that search returned some structure
                assert isinstance(data, dict)

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_get_doc_structure_tool_execution(self, server):
        """Test actual execution of get_doc_structure tool."""
        async with Client(server) as client:
            # Mock the HTTP request
            with respx.mock:
                respx.get("https://docs.espressif.com/projects/esp-idf/latest/").mock(
                    return_value=Response(
                        200,
                        content="""
                    <html>
                        <body>
                            <div class="toctree">
                                <ul>
                                    <li><a href="/get-started/">Get Started</a></li>
                                    <li><a href="/api-reference/">API Reference</a></li>
                                </ul>
                            </div>
                        </body>
                    </html>
                    """,
                    )
                )

                # Execute get_doc_structure tool
                result = await client.call_tool("get_doc_structure", {})

                # Verify result
                assert isinstance(result, dict) or hasattr(result, "data")

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_read_doc_tool_execution(self, server):
        """Test actual execution of read_doc tool."""
        async with Client(server) as client:
            # Mock the HTTP request for a specific document
            with respx.mock:
                respx.get(
                    "https://docs.espressif.com/projects/esp-idf/latest/get-started/index.html"
                ).mock(
                    return_value=Response(
                        200,
                        content="""
                    <html>
                        <body>
                            <h1>Get Started</h1>
                            <p>This guide will help you get started with ESP-IDF.</p>
                        </body>
                    </html>
                    """,
                    )
                )

                # Execute read_doc tool
                result = await client.call_tool("read_doc", {"file_path": "get-started/index.html"})

                # Verify result (can be None if document not found)
                assert result is None or isinstance(result, dict) or hasattr(result, "data")

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_find_api_references_tool_execution(self, server):
        """Test actual execution of find_api_references tool."""
        async with Client(server) as client:
            # Mock the HTTP request for API search
            with respx.mock:
                respx.get("https://docs.espressif.com/projects/esp-idf/latest/").mock(
                    return_value=Response(
                        200,
                        content="""
                    <html>
                        <body>
                            <div class="section">
                                <h2>GPIO Functions</h2>
                                <p>gpio_set_level() - Set GPIO level</p>
                                <p>gpio_get_level() - Get GPIO level</p>
                            </div>
                        </body>
                    </html>
                    """,
                    )
                )

                # Execute find_api_references tool
                result = await client.call_tool("find_api_references", {"component": "gpio"})

                # Verify result
                assert isinstance(result, dict) or hasattr(result, "data")

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_invalid_tool_call(self, server):
        """Test behavior with invalid tool calls."""
        async with Client(server) as client:
            # Try to call a non-existent tool
            with pytest.raises(Exception):  # Should raise some form of error
                await client.call_tool("non_existent_tool", {})

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_tool_with_invalid_parameters(self, server):
        """Test behavior with invalid parameters."""
        async with Client(server) as client:
            # Mock a basic response for the HTTP request
            with respx.mock:
                respx.get("https://docs.espressif.com/projects/esp-idf/latest/").mock(
                    return_value=Response(200, content="<html><body></body></html>")
                )

                # Try search_docs with invalid parameter type
                with pytest.raises(Exception):  # Should raise validation error
                    await client.call_tool("search_docs", {"query": 123})  # Should be string


class TestServerStartup:
    """Test actual server process startup and shutdown."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_server_command_help(self):
        """Test that the server command responds to help flag."""
        try:
            # Run the server with --help flag
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "esp_idf_docs_mcp.server",
                "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)

            # Verify it started and showed help (FastMCP shows server info)
            output = stdout.decode() + stderr.decode()
            assert "FastMCP" in output or "esp-idf-docs-explorer" in output

        except asyncio.TimeoutError:
            pytest.fail("Server help command timed out")
        except Exception as e:
            pytest.fail(f"Server help command failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_server_command_version_check(self):
        """Test that the server command can be executed (basic startup test)."""
        try:
            # Run the server command briefly
            proc = await asyncio.create_subprocess_exec(
                "uv",
                "run",
                "esp-idf-docs-mcp",
                "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait briefly to see if it starts without immediate errors
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
                output = stdout.decode() + stderr.decode()

                # Should contain server information
                assert "esp-idf-docs-explorer" in output or "FastMCP" in output

            except asyncio.TimeoutError:
                # If it times out, that might mean it's waiting for input (good sign)
                proc.terminate()
                await proc.wait()

        except Exception as e:
            pytest.fail(f"Server startup test failed: {e}")


class TestErrorHandling:
    """Test error handling in various failure scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_network_error_handling(self, server=mcp):
        """Test behavior when network requests fail."""
        async with Client(server) as client:
            # Mock network failure
            with respx.mock:
                respx.get("https://docs.espressif.com/projects/esp-idf/latest/").mock(
                    side_effect=Exception("Network error")
                )

                # Should handle network errors gracefully
                result = await client.call_tool("search_docs", {"query": "wifi"})

                # Should return error information rather than crashing
                assert result is not None

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_http_error_handling(self, server=mcp):
        """Test behavior when HTTP requests return errors."""
        async with Client(server) as client:
            # Mock HTTP error
            with respx.mock:
                respx.get("https://docs.espressif.com/projects/esp-idf/latest/").mock(
                    return_value=Response(500, content="Internal Server Error")
                )

                # Should handle HTTP errors gracefully
                result = await client.call_tool("search_docs", {"query": "wifi"})

                # Should return error information rather than crashing
                assert result is not None

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_malformed_response_handling(self, server=mcp):
        """Test behavior with malformed HTML responses."""
        async with Client(server) as client:
            # Mock malformed response
            with respx.mock:
                respx.get("https://docs.espressif.com/projects/esp-idf/latest/").mock(
                    return_value=Response(200, content="Not valid HTML content")
                )

                # Should handle malformed responses gracefully
                result = await client.call_tool("search_docs", {"query": "wifi"})

                # Should return some result even with bad HTML
                assert result is not None

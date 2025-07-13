"""Tests for FastMCP server implementation."""

import pytest


def test_server_module_import():
    """Test that server module can be imported."""
    from esp_idf_docs_mcp.server import main, mcp, run

    assert mcp is not None
    assert callable(main)
    assert callable(run)


def test_fastmcp_instance():
    """Test that FastMCP instance is properly configured."""
    from esp_idf_docs_mcp.server import mcp

    assert mcp.name == "esp-idf-docs-explorer"
    assert "httpx" in mcp.dependencies
    assert "beautifulsoup4" in mcp.dependencies
    assert "lxml" in mcp.dependencies


def test_tools_are_defined():
    """Test that tool functions are properly defined."""
    from esp_idf_docs_mcp.server import (
        find_api_references,
        get_doc_structure,
        read_doc,
        search_docs,
    )

    # All tools should exist and have names
    assert search_docs.name == "search_docs"
    assert get_doc_structure.name == "get_doc_structure"
    assert read_doc.name == "read_doc"
    assert find_api_references.name == "find_api_references"


def test_tools_have_descriptions():
    """Test that tools have proper descriptions."""
    from esp_idf_docs_mcp.server import (
        find_api_references,
        get_doc_structure,
        read_doc,
        search_docs,
    )

    # All tools should have descriptions
    assert search_docs.description and len(search_docs.description) > 0
    assert get_doc_structure.description and len(get_doc_structure.description) > 0
    assert read_doc.description and len(read_doc.description) > 0
    assert find_api_references.description and len(find_api_references.description) > 0


def test_config_loaded():
    """Test that configuration is properly loaded."""
    from esp_idf_docs_mcp.server import config

    assert config is not None
    assert hasattr(config, "server_name")
    assert hasattr(config, "server_version")
    assert hasattr(config, "base_url")
    assert hasattr(config, "esp_idf_version")


def test_explorer_initialized():
    """Test that explorer is properly initialized."""
    from esp_idf_docs_mcp.server import explorer

    assert explorer is not None
    assert hasattr(explorer, "search_docs")
    assert hasattr(explorer, "get_doc_structure")
    assert hasattr(explorer, "read_doc")
    assert hasattr(explorer, "find_api_references")


def test_logging_configured():
    """Test that logging is properly configured."""
    import logging

    # Check that logging is configured
    logger = logging.getLogger("esp_idf_docs_mcp.server")
    assert logger is not None
    assert logger.level <= logging.INFO


def test_server_can_start():
    """Test that the server initialization doesn't fail."""
    # This tests the module loading without actually starting the server
    try:
        from esp_idf_docs_mcp.server import config, explorer, mcp

        # Basic validation that everything is set up
        assert mcp is not None
        assert config is not None
        assert explorer is not None

    except Exception as e:
        pytest.fail(f"Server initialization failed: {e}")

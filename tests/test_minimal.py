"""Minimal tests for ESP-IDF Documentation MCP Server."""


def test_config_import_and_creation():
    """Test that config module can be imported and ServerConfig created."""
    from esp_idf_docs_mcp.config import ServerConfig

    config = ServerConfig()
    assert config is not None
    assert hasattr(config, "server_name")


def test_exceptions_import():
    """Test that exceptions module can be imported."""
    from esp_idf_docs_mcp.exceptions import (
        DocumentNotFoundError,
        ESPIDFDocsError,
        InvalidPathError,
        ProcessingError,
    )

    # Test exception hierarchy
    assert issubclass(DocumentNotFoundError, ESPIDFDocsError)
    assert issubclass(InvalidPathError, ESPIDFDocsError)
    assert issubclass(ProcessingError, ESPIDFDocsError)


def test_util_import():
    """Test that util module can be imported."""
    from esp_idf_docs_mcp.util import FileCache, TextProcessor, ValidationUtils

    processor = TextProcessor()
    cache = FileCache()
    validator = ValidationUtils()

    assert processor is not None
    assert cache is not None
    assert validator is not None


def test_text_processor_basic():
    """Test basic TextProcessor functionality."""
    from esp_idf_docs_mcp.util import TextProcessor

    processor = TextProcessor()

    # Test RST cleaning
    rst_text = ".. note::\n   Test\n\nContent here"
    cleaned = processor.clean_rst_content(rst_text)
    assert isinstance(cleaned, str)
    assert "Content here" in cleaned

    # Test Markdown cleaning
    md_text = "# Title\n\nContent here"
    cleaned_md = processor.clean_markdown_content(md_text)
    assert isinstance(cleaned_md, str)
    assert "Title" in cleaned_md


def test_file_cache_basic():
    """Test basic FileCache functionality."""
    from esp_idf_docs_mcp.util import FileCache

    cache = FileCache()

    # Test basic cache operations
    assert cache.get("nonexistent") is None

    # Test that cache has expected methods
    assert hasattr(cache, "get")


def test_validation_utils_basic():
    """Test basic ValidationUtils functionality."""
    from esp_idf_docs_mcp.util import ValidationUtils

    validator = ValidationUtils()

    # Test that validator has expected methods
    assert hasattr(validator, "validate_query")
    assert hasattr(validator, "is_safe_path")


def test_package_structure():
    """Test that package has expected structure."""
    import esp_idf_docs_mcp

    # Test that main package can be imported
    assert esp_idf_docs_mcp is not None

    # Test that submodules exist
    import esp_idf_docs_mcp.config
    import esp_idf_docs_mcp.exceptions
    import esp_idf_docs_mcp.explorer
    import esp_idf_docs_mcp.handlers
    import esp_idf_docs_mcp.recommendations
    import esp_idf_docs_mcp.util

    assert True  # If we reach here, all imports succeeded

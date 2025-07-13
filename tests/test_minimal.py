"""Minimal tests for ESP-IDF Documentation MCP Server."""


def test_config_import_and_creation():
    """Test that config module can be imported and ServerConfig created."""
    from esp_idf_docs_mcp.config import ServerConfig

    config = ServerConfig()
    assert config is not None
    assert hasattr(config, "server_name")
    assert hasattr(config, "base_url")
    assert hasattr(config, "esp_idf_version")
    assert config.base_url == "https://docs.espressif.com/projects/esp-idf"
    assert config.esp_idf_version == "latest"


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
    from esp_idf_docs_mcp.util import TextProcessor, ValidationUtils

    # Test that classes exist
    assert TextProcessor is not None
    assert ValidationUtils is not None


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


def test_text_processor_static():
    """Test TextProcessor static methods."""
    from esp_idf_docs_mcp.util import TextProcessor

    # Test normalize_text
    result = TextProcessor.normalize_text("Hello World!")
    assert result == "hello world"

    # Test extract_headings
    md_text = "# Heading 1\n## Heading 2"
    headings = TextProcessor.extract_headings(md_text)
    assert len(headings) >= 2


def test_validation_utils_basic():
    """Test basic ValidationUtils functionality."""
    from esp_idf_docs_mcp.util import ValidationUtils

    # Test that methods exist (static methods)
    assert hasattr(ValidationUtils, "validate_query")
    assert hasattr(ValidationUtils, "detect_encoding")
    assert hasattr(ValidationUtils, "sanitize_filename")

    # Test validate_query
    try:
        ValidationUtils.validate_query("wifi")
    except Exception:
        assert False, "Valid query should not raise exception"


def test_package_structure():
    """Test that package has expected structure."""
    import esp_idf_docs_mcp

    # Test that main package can be imported
    assert esp_idf_docs_mcp is not None

    # Test that submodules exist
    import esp_idf_docs_mcp.config
    import esp_idf_docs_mcp.exceptions
    import esp_idf_docs_mcp.explorer
    import esp_idf_docs_mcp.util
    import esp_idf_docs_mcp.web_explorer

    assert True  # If we reach here, all imports succeeded

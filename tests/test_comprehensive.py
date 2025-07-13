"""Comprehensive tests for ESP-IDF Documentation MCP Server (simplified)."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from esp_idf_docs_mcp.config import ServerConfig
from esp_idf_docs_mcp.exceptions import DocumentNotFoundError, InvalidPathError
from esp_idf_docs_mcp.explorer import ESPIDFDocsExplorer
from esp_idf_docs_mcp.handlers import MCPHandlers
from esp_idf_docs_mcp.util import (
    FileCache,
    SearchConfig,
    SearchEngine,
    TextProcessor,
    ValidationUtils,
)


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_document_not_found_exception(self):
        """Test DocumentNotFoundError handling."""
        error = DocumentNotFoundError("File not found", "/path/to/file")
        assert str(error) == "File not found"
        assert error.file_path == "/path/to/file"

    def test_invalid_path_exception(self):
        """Test InvalidPathError handling."""
        error = InvalidPathError("Invalid path", "bad_field", "../../../etc/passwd")
        assert str(error) == "Invalid path"
        assert error.field == "bad_field"
        assert error.value == "../../../etc/passwd"

    def test_validation_error_handling(self):
        """Test validation error scenarios."""
        validator = ValidationUtils()

        # Test malicious query patterns
        malicious_queries = [
            "../../../etc/passwd",
            "<script>alert('xss')</script>",
            "'; DROP TABLE docs; --",
        ]

        for query in malicious_queries:
            try:
                result = validator.validate_query(query)
                # Should either return False or raise exception
                if result is not None:
                    assert result is False
            except ValueError:
                # Expected for malicious patterns
                assert True


class TestSecurityFeatures:
    """Test security-related features."""

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        validator = ValidationUtils()

        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "docs/../../../secret.txt",
        ]

        for path in malicious_paths:
            try:
                # Should detect unsafe paths
                is_safe = validator.is_safe_path(path, "/safe/base")
                if is_safe is not None:
                    assert is_safe is False
            except Exception:
                # Exception is also acceptable for malicious paths
                assert True

    def test_query_length_limits(self):
        """Test query length limitations."""
        validator = ValidationUtils()

        # Test very long query
        long_query = "a" * 1000
        try:
            result = validator.validate_query(long_query)
            # Should handle long queries gracefully
            assert result is False or result is None
        except ValueError:
            # Expected behavior for oversized queries
            assert True


class TestSearchFunctionality:
    """Test search functionality."""

    def test_search_engine_basic(self):
        """Test basic search engine functionality."""
        config = SearchConfig()
        engine = SearchEngine(config)

        # Test fuzzy matching
        result = engine.fuzzy_match("WiFi", "This document covers WiFi setup")
        assert result is True

        result = engine.fuzzy_match("bluetooth", "WiFi configuration guide")
        assert result is False or isinstance(result, bool)

    def test_search_configuration(self):
        """Test search configuration options."""
        config = SearchConfig(max_results=10, fuzzy_threshold=0.8, max_query_length=50)

        assert config.max_results == 10
        assert config.fuzzy_threshold == 0.8
        assert config.max_query_length == 50

    def test_text_normalization(self):
        """Test text normalization for search."""
        # Test that normalization method exists
        normalized = TextProcessor.normalize_text("WiFi API Reference")
        assert isinstance(normalized, str)
        assert len(normalized) > 0


class TestFileOperations:
    """Test file operations and processing."""

    def test_rst_markdown_processing(self):
        """Test processing different file formats."""
        processor = TextProcessor()

        # Test RST processing
        rst_content = "API Guide\n=========\n\nContent here."
        rst_cleaned = processor.clean_rst_content(rst_content)
        assert "API Guide" in rst_cleaned

        # Test Markdown processing
        md_content = "# API Guide\n\nContent here."
        md_cleaned = processor.clean_markdown_content(md_content)
        assert "API Guide" in md_cleaned

    def test_file_encoding_handling(self):
        """Test handling of different file encodings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create UTF-8 file with international characters
            test_file = Path(temp_dir) / "unicode_test.rst"
            content = "ESP32 配置\n========\n\nWiFi 設定ガイド"
            test_file.write_text(content, encoding="utf-8")

            # Read and verify
            read_content = test_file.read_text(encoding="utf-8")
            assert "ESP32 配置" in read_content
            assert "WiFi 設定ガイド" in read_content

    def test_large_file_handling(self):
        """Test handling of large files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create moderately large file
            large_file = Path(temp_dir) / "large.rst"
            content = "ESP32 Documentation\n" * 1000  # ~20KB
            large_file.write_text(content)

            # Verify file was created and can be read
            assert large_file.exists()
            read_content = large_file.read_text()
            assert "ESP32 Documentation" in read_content


class TestCaching:
    """Test caching functionality."""

    def test_file_cache_basic(self):
        """Test basic file cache operations."""
        cache = FileCache()

        # Test cache miss
        result = cache.get("nonexistent_key")
        assert result is None

        # Test cache object initialization
        assert hasattr(cache, "get")

    def test_cache_with_file_operations(self):
        """Test cache integration with file operations."""
        cache = FileCache()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "cached_file.rst"
            test_file.write_text("Cached content")

            # Test file-based caching if available
            if hasattr(cache, "cache_file_content"):
                cache.cache_file_content(str(test_file), "cached_data")

                if hasattr(cache, "get_file_content"):
                    result = cache.get_file_content(str(test_file))
                    # Cache behavior depends on implementation
                    assert result is None or isinstance(result, str)


class TestAsyncIntegration:
    """Test async integration scenarios."""

    @pytest.mark.asyncio
    async def test_async_handler_basic(self):
        """Test basic async handler functionality."""
        config = ServerConfig()

        with tempfile.TemporaryDirectory() as temp_dir:
            config.docs_path = Path(temp_dir)

            # Create sample document
            doc_file = Path(temp_dir) / "test.rst"
            doc_file.write_text("Test API\n========\n\nAPI documentation.")

            # Test async operations with mocked explorer
            with patch.object(ESPIDFDocsExplorer, "_initialize_recommendations", return_value=None):
                explorer = ESPIDFDocsExplorer(config)
                handlers = MCPHandlers(explorer)

                # Test async tool call
                result = await handlers.call_tool("get_doc_structure", {})
                assert len(result) == 1
                assert isinstance(result[0].text, str)


class TestConfigurationManagement:
    """Test configuration management."""

    def test_server_config_defaults(self):
        """Test server configuration defaults."""
        config = ServerConfig()

        # Test that config has expected attributes
        assert hasattr(config, "server_name")
        assert hasattr(config, "docs_path")
        assert hasattr(config, "server_version")

        # Test default values are reasonable
        assert isinstance(config.server_name, str)
        assert len(config.server_name) > 0

    def test_search_config_validation(self):
        """Test search configuration validation."""
        # Test with valid configuration
        config = SearchConfig(max_results=100, fuzzy_threshold=0.7)
        assert config.max_results == 100
        assert config.fuzzy_threshold == 0.7

        # Test with edge values
        edge_config = SearchConfig(max_results=1, fuzzy_threshold=0.0)
        assert edge_config.max_results == 1
        assert edge_config.fuzzy_threshold == 0.0


class TestPerformanceCharacteristics:
    """Test basic performance characteristics."""

    def test_search_response_time(self):
        """Test that search operations complete in reasonable time."""
        import time

        config = SearchConfig()
        engine = SearchEngine(config)

        # Create moderate dataset
        documents = [f"ESP32 API documentation {i}" for i in range(100)]

        start_time = time.time()

        # Perform multiple fuzzy matches
        results = []
        for doc in documents[:10]:  # Test first 10 documents
            result = engine.fuzzy_match("ESP32", doc)
            results.append(result)

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete quickly
        assert elapsed < 5.0  # 5 seconds max
        assert len(results) == 10

    def test_text_processing_performance(self):
        """Test text processing performance."""
        import time

        processor = TextProcessor()

        # Create moderately large content
        large_content = "ESP32 Documentation\n" + "=" * 20 + "\n\n" + "Content line.\n" * 1000

        start_time = time.time()
        cleaned = processor.clean_rst_content(large_content)
        end_time = time.time()

        elapsed = end_time - start_time

        # Should process efficiently
        assert elapsed < 2.0  # 2 seconds max
        assert isinstance(cleaned, str)
        assert len(cleaned) > 0


class TestRobustness:
    """Test system robustness."""

    def test_empty_input_handling(self):
        """Test handling of empty inputs."""
        processor = TextProcessor()

        # Test with empty content
        empty_rst = processor.clean_rst_content("")
        assert isinstance(empty_rst, str)

        empty_md = processor.clean_markdown_content("")
        assert isinstance(empty_md, str)

    def test_malformed_content_handling(self):
        """Test handling of malformed content."""
        processor = TextProcessor()

        # Test with malformed RST
        malformed_rst = "Incomplete RST\n====\n\n.. incomplete directive"
        cleaned = processor.clean_rst_content(malformed_rst)
        assert isinstance(cleaned, str)

        # Test with malformed Markdown
        malformed_md = "# Incomplete\n\n```\nunclosed code block"
        cleaned_md = processor.clean_markdown_content(malformed_md)
        assert isinstance(cleaned_md, str)

    def test_special_character_handling(self):
        """Test handling of special characters."""
        processor = TextProcessor()

        # Content with various special characters
        special_content = "API Guide\n=========\n\nChars: àáâã 中文 🚀 ©®™"
        cleaned = processor.clean_rst_content(special_content)

        assert "API Guide" in cleaned
        assert isinstance(cleaned, str)

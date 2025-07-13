"""Test configuration and fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_docs_dir():
    """Create a temporary directory with sample ESP-IDF documentation structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        docs_path = Path(temp_dir)

        # Create sample documentation structure
        api_dir = docs_path / "en" / "api-reference"
        api_dir.mkdir(parents=True)

        # Create sample API documentation
        wifi_doc = api_dir / "wifi.rst"
        wifi_doc.write_text("""
WiFi API
========

.. doxygengroup:: WiFi
   :project: esp32

WiFi Station Example
-------------------

This example shows how to connect to WiFi.

.. code-block:: c

   #include "esp_wifi.h"

   void wifi_init() {
       // Initialize WiFi
   }
""")

        # Create sample guide
        guide_dir = docs_path / "en" / "get-started"
        guide_dir.mkdir(parents=True)

        guide_doc = guide_dir / "index.rst"
        guide_doc.write_text("""
Get Started
===========

Welcome to ESP-IDF!

Installation
------------

Follow these steps to install ESP-IDF:

1. Download the toolchain
2. Set up environment variables
3. Build your first project
""")

        # Create sample markdown file
        md_doc = docs_path / "en" / "README.md"
        md_doc.write_text("""
# ESP-IDF Documentation

This is the ESP-IDF documentation.

## Features

- WiFi support
- Bluetooth support
- Various peripherals
""")

        yield str(docs_path)


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    from esp_idf_docs_mcp.config import ServerConfig  # noqa: PLC0415

    config = ServerConfig()
    config.docs_path = "/tmp/esp-idf-docs"
    config.cache_size = 10
    config.cache_ttl = 300
    config.max_file_size = 1024 * 1024
    config.search_limit = 50
    config.enable_recommendations = False

    return config

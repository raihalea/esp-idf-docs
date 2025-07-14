# ESP-IDF Documentation Explorer MCP Server

A Model Context Protocol (MCP) server for exploring ESP-IDF documentation online. This server fetches content directly from the official ESP-IDF documentation website, ensuring you always have access to the latest information. This implementation is inspired by the [AWS Documentation MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-documentation-mcp-server).

## Features

- **Online Search**: Search ESP-IDF documentation directly from the official website
- **Real-time Content**: Always access the latest documentation without local setup
- **Multi-version Support**: Choose ESP-IDF version (latest or specific versions)
- **API Reference Search**: Find API references for ESP-IDF components
- **Smart Caching**: Intelligent caching for improved performance

## Usage in MCP Clients

Add the following to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "esp-idf-docs": {
      "command": "uvx",
      "args": ["esp-idf-docs-mcp"],
      "env": {
        "ESP_IDF_VERSION": "latest",
        "ESP_IDF_CHIP_TARGET": "esp32s3"
      }
    }
  }
}
```

### Development Installation

```bash
# Clone and install for development
git clone https://github.com/raihalea/esp-idf-docs.git
cd esp-idf-docs

# Install dependencies only
uv sync

# Install with development dependencies
uv sync --dev
```

## Available Tools

### search_docs
Search ESP-IDF documentation for keywords (case-insensitive).

**Parameters:**
- `query` (string): Search query

### get_doc_structure
Get the directory structure of ESP-IDF documentation.

**Parameters:** None

### read_doc
Read the contents of a specific documentation file.

**Parameters:**
- `file_path` (string): Relative path to the documentation file

### find_api_references
Find API references for a specific ESP-IDF component.

**Parameters:**
- `component` (string): Component or API name to search for

## Environment Variables

### ESP_IDF_VERSION

ESP-IDF documentation version to use (defaults to "latest").

**Available versions:**
- `latest` - Latest stable version
- `v5.1` - ESP-IDF v5.1
- `v5.0` - ESP-IDF v5.0
- `v4.4` - ESP-IDF v4.4
- etc.

**Setting the environment variable:**

```bash
# Linux/macOS
export ESP_IDF_VERSION="v5.1"

# Windows Command Prompt
set ESP_IDF_VERSION=v5.1

# Windows PowerShell
$env:ESP_IDF_VERSION="v5.1"
```

### ESP_IDF_BASE_URL

Base URL for ESP-IDF documentation (defaults to official site).

```bash
export ESP_IDF_BASE_URL="https://docs.espressif.com/projects/esp-idf"
```

**Usage examples:**

```bash
# Run with specific version (PyPI)
ESP_IDF_VERSION="v5.1" uvx esp-idf-docs-mcp

# Run with latest (default)
uvx esp-idf-docs-mcp
```

## Testing

Run the test suite:

```bash
# Install development dependencies
uv sync --dev

# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_minimal.py -v

# Run tests with coverage (if coverage is installed)
uv run pytest --cov=src/esp_idf_docs_mcp

# Search document
ESP_IDF_CHIP_TARGET=esp32s3 ESP_IDF_VERSION=latest uv run python test_search.py bluetooth
```

### Test Categories

- **Basic Tests** (`test_minimal.py`): Core functionality and imports
- **Implementation Tests** (`test_fixed.py`): Actual implementation validation  
- **Comprehensive Tests** (`test_comprehensive.py`): Error handling, security, performance, and robustness
- **Integration Tests** (`test_explorer_integration.py`): End-to-end ESPIDFDocsExplorer testing

## Development

### Code Quality

This project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Install development dependencies
uv sync --dev

# Run linter
uv run ruff check src/ tests/

# Auto-fix linting issues
uv run ruff check src/ tests/ --fix

# Format code
uv run ruff format src/ tests/

# Check formatting
uv run ruff format --check src/ tests/
```

### Development Workflow

Common development commands:

```bash
# Setup development environment
uv sync --dev

# Run all quality checks
uv run ruff check src/ tests/ && uv run ruff format src/ tests/ && uv run pytest && uv run mypy src/ --ignore-missing-imports

# Run individual checks
uv run ruff check src/ tests/              # Linting
uv run ruff check src/ tests/ --fix        # Auto-fix linting
uv run ruff format src/ tests/             # Format code
uv run pytest                              # Run tests
uv run mypy src/ --ignore-missing-imports  # Type checking
```

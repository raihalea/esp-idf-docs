# ESP-IDF Documentation Explorer MCP Server

A Model Context Protocol (MCP) server for exploring ESP-IDF documentation. This implementation is inspired by the [AWS Documentation MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-documentation-mcp-server).

## Features

- **Document Search**: Search ESP-IDF documentation by keywords
- **Document Structure**: Get directory structure of documentation
- **File Reading**: Read specific documentation files
- **API Reference Search**: Find API references for ESP-IDF components

## Installation and Usage

Run directly with uvx:

```bash
uvx --from git+https://github.com/your-username/esp-idf-docs-mcp.git esp-idf-docs-mcp
```

For development installation:

```bash
uv pip install -e .
```

## Usage in MCP Clients

Add the following to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "esp-idf-docs": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/your-username/esp-idf-docs-mcp.git",
        "esp-idf-docs-mcp"
      ],
      "env": {
        "ESP_IDF_DOCS_PATH": "/path/to/esp-idf/docs"
      }
    }
  }
}
```

## Usage from DevContainers

See [Simple Usage Guide](README_SIMPLE_USAGE.md) for detailed instructions on using this MCP server from other DevContainer projects.

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

- `ESP_IDF_DOCS_PATH`: Path to ESP-IDF documentation directory (defaults to current working directory)

## License

MIT License
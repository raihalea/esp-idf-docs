# Simple Usage Guide - Direct Access from DevContainers

After publishing on GitHub, other projects can use the ESP-IDF Docs MCP server with just DevContainer configuration.

## Method 1: Direct uvx execution (Recommended)

Add the following to your project's `.devcontainer/devcontainer.json`:

```json
{
  "features": {
    "ghcr.io/devcontainers/features/python:1": {}
  },
  "postCreateCommand": "curl -LsSf https://astral.sh/uv/install.sh | sh"
}
```

MCP client configuration (e.g., Claude Desktop):

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
        "ESP_IDF_DOCS_PATH": "/workspace/docs"
      }
    }
  }
}
```

## Method 2: Using DevContainer Feature (Custom)

Add to your project's `.devcontainer/devcontainer.json`:

```json
{
  "features": {
    "ghcr.io/devcontainers/features/python:1": {},
    "https://github.com/your-username/esp-idf-docs-mcp/devcontainer-feature": {
      "version": "latest",
      "esp_idf_docs_path": "/workspace/docs"
    }
  }
}
```

MCP client configuration:

```json
{
  "mcpServers": {
    "esp-idf-docs": {
      "command": "esp-idf-docs-mcp"
    }
  }
}
```

## Method 3: pip install execution

```json
{
  "features": {
    "ghcr.io/devcontainers/features/python:1": {}
  },
  "postCreateCommand": "pip install git+https://github.com/your-username/esp-idf-docs-mcp.git"
}
```

MCP client configuration:

```json
{
  "mcpServers": {
    "esp-idf-docs": {
      "command": "esp-idf-docs-mcp",
      "env": {
        "ESP_IDF_DOCS_PATH": "/workspace/docs"
      }
    }
  }
}
```

## Mounting ESP-IDF Documentation

If you have actual ESP-IDF documentation, mount it in devcontainer.json:

```json
{
  "mounts": [
    "source=/path/to/esp-idf/docs,target=/workspace/esp-idf-docs,type=bind,readonly"
  ]
}
```

And set the environment variable:

```json
{
  "remoteEnv": {
    "ESP_IDF_DOCS_PATH": "/workspace/esp-idf-docs"
  }
}
```

## Available Tools

- `search_docs`: Keyword search
- `get_doc_structure`: Get documentation structure
- `read_doc`: Read specific files
- `find_api_references`: Search API references

## Troubleshooting

### If uv is not found
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

### Testing the MCP server
```bash
# Inside devcontainer
uvx --from git+https://github.com/your-username/esp-idf-docs-mcp.git esp-idf-docs-mcp
```

### Force update to latest version
```bash
uv cache clean
uvx --force --from git+https://github.com/your-username/esp-idf-docs-mcp.git esp-idf-docs-mcp
```

## Example DevContainer Configuration

Complete example for ESP-IDF projects:

```json
{
  "name": "ESP-IDF Project with Docs MCP",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  
  "features": {
    "ghcr.io/devcontainers/features/python:1": {}
  },

  "postCreateCommand": "curl -LsSf https://astral.sh/uv/install.sh | sh",
  
  "remoteEnv": {
    "ESP_IDF_DOCS_PATH": "/workspace/esp-idf/docs"
  },
  
  "mounts": [
    "source=${localWorkspaceFolder}/esp-idf/docs,target=/workspace/esp-idf/docs,type=bind,readonly"
  ]
}
```
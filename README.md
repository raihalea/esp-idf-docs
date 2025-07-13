# ESP-IDF Documentation Explorer MCP Server

ESP-IDFドキュメントを探索するためのMCP (Model Context Protocol) サーバーです。

## 機能

- **ドキュメント検索**: キーワードでESP-IDFドキュメントを検索
- **ドキュメント構造の取得**: ドキュメントのディレクトリ構造を確認
- **ファイル読み取り**: 特定のドキュメントファイルを読み取り
- **API参照検索**: ESP-IDFコンポーネントのAPI参照を検索

## インストールと実行

uvxを使用して直接実行できます：

```bash
uvx esp-idf-docs-mcp
```

または、開発環境でインストール：

```bash
uv pip install -e .
```

## 使用方法

MCPクライアント（例：Claude Desktop）の設定に以下を追加：

```json
{
  "mcpServers": {
    "esp-idf-docs": {
      "command": "uvx",
      "args": ["esp-idf-docs-mcp"],
      "env": {}
    }
  }
}
```

## 利用可能なツール

### search_docs
ESP-IDFドキュメント内でキーワード検索を実行します。

### get_doc_structure  
ドキュメントのディレクトリ構造を取得します。

### read_doc
指定したドキュメントファイルの内容を読み取ります。

### find_api_references
特定のESP-IDFコンポーネントのAPI参照を検索します。
#!/usr/bin/env python3
"""Test script for ESP-IDF Documentation Search"""

import asyncio
import sys
from src.esp_idf_docs_mcp.explorer import ESPIDFDocsExplorer
from src.esp_idf_docs_mcp.config import get_config


async def test_search(query: str):
    """Test search with a specific query."""
    config = get_config()
    explorer = ESPIDFDocsExplorer(config)

    print(f"ESP-IDF Documentation Search Test")
    print(f"=================================")
    print(f"Query: '{query}'")
    print(f"Chip target: {config.chip_target}")
    print(f"Version: {config.esp_idf_version}")
    print(f"Docs URL: {explorer.online_explorer.docs_url}")
    print()

    try:
        result = await explorer.search_docs(query)

        print(f"Search Results ({len(result.get('results', []))} found):")
        print("-" * 50)

        for i, res in enumerate(result.get("results", []), 1):
            title = res.get("title", "No title")
            url = res.get("url", "No URL")
            snippet = res.get("snippet", "No snippet")

            print(f"{i}. {title}")
            print(f"   URL: {url}")
            if snippet:
                print(f"   Snippet: {snippet[:100]}...")
            print()

        if result.get("metadata"):
            metadata = result["metadata"]
            print(f"Metadata:")
            print(f"  Search time: {metadata.get('search_time_ms', 0)}ms")
            print(f"  Total results: {metadata.get('total_results', 0)}")
            print(f"  Source: {metadata.get('source', 'unknown')}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await explorer.close()


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python test_search.py <search_query>")
        print("Example: python test_search.py gpio")
        sys.exit(1)

    query = sys.argv[1]
    asyncio.run(test_search(query))


if __name__ == "__main__":
    main()

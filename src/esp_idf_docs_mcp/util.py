"""Utility functions for ESP-IDF Documentation MCP Server.

This module provides text processing and validation functions
for the online documentation explorer.
"""

import re
from pathlib import Path


class TextProcessor:
    """Text processing utilities for documentation content."""

    @staticmethod
    def clean_rst_content(content: str) -> str:
        """Clean RST-specific markup from content."""
        if not content:
            return ""

        # Remove RST directives
        content = re.sub(r"^\.\. \w+::", "", content, flags=re.MULTILINE)

        # Remove reference links
        content = re.sub(r":ref:`[^`]+`", "", content)
        content = re.sub(r":doc:`[^`]+`", "", content)

        # Remove code-block directives but keep content
        content = re.sub(r"^\.\. code-block::\s*\w*\s*$", "", content, flags=re.MULTILINE)

        # Clean excessive whitespace
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)

        return content.strip()

    @staticmethod
    def clean_markdown_content(content: str) -> str:
        """Clean Markdown-specific markup from content."""
        if not content:
            return ""

        # Remove markdown links but keep text
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)

        # Remove markdown images
        content = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", content)

        # Remove emphasis markers
        content = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)
        content = re.sub(r"\*([^*]+)\*", r"\1", content)

        # Remove code blocks
        content = re.sub(r"```[\s\S]*?```", "", content)
        content = re.sub(r"`([^`]+)`", r"\1", content)

        return content.strip()

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for search operations."""
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Replace special characters with spaces
        text = re.sub(r"[^\w\s]", " ", text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def extract_headings(content: str) -> list[dict[str, str | int]]:
        """Extract headings from content."""
        headings = []

        # RST-style headings
        rst_patterns = [
            (r"^(.+)\n=+\s*$", 1),  # Level 1
            (r"^(.+)\n-+\s*$", 2),  # Level 2
            (r"^(.+)\n\^+\s*$", 3),  # Level 3
        ]

        for pattern, level in rst_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                headings.append({"title": match.group(1).strip(), "level": level})

        # Markdown headings
        md_matches = re.finditer(r"^(#{1,6})\s*(.+?)(?:\s*#*)?$", content, re.MULTILINE)
        for match in md_matches:
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append({"title": title, "level": level})

        return headings

    @staticmethod
    def extract_code_blocks(content: str) -> list[dict[str, str]]:
        """Extract code blocks from content."""
        code_blocks = []

        # RST code blocks
        rst_pattern = r"^\.\. code-block::\s*(\w*)\s*\n\n((?:    .+\n?)*)"
        for match in re.finditer(rst_pattern, content, re.MULTILINE):
            language = match.group(1) or "text"
            code = re.sub(r"^    ", "", match.group(2), flags=re.MULTILINE)
            code_blocks.append({"language": language, "code": code.strip()})

        # Markdown code blocks
        md_pattern = r"```(\w*)\n(.*?)```"
        for match in re.finditer(md_pattern, content, re.DOTALL):
            language = match.group(1) or "text"
            code = match.group(2).strip()
            code_blocks.append({"language": language, "code": code})

        return code_blocks


class ValidationUtils:
    """Security and validation utilities."""

    @staticmethod
    def validate_query(query: str, max_length: int = 100) -> None:
        """Validate search query."""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if len(query) > max_length:
            raise ValueError(f"Query too long. Maximum length is {max_length} characters")

        # Check for dangerous patterns
        dangerous_patterns = [
            "../",
            "..\\",
            "/etc/",
            "/proc/",
            "C:\\",
            "<script",
            "javascript:",
            "data:",
            "file://",
            "ftp://",
            "ldap://",
        ]

        query_lower = query.lower()
        for pattern in dangerous_patterns:
            if pattern in query_lower:
                raise ValueError(f"Query contains invalid pattern: {pattern}")

    @staticmethod
    def detect_encoding(file_path: Path) -> str:
        """Detect file encoding with fallbacks."""
        try:
            # Try UTF-8 first
            with open(file_path, encoding="utf-8") as f:
                f.read(1024)  # Read sample
            return "utf-8"
        except UnicodeDecodeError:
            pass

        try:
            # Try latin-1 as fallback
            with open(file_path, encoding="latin-1") as f:
                f.read(1024)
            return "latin-1"
        except UnicodeDecodeError:
            pass

        return "utf-8"  # Default fallback

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe usage."""
        # Remove or replace dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)

        # Remove control characters
        sanitized = re.sub(r"[\x00-\x1f\x7f]", "", sanitized)

        # Limit length
        if len(sanitized) > 255:
            sanitized = sanitized[:255]

        return sanitized.strip()

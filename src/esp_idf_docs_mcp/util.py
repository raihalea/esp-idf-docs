"""Utility functions for ESP-IDF Documentation MCP Server.

This module provides text processing, search utilities, validation functions,
and other reusable components inspired by AWS MCP server patterns.
"""

import asyncio
import difflib
import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadata:
    """Metadata for a documentation file."""

    file_path: str
    size_bytes: int
    line_count: int
    word_count: int
    last_modified: float
    encoding: str
    doc_type: str  # 'rst', 'md', 'txt'
    hash_md5: str


@dataclass
class SearchConfig:
    """Configuration for search operations."""

    max_results: int = 20
    max_matches_per_file: int = 5
    max_query_length: int = 100
    context_lines: int = 2
    fuzzy_threshold: float = 0.6
    enable_stemming: bool = False
    cache_size: int = 100


class TextProcessor:
    """Advanced text processing utilities for documentation."""

    @staticmethod
    def clean_rst_content(content: str) -> str:
        """Clean reStructuredText content by removing directives and comments."""
        lines = content.split("\n")
        cleaned_lines = []

        in_directive = False
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            # Skip comments
            if stripped.startswith("..") and not stripped.startswith(".. _"):
                if "::" in stripped:
                    in_directive = True
                continue

            # Check for code blocks
            if stripped.endswith("::"):
                in_code_block = True
                cleaned_lines.append(line)
                continue

            if in_code_block and line and not line[0].isspace():
                in_code_block = False

            # Skip directive content (indented after directive)
            if in_directive:
                if line and not line[0].isspace():
                    in_directive = False
                else:
                    continue

            # Clean common RST patterns
            cleaned_line = line

            # Remove inline RST markup
            cleaned_line = re.sub(r":ref:`([^`]+)`", r"\1", cleaned_line)
            cleaned_line = re.sub(r":doc:`([^`]+)`", r"\1", cleaned_line)
            cleaned_line = re.sub(r":func:`([^`]+)`", r"\1", cleaned_line)
            cleaned_line = re.sub(r":class:`([^`]+)`", r"\1", cleaned_line)
            cleaned_line = re.sub(r":meth:`([^`]+)`", r"\1", cleaned_line)

            cleaned_lines.append(cleaned_line)

        return "\n".join(cleaned_lines)

    @staticmethod
    def clean_markdown_content(content: str) -> str:
        """Clean Markdown content by removing metadata and excess formatting."""
        lines = content.split("\n")
        cleaned_lines = []

        in_front_matter = False
        front_matter_start = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Handle YAML front matter
            if i == 0 and stripped == "---":
                in_front_matter = True
                front_matter_start = True
                continue

            if in_front_matter and stripped == "---" and not front_matter_start:
                in_front_matter = False
                continue

            if in_front_matter:
                front_matter_start = False
                continue

            # Clean markdown syntax while preserving readability
            cleaned_line = line

            # Remove excessive markdown formatting
            cleaned_line = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned_line)  # Bold
            cleaned_line = re.sub(r"\*([^*]+)\*", r"\1", cleaned_line)  # Italic
            cleaned_line = re.sub(r"`([^`]+)`", r"\1", cleaned_line)  # Inline code
            cleaned_line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned_line)  # Links

            cleaned_lines.append(cleaned_line)

        return "\n".join(cleaned_lines)

    @staticmethod
    def extract_code_blocks(content: str) -> list[dict[str, str]]:
        """Extract code blocks from documentation content."""
        code_blocks = []

        # RST code blocks
        rst_pattern = r".. code-block::\s*(\w+)?\s*\n((?:\s+.*\n?)*)"
        for match in re.finditer(rst_pattern, content, re.MULTILINE):
            language = match.group(1) or "text"
            code = match.group(2)
            # Remove common indentation
            lines = code.split("\n")
            if lines:
                min_indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
                code = "\n".join(line[min_indent:] if line.strip() else line for line in lines)

            code_blocks.append({"language": language, "code": code.strip(), "type": "rst"})

        # Markdown code blocks
        md_pattern = r"```(\w+)?\s*\n(.*?)\n```"
        for match in re.finditer(md_pattern, content, re.MULTILINE | re.DOTALL):
            language = match.group(1) or "text"
            code = match.group(2)

            code_blocks.append({"language": language, "code": code.strip(), "type": "markdown"})

        return code_blocks

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for better searching."""
        # Convert to lowercase
        text = text.lower()

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove special characters but keep alphanumeric and basic punctuation
        text = re.sub(r"[^\w\s\-_.]", " ", text)

        # Remove extra spaces
        text = " ".join(text.split())

        return text

    @staticmethod
    def extract_headings(content: str) -> list[dict[str, Any]]:
        """Extract headings from RST and Markdown content."""
        headings = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Markdown headings
            md_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if md_match:
                level = len(md_match.group(1))
                title = md_match.group(2)
                headings.append({"level": level, "title": title, "line": i + 1, "type": "markdown"})
                continue

            # RST headings (underlined)
            if i + 1 < len(lines) and stripped:
                next_line = lines[i + 1].strip()
                if len(next_line) >= len(stripped) and len(set(next_line)) == 1:
                    char = next_line[0]
                    if char in "=-~^\"'#*+<>":
                        # Determine level based on character
                        level_map = {"=": 1, "-": 2, "~": 3, "^": 4, '"': 5, "'": 6}
                        level = level_map.get(char, 3)

                        headings.append(
                            {"level": level, "title": stripped, "line": i + 1, "type": "rst"}
                        )

        return headings


class SearchEngine:
    """Advanced search engine with fuzzy matching and relevance scoring."""

    def __init__(self, config: SearchConfig):
        """Initialize search engine with configuration."""
        self.config = config
        self._term_cache: dict[str, list[str]] = {}

    def fuzzy_match(self, query: str, text: str, threshold: float | None = None) -> bool:
        """Check if query fuzzy matches text."""
        threshold = threshold or self.config.fuzzy_threshold

        # Normalize both strings
        query_norm = TextProcessor.normalize_text(query)
        text_norm = TextProcessor.normalize_text(text)

        # Exact match first
        if query_norm in text_norm:
            return True

        # Fuzzy match using sequence matcher
        matcher = difflib.SequenceMatcher(None, query_norm, text_norm)
        return matcher.ratio() >= threshold

    def expand_query(self, query: str) -> list[str]:
        """Expand query with related terms and variations."""
        expanded = [query]

        # Add common variations
        query_lower = query.lower()

        # ESP-IDF specific expansions
        esp_expansions = {
            "wifi": ["wi-fi", "wireless", "wlan"],
            "gpio": ["pin", "input", "output", "digital"],
            "uart": ["serial", "communication"],
            "spi": ["serial peripheral interface"],
            "i2c": ["iic", "two wire"],
            "bluetooth": ["ble", "bt"],
            "nvs": ["non-volatile storage", "flash"],
            "freertos": ["rtos", "real-time"],
        }

        for key, synonyms in esp_expansions.items():
            if key in query_lower:
                expanded.extend(synonyms)

        # Add plural/singular forms
        if query_lower.endswith("s") and len(query_lower) > 3:
            expanded.append(query_lower[:-1])  # Remove 's'
        else:
            expanded.append(query_lower + "s")  # Add 's'

        return list(set(expanded))

    def calculate_relevance_score(
        self, query: str, content: str, matches: list[dict], metadata: DocumentMetadata
    ) -> float:
        """Calculate advanced relevance score."""
        query_lower = query.lower()
        content_lower = content.lower()

        score = 0.0

        # Base score from match count
        score += len(matches) * 10

        # Exact match bonus
        exact_matches = content_lower.count(query_lower)
        score += exact_matches * 15

        # Title/heading bonus
        headings = TextProcessor.extract_headings(content)
        for heading in headings:
            if query_lower in heading["title"].lower():
                # Higher bonus for higher level headings
                bonus = 30 - (heading["level"] * 5)
                score += max(bonus, 10)

        # File name relevance
        file_name = os.path.basename(metadata.file_path).lower()
        if query_lower in file_name:
            score += 25

        # File type bonus (prefer certain file types)
        if metadata.doc_type == "rst":
            score += 5  # RST files are often more detailed

        # Recency bonus (prefer recently modified files)
        age_days = (time.time() - metadata.last_modified) / 86400
        if age_days < 30:
            score += 10
        elif age_days < 90:
            score += 5

        # Document length penalty (prefer focused content)
        if metadata.word_count > 0:
            length_factor = min(1000 / metadata.word_count, 1.0)
            score *= 0.5 + 0.5 * length_factor

        # Normalize score
        return min(score, 100.0)

    def highlight_matches(self, text: str, query: str, max_highlight: int = 5) -> str:
        """Highlight query matches in text with smart context."""
        if not query or not text:
            return text

        query_lower = query.lower()
        text_lower = text.lower()

        # Find all match positions
        matches = []
        start = 0
        count = 0

        while start < len(text_lower) and count < max_highlight:
            pos = text_lower.find(query_lower, start)
            if pos == -1:
                break

            matches.append((pos, pos + len(query)))
            start = pos + 1
            count += 1

        if not matches:
            return text

        # Build highlighted text
        result = []
        last_end = 0

        for start_pos, end_pos in matches:
            # Add text before match
            result.append(text[last_end:start_pos])

            # Add highlighted match
            match_text = text[start_pos:end_pos]
            result.append(f"**{match_text}**")

            last_end = end_pos

        # Add remaining text
        result.append(text[last_end:])

        return "".join(result)


class FileCache:
    """Intelligent file caching with change detection."""

    def __init__(self, max_size: int = 100):
        """Initialize file cache with maximum size limit."""
        self.max_size = max_size
        self._cache: dict[str, tuple[str, float, str]] = {}  # path -> (content, mtime, hash)

    def get(self, file_path: Path) -> str | None:
        """Get cached file content if still valid."""
        path_str = str(file_path)

        if path_str not in self._cache:
            return None

        try:
            current_mtime = file_path.stat().st_mtime
            cached_content, cached_mtime, cached_hash = self._cache[path_str]

            # Check if file has been modified
            if current_mtime != cached_mtime:
                del self._cache[path_str]
                return None

            return cached_content

        except (OSError, FileNotFoundError):
            # File no longer exists
            if path_str in self._cache:
                del self._cache[path_str]
            return None

    def put(self, file_path: Path, content: str) -> None:
        """Cache file content with metadata."""
        if len(self._cache) >= self.max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        try:
            stat = file_path.stat()
            content_hash = hashlib.md5(content.encode()).hexdigest()

            self._cache[str(file_path)] = (content, stat.st_mtime, content_hash)

        except (OSError, FileNotFoundError):
            pass

    def invalidate(self, file_path: Path | None = None) -> None:
        """Invalidate cache for specific file or all files."""
        if file_path:
            self._cache.pop(str(file_path), None)
        else:
            self._cache.clear()

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "usage_percent": round((len(self._cache) / self.max_size) * 100, 2),
        }


class ValidationUtils:
    """Security and validation utilities."""

    @staticmethod
    def is_safe_path(file_path: str, base_path: Path) -> bool:
        """Check if file path is safe (no directory traversal)."""
        try:
            # Normalize and resolve paths
            full_path = (base_path / file_path).resolve()
            base_resolved = base_path.resolve()

            # Check if the resolved path is within base directory
            return str(full_path).startswith(str(base_resolved))

        except (OSError, ValueError):
            return False

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


class DocumentAnalyzer:
    """Analyze documentation quality and structure."""

    @staticmethod
    def analyze_document(content: str, metadata: DocumentMetadata) -> dict[str, Any]:
        """Comprehensive document analysis."""
        analysis: dict[str, Any] = {
            "readability": {},
            "structure": {},
            "quality": {},
            "metadata": {},
        }

        # Basic metrics
        words = content.split()
        sentences = re.split(r"[.!?]+", content)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        # Readability metrics
        analysis["readability"] = {
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "paragraph_count": len(paragraphs),
            "avg_words_per_sentence": len(words) / max(len(sentences), 1),
            "avg_sentences_per_paragraph": len(sentences) / max(len(paragraphs), 1),
        }

        # Structure analysis
        headings = TextProcessor.extract_headings(content)
        code_blocks = TextProcessor.extract_code_blocks(content)

        analysis["structure"] = {
            "heading_count": len(headings),
            "heading_levels": list({h["level"] for h in headings}),
            "code_block_count": len(code_blocks),
            "code_languages": list({cb["language"] for cb in code_blocks}),
            "has_toc": "contents::" in content or "toctree::" in content,
        }

        # Quality metrics
        links = re.findall(r"https?://[^\s]+", content)
        api_refs = re.findall(r"(?:doxygenfunction|doxygenstruct|doxygenenum)::", content)

        analysis["quality"] = {
            "external_links": len(links),
            "api_references": len(api_refs),
            "has_examples": bool(code_blocks),
            "estimated_reading_time_minutes": max(1, len(words) // 200),
        }

        # Metadata
        analysis["metadata"] = {
            "file_size_kb": metadata.size_bytes / 1024,
            "doc_type": metadata.doc_type,
            "last_modified": metadata.last_modified,
        }

        return analysis


@lru_cache(maxsize=50)
def get_similar_terms(term: str) -> list[str]:
    """Get similar terms using cached computation."""
    # This would typically use a more sophisticated similarity algorithm
    # For now, implement basic character-based similarity

    # ESP-IDF specific term mappings
    term_mappings = {
        "wifi": ["wireless", "wlan", "ap", "sta", "station"],
        "gpio": ["pin", "digital", "input", "output"],
        "uart": ["serial", "usart", "communication"],
        "spi": ["serial", "peripheral", "interface"],
        "i2c": ["iic", "two-wire", "twi"],
        "bluetooth": ["ble", "bt", "classic"],
        "nvs": ["storage", "flash", "partition"],
        "freertos": ["rtos", "task", "scheduler"],
        "esp32": ["esp-32", "espressif"],
        "idf": ["framework", "sdk"],
    }

    term_lower = term.lower()
    similar = []

    # Direct mappings
    if term_lower in term_mappings:
        similar.extend(term_mappings[term_lower])

    # Reverse mappings
    for key, values in term_mappings.items():
        if term_lower in values:
            similar.append(key)
            similar.extend(v for v in values if v != term_lower)

    return list(set(similar))


async def process_files_parallel(
    file_paths: list[Path], processor_func, max_concurrent: int = 10
) -> list[Any]:
    """Process multiple files in parallel with concurrency limit."""

    async def process_single(path: Path):
        """Process a single file."""
        try:
            return await processor_func(path)
        except Exception as e:
            logger.warning(f"Error processing {path}: {e}")
            return None

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_process(path: Path):
        async with semaphore:
            return await process_single(path)

    # Process files concurrently
    tasks = [limited_process(path) for path in file_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out None results and exceptions
    return [r for r in results if r is not None and not isinstance(r, Exception)]


def create_document_metadata(file_path: Path) -> DocumentMetadata:
    """Create metadata for a documentation file."""
    try:
        stat = file_path.stat()

        # Detect document type
        doc_type = file_path.suffix.lower().lstrip(".")
        if doc_type not in ["rst", "md", "txt"]:
            doc_type = "txt"

        # Read content to get additional metrics
        encoding = ValidationUtils.detect_encoding(file_path)
        content = file_path.read_text(encoding=encoding)

        lines = content.split("\n")
        words = content.split()

        # Calculate MD5 hash
        content_hash = hashlib.md5(content.encode()).hexdigest()

        return DocumentMetadata(
            file_path=str(file_path),
            size_bytes=stat.st_size,
            line_count=len(lines),
            word_count=len(words),
            last_modified=stat.st_mtime,
            encoding=encoding,
            doc_type=doc_type,
            hash_md5=content_hash,
        )

    except Exception as e:
        logger.error(f"Error creating metadata for {file_path}: {e}")
        raise

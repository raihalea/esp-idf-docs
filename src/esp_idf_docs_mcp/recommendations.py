"""Recommendation system for ESP-IDF Documentation MCP Server.

This module provides intelligent document recommendations based on content similarity,
user queries, and document analysis.
"""

import logging
import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ServerConfig
from .util import (
    SearchEngine,
    TextProcessor,
    ValidationUtils,
    create_document_metadata,
)

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """A single document recommendation."""

    file_path: str
    title: str
    description: str
    relevance_score: float
    recommendation_type: str
    metadata: dict[str, Any]


@dataclass
class RecommendationResponse:
    """Response containing multiple recommendations."""

    query: str
    recommendations: list[Recommendation]
    metadata: dict[str, Any]


class DocumentIndexer:
    """Index documents for fast similarity searches and recommendations."""

    def __init__(self, config: ServerConfig):
        """Initialize document indexer with configuration."""
        self.config = config
        self._document_index: dict[str, dict[str, Any]] = {}
        self._term_frequency: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._document_frequency: dict[str, int] = defaultdict(int)
        self._total_documents = 0
        self._last_indexed = 0.0

    async def build_index(self, docs_path: Path) -> None:
        """Build document index for recommendations."""
        start_time = time.time()
        logger.info("Building document index for recommendations...")

        indexed_count = 0

        # Get all documentation files
        file_patterns = [f"**/*{ext}" for ext in self.config.allowed_extensions]
        all_files = []

        for pattern in file_patterns:
            all_files.extend(docs_path.rglob(pattern))

        for file_path in all_files:
            try:
                # Create metadata
                metadata = create_document_metadata(file_path)

                # Read and process content
                encoding = ValidationUtils.detect_encoding(file_path)
                content = file_path.read_text(encoding=encoding)

                # Clean content based on type
                if file_path.suffix == ".rst":
                    cleaned_content = TextProcessor.clean_rst_content(content)
                elif file_path.suffix == ".md":
                    cleaned_content = TextProcessor.clean_markdown_content(content)
                else:
                    cleaned_content = content

                # Extract features for indexing
                normalized_content = TextProcessor.normalize_text(cleaned_content)
                words = normalized_content.split()
                headings = TextProcessor.extract_headings(content)
                code_blocks = TextProcessor.extract_code_blocks(content)

                # Extract title (first heading or filename)
                title = file_path.stem
                if headings:
                    title = headings[0]["title"]

                # Create description (first paragraph or first few sentences)
                description = self._extract_description(cleaned_content)

                # Build term frequency for this document
                word_counts = Counter(words)

                # Store document in index
                rel_path = str(file_path.relative_to(docs_path))
                self._document_index[rel_path] = {
                    "metadata": metadata,
                    "title": title,
                    "description": description,
                    "word_count": len(words),
                    "headings": headings,
                    "code_blocks": code_blocks,
                    "term_frequency": word_counts,
                    "content_length": len(cleaned_content),
                }

                # Update global term frequencies
                for term, count in word_counts.items():
                    self._term_frequency[rel_path][term] = count
                    if count > 0:  # Document contains this term
                        self._document_frequency[term] += 1

                indexed_count += 1

            except Exception as e:
                logger.warning(f"Error indexing {file_path}: {e}")

        self._total_documents = indexed_count
        self._last_indexed = time.time()

        index_time = (time.time() - start_time) * 1000
        logger.info(f"Document index built: {indexed_count} documents in {index_time:.2f}ms")

    def _extract_description(self, content: str, max_length: int = 200) -> str:
        """Extract a meaningful description from document content."""
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        # Skip common RST/Markdown headers and directives
        skip_patterns = [r"^=+$", r"^-+$", r"^#+\s", r"^\.\.\s", r"^:\w+:", r"^\*+$"]

        description_lines = []
        for line in lines:
            # Skip empty lines and patterns
            if not line or any(re.match(pattern, line) for pattern in skip_patterns):
                continue

            # Skip single words or very short lines
            if len(line) < 20:
                continue

            description_lines.append(line)

            # Stop when we have enough content
            if len(" ".join(description_lines)) >= max_length:
                break

        description = " ".join(description_lines)

        # Truncate to max length
        if len(description) > max_length:
            description = description[:max_length] + "..."

        return description or "No description available."

    def calculate_tf_idf_similarity(self, query_terms: list[str], document_path: str) -> float:
        """Calculate TF-IDF based similarity between query and document."""
        if document_path not in self._document_index:
            return 0.0

        doc_info = self._document_index[document_path]
        doc_tf = doc_info["term_frequency"]
        doc_word_count = doc_info["word_count"]

        score = 0.0

        for term in query_terms:
            if term in doc_tf:
                # Term Frequency
                tf = doc_tf[term] / doc_word_count if doc_word_count > 0 else 0

                # Inverse Document Frequency
                df = self._document_frequency.get(term, 0)
                if df > 0:
                    idf = math.log(self._total_documents / df)
                else:
                    idf = 0

                # TF-IDF score
                score += tf * idf

        return score

    def get_document_info(self, document_path: str) -> dict[str, Any] | None:
        """Get indexed information for a document."""
        return self._document_index.get(document_path)

    def get_all_documents(self) -> list[str]:
        """Get list of all indexed document paths."""
        return list(self._document_index.keys())

    def get_index_stats(self) -> dict[str, Any]:
        """Get statistics about the document index."""
        return {
            "total_documents": self._total_documents,
            "total_terms": len(self._document_frequency),
            "last_indexed": self._last_indexed,
            "index_size_mb": len(str(self._document_index)) / (1024 * 1024),
        }


class RecommendationEngine:
    """Advanced recommendation engine for ESP-IDF documentation."""

    def __init__(self, config: ServerConfig):
        """Initialize recommendation engine with configuration."""
        self.config = config
        self.indexer = DocumentIndexer(config)
        self.search_engine = SearchEngine(self._create_search_config())

    def _create_search_config(self):
        """Create search config from server config."""
        from .util import SearchConfig

        return SearchConfig(
            max_results=self.config.max_results,
            max_matches_per_file=self.config.max_matches_per_file,
            max_query_length=self.config.max_query_length,
            context_lines=self.config.context_lines,
            fuzzy_threshold=self.config.fuzzy_threshold,
            enable_stemming=self.config.enable_stemming,
            cache_size=self.config.cache_size,
        )

    async def initialize(self, docs_path: Path) -> None:
        """Initialize the recommendation engine."""
        await self.indexer.build_index(docs_path)

    async def get_recommendations(self, query: str, limit: int = 5) -> RecommendationResponse:
        """Get document recommendations based on query."""
        start_time = time.time()

        try:
            recommendations = []

            # Get different types of recommendations
            similar_docs = await self._get_content_similarity_recommendations(query, limit)
            popular_docs = await self._get_popular_recommendations(query, limit // 2)
            related_docs = await self._get_related_api_recommendations(query, limit // 2)

            # Combine and rank recommendations
            all_recommendations = []
            all_recommendations.extend(similar_docs)
            all_recommendations.extend(popular_docs)
            all_recommendations.extend(related_docs)

            # Remove duplicates and sort by relevance
            seen_files = set()
            unique_recommendations = []

            for rec in sorted(all_recommendations, key=lambda x: x.relevance_score, reverse=True):
                if rec.file_path not in seen_files:
                    unique_recommendations.append(rec)
                    seen_files.add(rec.file_path)

            # Limit to requested number
            recommendations = unique_recommendations[:limit]

            search_time = (time.time() - start_time) * 1000

            return RecommendationResponse(
                query=query,
                recommendations=recommendations,
                metadata={
                    "recommendation_count": len(recommendations),
                    "search_time_ms": round(search_time, 2),
                    "index_stats": self.indexer.get_index_stats(),
                    "recommendation_types": list({r.recommendation_type for r in recommendations}),
                },
            )

        except Exception as e:
            logger.error(f"Error generating recommendations for '{query}': {e}")
            return RecommendationResponse(
                query=query, recommendations=[], metadata={"error": str(e)}
            )

    async def _get_content_similarity_recommendations(
        self, query: str, limit: int
    ) -> list[Recommendation]:
        """Get recommendations based on content similarity."""
        recommendations = []

        # Normalize query and extract terms
        normalized_query = TextProcessor.normalize_text(query)
        query_terms = normalized_query.split()

        # Calculate similarity scores for all documents
        doc_scores = []

        for doc_path in self.indexer.get_all_documents():
            doc_info = self.indexer.get_document_info(doc_path)
            if not doc_info:
                continue

            # Calculate TF-IDF similarity
            tf_idf_score = self.indexer.calculate_tf_idf_similarity(query_terms, doc_path)

            # Add bonus for title matches
            title_bonus = 0
            for term in query_terms:
                if term in doc_info["title"].lower():
                    title_bonus += 10

            # Add bonus for heading matches
            heading_bonus = 0
            for heading in doc_info["headings"]:
                for term in query_terms:
                    if term in heading["title"].lower():
                        heading_bonus += (
                            5 / heading["level"]
                        )  # Higher level headings get more bonus

            total_score = tf_idf_score + title_bonus + heading_bonus

            if total_score > 0:
                doc_scores.append((doc_path, total_score, doc_info))

        # Sort by score and take top results
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        for doc_path, score, doc_info in doc_scores[:limit]:
            recommendations.append(
                Recommendation(
                    file_path=doc_path,
                    title=doc_info["title"],
                    description=doc_info["description"],
                    relevance_score=score,
                    recommendation_type="content_similarity",
                    metadata={
                        "word_count": doc_info["word_count"],
                        "headings_count": len(doc_info["headings"]),
                        "code_blocks_count": len(doc_info["code_blocks"]),
                        "doc_type": doc_info["metadata"].doc_type,
                    },
                )
            )

        return recommendations

    async def _get_popular_recommendations(self, query: str, limit: int) -> list[Recommendation]:
        """Get recommendations for popular/important documents."""
        recommendations = []

        # Define patterns for important documents
        important_patterns = [
            (r"getting.?started", "Getting Started Guide", 15),
            (r"api.?reference", "API Reference", 12),
            (r"example", "Code Examples", 10),
            (r"tutorial", "Tutorial", 10),
            (r"quick.?start", "Quick Start Guide", 8),
            (r"overview", "Overview Documentation", 6),
        ]

        query_lower = query.lower()

        for doc_path in self.indexer.get_all_documents():
            doc_info = self.indexer.get_document_info(doc_path)
            if not doc_info:
                continue

            score = 0
            recommendation_type = "popular"

            # Check for important document patterns
            for pattern, description, points in important_patterns:
                if re.search(pattern, doc_path.lower()) or re.search(
                    pattern, doc_info["title"].lower()
                ):
                    score += points
                    recommendation_type = f"popular_{description.lower().replace(' ', '_')}"
                    break

            # Bonus for larger documents (more comprehensive)
            if doc_info["word_count"] > 1000:
                score += 5

            # Bonus for documents with many headings (well-structured)
            if len(doc_info["headings"]) > 5:
                score += 3

            # Bonus for documents with code examples
            if len(doc_info["code_blocks"]) > 0:
                score += 4

            # Query relevance check
            query_relevant = any(
                term in doc_info["title"].lower() or term in doc_info["description"].lower()
                for term in query_lower.split()
            )

            if score > 0 and query_relevant:
                recommendations.append(
                    Recommendation(
                        file_path=doc_path,
                        title=doc_info["title"],
                        description=doc_info["description"],
                        relevance_score=score,
                        recommendation_type=recommendation_type,
                        metadata={
                            "word_count": doc_info["word_count"],
                            "importance_score": score,
                            "doc_type": doc_info["metadata"].doc_type,
                        },
                    )
                )

        # Sort by relevance and return top results
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        return recommendations[:limit]

    async def _get_related_api_recommendations(
        self, query: str, limit: int
    ) -> list[Recommendation]:
        """Get recommendations for related API documentation."""
        recommendations = []

        # ESP-IDF API component mappings
        api_relationships = {
            "wifi": ["esp_wifi", "wireless", "ap", "sta", "station", "network"],
            "bluetooth": ["ble", "bt", "classic", "gatt", "gap"],
            "gpio": ["pin", "digital", "input", "output", "interrupt"],
            "uart": ["serial", "communication", "usart", "console"],
            "spi": ["serial", "peripheral", "interface", "master", "slave"],
            "i2c": ["iic", "two-wire", "twi", "master", "slave"],
            "timer": ["countdown", "alarm", "interrupt", "hardware"],
            "adc": ["analog", "digital", "converter", "voltage"],
            "dac": ["digital", "analog", "converter", "output"],
            "pwm": ["pulse", "width", "modulation", "signal"],
            "nvs": ["storage", "flash", "partition", "key-value"],
            "spiffs": ["filesystem", "flash", "storage"],
            "fatfs": ["filesystem", "fat", "storage", "sdcard"],
            "freertos": ["rtos", "task", "scheduler", "queue", "semaphore"],
            "esp32": ["esp-32", "espressif", "chip", "mcu"],
            "http": ["client", "server", "request", "response", "web"],
            "mqtt": ["message", "broker", "publish", "subscribe"],
            "json": ["parse", "generate", "data", "format"],
            "ota": ["update", "firmware", "upgrade", "download"],
            "security": ["encryption", "tls", "ssl", "crypto", "hash"],
        }

        query_lower = query.lower()
        related_terms = set()

        # Find related terms
        for key, terms in api_relationships.items():
            if key in query_lower or any(term in query_lower for term in terms):
                related_terms.update(terms)
                related_terms.add(key)

        if not related_terms:
            return recommendations

        # Score documents based on related term presence
        for doc_path in self.indexer.get_all_documents():
            doc_info = self.indexer.get_document_info(doc_path)
            if not doc_info:
                continue

            score = 0
            matched_terms = []

            # Check document content for related terms
            doc_text = (doc_info["title"] + " " + doc_info["description"]).lower()

            for term in related_terms:
                if term in doc_text:
                    score += 3
                    matched_terms.append(term)

            # Check headings for API references
            for heading in doc_info["headings"]:
                for term in related_terms:
                    if term in heading["title"].lower():
                        score += 5
                        if term not in matched_terms:
                            matched_terms.append(term)

            # Bonus for API reference documents
            if "api" in doc_path.lower() or "reference" in doc_path.lower():
                score += 8

            if score > 0:
                recommendations.append(
                    Recommendation(
                        file_path=doc_path,
                        title=doc_info["title"],
                        description=doc_info["description"],
                        relevance_score=score,
                        recommendation_type="related_api",
                        metadata={
                            "matched_terms": matched_terms,
                            "api_relevance_score": score,
                            "doc_type": doc_info["metadata"].doc_type,
                        },
                    )
                )

        # Sort by relevance and return top results
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        return recommendations[:limit]

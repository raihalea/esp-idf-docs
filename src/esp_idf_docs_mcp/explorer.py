"""Document explorer for ESP-IDF Documentation MCP Server.

This module contains the main document exploration logic,
separated from the server implementation for better organization.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from .config import ServerConfig
from .recommendations import RecommendationEngine
from .util import (
    DocumentAnalyzer,
    FileCache,
    SearchConfig,
    SearchEngine,
    TextProcessor,
    ValidationUtils,
    create_document_metadata,
)

logger = logging.getLogger(__name__)


class ESPIDFDocsExplorer:
    """Enhanced ESP-IDF Documentation Explorer with utility integration."""

    def __init__(self, config: ServerConfig):
        """Initialize the explorer with configuration."""
        self.config = config
        self.docs_path = config.docs_path

        # Initialize utility components
        search_config = SearchConfig(
            max_results=config.max_results,
            max_matches_per_file=config.max_matches_per_file,
            max_query_length=config.max_query_length,
            context_lines=config.context_lines,
            fuzzy_threshold=config.fuzzy_threshold,
            enable_stemming=config.enable_stemming,
            cache_size=config.cache_size,
        )

        self.search_engine = SearchEngine(search_config)
        self.file_cache = FileCache(config.cache_size)
        self.text_processor = TextProcessor()

        # Initialize recommendation engine if enabled
        self.recommendation_engine = None
        if config.enable_recommendations:
            self.recommendation_engine = RecommendationEngine(config)

        logger.info(f"Initialized ESP-IDF Docs Explorer with path: {self.docs_path}")
        logger.debug(f"Configuration: {config.to_dict()}")

        # Initialize recommendation engine asynchronously
        if self.recommendation_engine:
            asyncio.create_task(self._initialize_recommendations())

    async def _initialize_recommendations(self) -> None:
        """Initialize recommendation engine in background."""
        try:
            if self.recommendation_engine:
                await self.recommendation_engine.initialize(self.docs_path)
                logger.info("Recommendation engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize recommendation engine: {e}")

    def _validate_file_path(self, file_path: str) -> None:
        """Validate file path input using utility functions."""
        if self.config.enable_path_validation:
            if not ValidationUtils.is_safe_path(file_path, self.docs_path):
                raise ValueError(f"Unsafe file path: {file_path}")

        # Check file extension
        path_obj = Path(file_path)
        if path_obj.suffix not in self.config.allowed_extensions:
            raise ValueError(
                f"File must have one of these extensions: {self.config.allowed_extensions}"
            )

    def _get_all_doc_files(self) -> list[Path]:
        """Get all documentation files matching configured extensions."""
        file_patterns = [f"**/*{ext}" for ext in self.config.allowed_extensions]
        all_files = []

        for pattern in file_patterns:
            all_files.extend(self.docs_path.rglob(pattern))

        return all_files

    def _process_file_content(self, file_path: Path, content: str) -> str:
        """Process file content based on file type."""
        if file_path.suffix == ".rst":
            return TextProcessor.clean_rst_content(content)
        elif file_path.suffix == ".md":
            return TextProcessor.clean_markdown_content(content)
        else:
            return content

    def _extract_matches_from_content(self, content: str, query: str) -> list[dict[str, Any]]:
        """Extract matches with enhanced highlighting from content."""
        lines = content.split("\n")
        matches = []

        for i, line in enumerate(lines):
            if query.lower() in line.lower():
                # Get context with highlighting
                start = max(0, i - self.config.context_lines)
                end = min(len(lines), i + self.config.context_lines + 1)

                context_lines = []
                for j in range(start, end):
                    if j < len(lines):
                        line_text = lines[j]
                        if j == i:  # Highlight the matching line
                            highlighted = self.search_engine.highlight_matches(line_text, query)
                            context_lines.append(
                                {
                                    "line": j + 1,
                                    "text": line_text.strip(),
                                    "highlighted": highlighted.strip(),
                                    "is_match": True,
                                }
                            )
                        else:
                            context_lines.append(
                                {
                                    "line": j + 1,
                                    "text": line_text.strip(),
                                    "highlighted": line_text.strip(),
                                    "is_match": False,
                                }
                            )

                matches.append(
                    {"line_number": i + 1, "context": context_lines, "snippet": line.strip()}
                )

                if len(matches) >= self.config.max_matches_per_file:
                    break

        return matches

    async def search_docs(
        self, query: str, limit: int | None = None, offset: int = 0
    ) -> dict[str, Any]:
        """Search ESP-IDF documentation with enhanced features."""
        start_time = time.time()

        try:
            # Validate input using utility functions
            ValidationUtils.validate_query(query, self.config.max_query_length)

            # Use provided limit or default
            effective_limit = min(limit or self.config.max_results, self.config.max_results)

            logger.info(
                f"Starting search for query: '{query}' (limit={effective_limit}, offset={offset})"
            )

            all_results = []
            files_scanned = 0

            # Get all documentation files
            all_files = self._get_all_doc_files()

            # Process files
            for file_path in all_files:
                files_scanned += 1

                try:
                    # Use cache if available
                    content = self.file_cache.get(file_path)
                    if content is None:
                        encoding = ValidationUtils.detect_encoding(file_path)
                        content = file_path.read_text(encoding=encoding)
                        self.file_cache.put(file_path, content)

                    # Clean content based on file type
                    cleaned_content = self._process_file_content(file_path, content)

                    # Check for matches using enhanced search
                    if self.config.enable_fuzzy_search:
                        has_match = self.search_engine.fuzzy_match(query, cleaned_content)
                    else:
                        has_match = query.lower() in cleaned_content.lower()

                    if has_match:
                        # Create document metadata
                        try:
                            metadata = create_document_metadata(file_path)
                        except Exception as e:
                            logger.warning(f"Could not create metadata for {file_path}: {e}")
                            continue

                        # Extract matches with enhanced highlighting
                        matches = self._extract_matches_from_content(content, query)

                        if matches:
                            # Calculate relevance score using advanced algorithm
                            score = self.search_engine.calculate_relevance_score(
                                query, cleaned_content, matches, metadata
                            )

                            result = {
                                "file": str(file_path.relative_to(self.docs_path)),
                                "matches": matches,
                                "score": score,
                                "metadata": {
                                    "size_kb": round(metadata.size_bytes / 1024, 2),
                                    "word_count": metadata.word_count,
                                    "doc_type": metadata.doc_type,
                                },
                            }
                            all_results.append(result)

                except UnicodeDecodeError:
                    logger.warning(f"Could not decode file: {file_path}")
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")

            # Sort by relevance score (descending)
            all_results.sort(key=lambda x: x["score"], reverse=True)

            # Apply pagination
            paginated_results = all_results[offset : offset + effective_limit]

            search_time = (time.time() - start_time) * 1000

            # Enhanced response with query expansion info
            expanded_queries = []
            if self.config.enable_query_expansion:
                from .util import get_similar_terms

                expanded_queries = get_similar_terms(query)

            response = {
                "query": query,
                "expanded_queries": expanded_queries,
                "results": paginated_results,
                "metadata": {
                    "total_files_scanned": files_scanned,
                    "total_results_found": len(all_results),
                    "results_returned": len(paginated_results),
                    "search_time_ms": round(search_time, 2),
                    "fuzzy_search_enabled": self.config.enable_fuzzy_search,
                    "query_expansion_enabled": self.config.enable_query_expansion,
                    "cache_stats": self.file_cache.get_cache_stats(),
                },
            }

            logger.info(
                f"Search completed: found {len(all_results)} results in {files_scanned} files "
                f"({search_time:.2f}ms)"
            )

            return response

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            raise

    async def get_doc_structure(self) -> dict[str, Any]:
        """Get the structure of ESP-IDF documentation with enhanced metadata."""
        start_time = time.time()

        try:
            logger.debug("Getting documentation structure")

            structure = {
                "directories": {},
                "files": [],
                "metadata": {
                    "total_directories": 0,
                    "total_files": 0,
                    "supported_extensions": self.config.allowed_extensions,
                    "total_size_mb": 0,
                },
            }

            total_files = 0
            total_dirs = 0
            total_size = 0

            # Find all documentation directories and files
            for item in self.docs_path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    # Get all files matching allowed extensions
                    doc_files = []
                    for ext in self.config.allowed_extensions:
                        doc_files.extend(item.rglob(f"*{ext}"))

                    if doc_files:
                        # Group by extension
                        ext_counts = {}
                        dir_size = 0

                        for file_path in doc_files:
                            ext = file_path.suffix
                            ext_counts[ext] = ext_counts.get(ext, 0) + 1
                            try:
                                dir_size += file_path.stat().st_size
                            except OSError:
                                pass

                        structure["directories"][item.name] = {
                            "file_count": len(doc_files),
                            "size_kb": round(dir_size / 1024, 2),
                            "extensions": ext_counts,
                        }
                        total_dirs += 1
                        total_size += dir_size

                elif item.suffix in self.config.allowed_extensions:
                    try:
                        file_stat = item.stat()
                        structure["files"].append(
                            {
                                "name": item.name,
                                "size_kb": round(file_stat.st_size / 1024, 2),
                                "extension": item.suffix,
                                "last_modified": file_stat.st_mtime,
                            }
                        )
                        total_files += 1
                        total_size += file_stat.st_size
                    except OSError:
                        pass

            structure["metadata"].update(
                {
                    "total_directories": total_dirs,
                    "total_files": total_files,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "scan_time_ms": round((time.time() - start_time) * 1000, 2),
                }
            )

            logger.debug(f"Structure scan completed: {total_dirs} dirs, {total_files} files")

            return structure

        except Exception as e:
            logger.error(f"Error getting doc structure: {e}")
            raise

    async def read_doc(self, file_path: str) -> dict[str, Any] | None:
        """Read a specific documentation file with enhanced metadata."""
        try:
            # Validate input
            self._validate_file_path(file_path)

            logger.debug(f"Reading file: {file_path}")

            full_path = self.docs_path / file_path

            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            if not full_path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")

            # Check file size
            file_size = full_path.stat().st_size
            if file_size > self.config.max_file_size_kb * 1024:
                raise ValueError(
                    f"File too large: {file_size} bytes (max: {self.config.max_file_size_kb}KB)"
                )

            # Read file content with proper encoding detection
            encoding = ValidationUtils.detect_encoding(full_path)
            content = full_path.read_text(encoding=encoding)

            # Create comprehensive metadata
            metadata = create_document_metadata(full_path)

            result = {
                "content": content,
                "metadata": {
                    "file_path": file_path,
                    "size_bytes": metadata.size_bytes,
                    "size_kb": round(metadata.size_bytes / 1024, 2),
                    "line_count": metadata.line_count,
                    "word_count": metadata.word_count,
                    "extension": full_path.suffix,
                    "encoding": metadata.encoding,
                    "doc_type": metadata.doc_type,
                    "last_modified": metadata.last_modified,
                    "hash_md5": metadata.hash_md5,
                },
            }

            # Add document analysis if enabled
            if self.config.enable_document_analysis:
                analysis = DocumentAnalyzer.analyze_document(content, metadata)
                result["analysis"] = analysis

            return result

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise

    async def find_api_references(self, component: str) -> dict[str, Any]:
        """Find API references for a specific ESP-IDF component with enhanced search."""
        start_time = time.time()

        try:
            if not component or not component.strip():
                raise ValueError("Component name cannot be empty")

            # Sanitize component name
            component_clean = component.strip()
            component_escaped = ValidationUtils.sanitize_filename(component_clean)

            logger.info(f"Finding API references for component: {component_clean}")

            results = []
            files_scanned = 0

            # Enhanced API patterns with escaped component name
            import re

            component_regex = re.escape(component_clean)
            api_patterns = [
                (rf".. doxygenfunction::\s*{component_regex}", "function"),
                (rf".. doxygenstruct::\s*{component_regex}", "struct"),
                (rf".. doxygenenum::\s*{component_regex}", "enum"),
                (rf".. doxygendefine::\s*{component_regex}", "define"),
                (rf"`{component_regex}`", "reference"),
                (rf"#{component_regex}", "heading"),
                (rf"## {component_regex}", "heading"),
                (rf"### {component_regex}", "heading"),
                (rf"\\b{component_regex}_\\w+", "function_family"),
            ]

            # Get all documentation files
            all_files = self._get_all_doc_files()

            for file_path in all_files:
                files_scanned += 1

                try:
                    # Use proper encoding detection
                    encoding = ValidationUtils.detect_encoding(file_path)
                    content = file_path.read_text(encoding=encoding)

                    file_matches = []
                    for api_pattern, match_type in api_patterns:
                        matches = list(
                            re.finditer(api_pattern, content, re.IGNORECASE | re.MULTILINE)
                        )
                        for match in matches:
                            # Get line number
                            line_num = content[: match.start()].count("\n") + 1

                            file_matches.append(
                                {
                                    "type": match_type,
                                    "pattern": match.group(0),
                                    "line_number": line_num,
                                    "context": content.split("\n")[line_num - 1].strip(),
                                }
                            )

                    if file_matches:
                        results.append(
                            {
                                "file": str(file_path.relative_to(self.docs_path)),
                                "matches": file_matches,
                                "match_count": len(file_matches),
                            }
                        )

                except Exception as e:
                    logger.warning(f"Error processing file {file_path}: {e}")

            # Sort by match count (descending)
            results.sort(key=lambda x: x["match_count"], reverse=True)

            search_time = (time.time() - start_time) * 1000

            return {
                "component": component_clean,
                "query_variations": [component_clean, component_escaped],
                "results": results,
                "metadata": {
                    "total_files_scanned": files_scanned,
                    "files_with_matches": len(results),
                    "total_matches": sum(r["match_count"] for r in results),
                    "search_time_ms": round(search_time, 2),
                    "pattern_count": len(api_patterns),
                },
            }

        except Exception as e:
            logger.error(f"Error finding API references for {component}: {e}")
            raise

    async def get_recommendations(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Get document recommendations based on query."""
        if not self.recommendation_engine:
            return {
                "error": "Recommendation system is disabled",
                "query": query,
                "recommendations": [],
                "metadata": {"feature_enabled": False},
            }

        try:
            response = await self.recommendation_engine.get_recommendations(query, limit)

            return {
                "query": response.query,
                "recommendations": [
                    {
                        "file_path": rec.file_path,
                        "title": rec.title,
                        "description": rec.description,
                        "relevance_score": rec.relevance_score,
                        "recommendation_type": rec.recommendation_type,
                        "metadata": rec.metadata,
                    }
                    for rec in response.recommendations
                ],
                "metadata": response.metadata,
            }

        except Exception as e:
            logger.error(f"Error getting recommendations for '{query}': {e}")
            return {"error": str(e), "query": query, "recommendations": [], "metadata": {}}

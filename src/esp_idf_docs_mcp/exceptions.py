"""
Custom exceptions for ESP-IDF Documentation MCP Server.

This module defines custom exception classes for better error handling
and more specific error reporting.
"""


class ESPIDFDocsError(Exception):
    """Base exception for ESP-IDF Docs MCP Server."""
    pass


class ConfigurationError(ESPIDFDocsError):
    """Raised when there's a configuration issue."""
    pass


class ValidationError(ESPIDFDocsError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None, value: str = None):
        super().__init__(message)
        self.field = field
        self.value = value


class FileAccessError(ESPIDFDocsError):
    """Raised when file access fails."""
    
    def __init__(self, message: str, file_path: str = None):
        super().__init__(message)
        self.file_path = file_path


class SearchError(ESPIDFDocsError):
    """Raised when search operation fails."""
    
    def __init__(self, message: str, query: str = None):
        super().__init__(message)
        self.query = query


class RecommendationError(ESPIDFDocsError):
    """Raised when recommendation system fails."""
    pass


class CacheError(ESPIDFDocsError):
    """Raised when cache operation fails."""
    pass


class EncodingError(FileAccessError):
    """Raised when file encoding detection/decoding fails."""
    pass


class SecurityError(ValidationError):
    """Raised when security validation fails."""
    pass
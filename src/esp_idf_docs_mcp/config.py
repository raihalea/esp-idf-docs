"""
Configuration management for ESP-IDF Documentation MCP Server.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List


@dataclass
class ServerConfig:
    """Main server configuration."""
    
    # Server identification
    server_name: str = "esp-idf-docs-explorer"
    server_version: str = "0.3.0"
    
    # Documentation paths
    docs_path: Path = field(default_factory=lambda: Path.cwd())
    
    # Search configuration
    max_results: int = 20
    max_matches_per_file: int = 5
    max_query_length: int = 100
    context_lines: int = 2
    
    # Advanced search features
    enable_fuzzy_search: bool = True
    fuzzy_threshold: float = 0.6
    enable_query_expansion: bool = True
    enable_stemming: bool = False
    
    # Performance settings
    cache_size: int = 100
    max_concurrent_files: int = 10
    max_file_size_kb: int = 1024
    
    # Security settings
    allowed_extensions: List[str] = field(default_factory=lambda: ['.rst', '.md', '.txt'])
    enable_path_validation: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Feature flags
    enable_recommendations: bool = True
    enable_document_analysis: bool = True
    enable_metrics: bool = True
    
    @classmethod
    def from_environment(cls) -> 'ServerConfig':
        """Create configuration from environment variables."""
        
        # Get docs path from environment
        docs_path_str = os.getenv('ESP_IDF_DOCS_PATH', str(Path.cwd()))
        docs_path = Path(docs_path_str)
        
        # Parse boolean values
        def parse_bool(value: str, default: bool = False) -> bool:
            if not value:
                return default
            return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
        
        # Parse integer values
        def parse_int(value: str, default: int) -> int:
            try:
                return int(value) if value else default
            except ValueError:
                return default
        
        # Parse float values
        def parse_float(value: str, default: float) -> float:
            try:
                return float(value) if value else default
            except ValueError:
                return default
        
        # Parse list values
        def parse_list(value: str, default: List[str]) -> List[str]:
            if not value:
                return default
            return [item.strip() for item in value.split(',') if item.strip()]
        
        return cls(
            # Server identification
            server_name=os.getenv('ESP_IDF_SERVER_NAME', 'esp-idf-docs-explorer'),
            server_version=os.getenv('ESP_IDF_SERVER_VERSION', '0.3.0'),
            
            # Documentation paths
            docs_path=docs_path,
            
            # Search configuration
            max_results=parse_int(os.getenv('ESP_IDF_MAX_RESULTS'), 20),
            max_matches_per_file=parse_int(os.getenv('ESP_IDF_MAX_MATCHES_PER_FILE'), 5),
            max_query_length=parse_int(os.getenv('ESP_IDF_MAX_QUERY_LENGTH'), 100),
            context_lines=parse_int(os.getenv('ESP_IDF_CONTEXT_LINES'), 2),
            
            # Advanced search features
            enable_fuzzy_search=parse_bool(os.getenv('ESP_IDF_ENABLE_FUZZY_SEARCH'), True),
            fuzzy_threshold=parse_float(os.getenv('ESP_IDF_FUZZY_THRESHOLD'), 0.6),
            enable_query_expansion=parse_bool(os.getenv('ESP_IDF_ENABLE_QUERY_EXPANSION'), True),
            enable_stemming=parse_bool(os.getenv('ESP_IDF_ENABLE_STEMMING'), False),
            
            # Performance settings
            cache_size=parse_int(os.getenv('ESP_IDF_CACHE_SIZE'), 100),
            max_concurrent_files=parse_int(os.getenv('ESP_IDF_MAX_CONCURRENT_FILES'), 10),
            max_file_size_kb=parse_int(os.getenv('ESP_IDF_MAX_FILE_SIZE_KB'), 1024),
            
            # Security settings
            allowed_extensions=parse_list(
                os.getenv('ESP_IDF_ALLOWED_EXTENSIONS'), 
                ['.rst', '.md', '.txt']
            ),
            enable_path_validation=parse_bool(os.getenv('ESP_IDF_ENABLE_PATH_VALIDATION'), True),
            
            # Logging configuration
            log_level=os.getenv('ESP_IDF_LOG_LEVEL', 'INFO'),
            log_format=os.getenv('ESP_IDF_LOG_FORMAT', 
                               '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            
            # Feature flags
            enable_recommendations=parse_bool(os.getenv('ESP_IDF_ENABLE_RECOMMENDATIONS'), True),
            enable_document_analysis=parse_bool(os.getenv('ESP_IDF_ENABLE_DOCUMENT_ANALYSIS'), True),
            enable_metrics=parse_bool(os.getenv('ESP_IDF_ENABLE_METRICS'), True),
        )
    
    def validate(self) -> None:
        """Validate configuration values."""
        errors = []
        
        # Validate paths
        if not self.docs_path.exists():
            errors.append(f"Documentation path does not exist: {self.docs_path}")
        
        if not self.docs_path.is_dir():
            errors.append(f"Documentation path is not a directory: {self.docs_path}")
        
        # Validate numeric ranges
        if self.max_results <= 0 or self.max_results > 1000:
            errors.append(f"max_results must be between 1 and 1000, got {self.max_results}")
        
        if self.max_matches_per_file <= 0 or self.max_matches_per_file > 100:
            errors.append(f"max_matches_per_file must be between 1 and 100, got {self.max_matches_per_file}")
        
        if self.max_query_length <= 0 or self.max_query_length > 1000:
            errors.append(f"max_query_length must be between 1 and 1000, got {self.max_query_length}")
        
        if self.fuzzy_threshold < 0.0 or self.fuzzy_threshold > 1.0:
            errors.append(f"fuzzy_threshold must be between 0.0 and 1.0, got {self.fuzzy_threshold}")
        
        if self.cache_size <= 0 or self.cache_size > 10000:
            errors.append(f"cache_size must be between 1 and 10000, got {self.cache_size}")
        
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_levels:
            errors.append(f"log_level must be one of {valid_levels}, got {self.log_level}")
        
        # Validate extensions
        if not self.allowed_extensions:
            errors.append("allowed_extensions cannot be empty")
        
        for ext in self.allowed_extensions:
            if not ext.startswith('.'):
                errors.append(f"Extension must start with '.', got {ext}")
        
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                result[key] = str(value)
            else:
                result[key] = value
        return result
    
    def __post_init__(self):
        """Post-initialization validation."""
        # Convert string path to Path object if needed
        if isinstance(self.docs_path, str):
            self.docs_path = Path(self.docs_path)
        
        # Ensure extensions start with dot
        self.allowed_extensions = [
            ext if ext.startswith('.') else f'.{ext}' 
            for ext in self.allowed_extensions
        ]
        
        # Normalize log level
        self.log_level = self.log_level.upper()


# Global configuration instance
_config: Optional[ServerConfig] = None


def get_config() -> ServerConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = ServerConfig.from_environment()
        _config.validate()
    return _config


def set_config(config: ServerConfig) -> None:
    """Set the global configuration instance."""
    global _config
    config.validate()
    _config = config


def reload_config() -> ServerConfig:
    """Reload configuration from environment."""
    global _config
    _config = ServerConfig.from_environment()
    _config.validate()
    return _config


# Environment variable documentation for users
ENV_VAR_DOCS = """
ESP-IDF Documentation MCP Server Environment Variables:

Server Configuration:
  ESP_IDF_SERVER_NAME          Server name (default: esp-idf-docs-explorer)
  ESP_IDF_SERVER_VERSION       Server version (default: 0.3.0)
  ESP_IDF_DOCS_PATH           Path to ESP-IDF documentation (default: current directory)

Search Configuration:
  ESP_IDF_MAX_RESULTS         Maximum search results (default: 20)
  ESP_IDF_MAX_MATCHES_PER_FILE Maximum matches per file (default: 5)
  ESP_IDF_MAX_QUERY_LENGTH    Maximum query length (default: 100)
  ESP_IDF_CONTEXT_LINES       Context lines around matches (default: 2)

Advanced Search:
  ESP_IDF_ENABLE_FUZZY_SEARCH Enable fuzzy search (default: true)
  ESP_IDF_FUZZY_THRESHOLD     Fuzzy search threshold (default: 0.6)
  ESP_IDF_ENABLE_QUERY_EXPANSION Enable query expansion (default: true)
  ESP_IDF_ENABLE_STEMMING     Enable word stemming (default: false)

Performance:
  ESP_IDF_CACHE_SIZE          File cache size (default: 100)
  ESP_IDF_MAX_CONCURRENT_FILES Max concurrent file processing (default: 10)
  ESP_IDF_MAX_FILE_SIZE_KB    Maximum file size in KB (default: 1024)

Security:
  ESP_IDF_ALLOWED_EXTENSIONS  Allowed file extensions (default: .rst,.md,.txt)
  ESP_IDF_ENABLE_PATH_VALIDATION Enable path validation (default: true)

Logging:
  ESP_IDF_LOG_LEVEL           Log level (default: INFO)
  ESP_IDF_LOG_FORMAT          Log format string

Features:
  ESP_IDF_ENABLE_RECOMMENDATIONS Enable recommendation system (default: true)
  ESP_IDF_ENABLE_DOCUMENT_ANALYSIS Enable document analysis (default: true)
  ESP_IDF_ENABLE_METRICS      Enable metrics collection (default: true)

Example usage:
  export ESP_IDF_DOCS_PATH=/path/to/esp-idf/docs
  export ESP_IDF_MAX_RESULTS=50
  export ESP_IDF_ENABLE_FUZZY_SEARCH=true
"""
"""Configuration management for SynthDB."""

import os
from typing import Optional


class Config:
    """Configuration class for SynthDB."""
    
    def __init__(self) -> None:
        self._backend: str = "sqlite"  # Default value
        self._load_from_env()
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        self._backend = os.getenv("SYNTHDB_BACKEND", "sqlite")
    
    @property
    def backend(self) -> str:
        """Get the default backend."""
        return self._backend
    
    @backend.setter
    def backend(self, value: str) -> None:
        """Set the default backend."""
        if value not in ("sqlite", "libsql"):
            raise ValueError(f"Invalid backend: {value}. Supported: libsql, sqlite")
        self._backend = value
    
    def get_backend_for_path(self, db_path: str, explicit_backend: Optional[str] = None) -> str:
        """Get the backend to use for a specific database path."""
        if explicit_backend:
            return explicit_backend
        
        # Check for remote LibSQL URLs
        if isinstance(db_path, str) and db_path.startswith(('http://', 'https://', 'libsql://')):
            return "libsql"
        
        # Use default backend (libsql)
        return self.backend


# Global configuration instance
config = Config()


def set_default_backend(backend: str) -> None:
    """Set the default backend globally."""
    config.backend = backend


def get_default_backend() -> str:
    """Get the default backend."""
    return config.backend
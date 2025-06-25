"""Configuration management for SynthDB."""

import os
from typing import Optional
from pathlib import Path


class Config:
    """Configuration class for SynthDB."""
    
    def __init__(self):
        self._backend = None
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        self._backend = os.getenv("SYNTHDB_BACKEND", "limbo")
    
    @property
    def backend(self) -> str:
        """Get the default backend."""
        return self._backend
    
    @backend.setter
    def backend(self, value: str):
        """Set the default backend."""
        if value not in ("limbo", "sqlite"):
            raise ValueError(f"Invalid backend: {value}. Supported: limbo, sqlite")
        self._backend = value
    
    def get_backend_for_path(self, db_path: str, explicit_backend: Optional[str] = None) -> str:
        """Get the backend to use for a specific database path."""
        if explicit_backend:
            return explicit_backend
        
        # Check if file exists and has a specific extension preference
        path = Path(db_path)
        if path.suffix == ".sqlite" or path.suffix == ".sqlite3":
            return "sqlite"
        elif path.suffix == ".limbo":
            return "limbo"
        
        # Use default backend
        return self.backend


# Global configuration instance
config = Config()


def set_default_backend(backend: str):
    """Set the default backend globally."""
    config.backend = backend


def get_default_backend() -> str:
    """Get the default backend."""
    return config.backend
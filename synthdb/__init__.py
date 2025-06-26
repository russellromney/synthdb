"""
SynthDB - A flexible database system with schema-on-write capabilities.

This package provides a flexible schema-on-write database system that stores
data with dynamic schemas while presenting familiar table-like views.
"""

__version__ = "0.1.0"

# Connection-based API (recommended)
from .connection import Connection, connect

# Backend configuration
from .config import set_default_backend, get_default_backend
from .backends import get_backend

# Data import/export utilities
from .bulk import load_csv, load_json, export_csv, export_json

__all__ = [
    # Connection-based API
    "Connection",
    "connect",
    
    # Configuration
    "set_default_backend",
    "get_default_backend", 
    "get_backend",
    
    # Data utilities
    "load_csv",
    "load_json", 
    "export_csv",
    "export_json",
]
"""
SynthDB - A synthetic database system using Entity-Attribute-Value (EAV) model.

This package provides a flexible schema-on-write database system that stores
data in a type-specific EAV format while presenting familiar table-like views.
"""

__version__ = "0.1.0"

from .core import create_table, add_column, insert_typed_value
from .utils import query_view, export_table_structure, list_tables, list_columns
from .database import make_db
from .views import create_table_views

__all__ = [
    "create_table",
    "add_column", 
    "insert_typed_value",
    "query_view",
    "export_table_structure",
    "list_tables",
    "list_columns",
    "make_db",
    "create_table_views",
]
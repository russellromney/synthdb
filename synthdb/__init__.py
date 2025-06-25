"""
SynthDB - A flexible database system with schema-on-write capabilities.

This package provides a flexible schema-on-write database system that stores
data with dynamic schemas while presenting familiar table-like views.
"""

__version__ = "0.1.0"

from .core import create_table, add_column, insert_typed_value
from .utils import query_view, export_table_structure, list_tables, list_columns
from .database import make_db
from .views import create_table_views
from .config import set_default_backend, get_default_backend
from .backends import get_backend
from .inference import smart_insert, infer_type, create_table_from_data, suggest_column_types
from .bulk import bulk_insert_rows, load_csv, load_json, export_csv, export_json

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
    "set_default_backend",
    "get_default_backend",
    "get_backend",
    "smart_insert",
    "infer_type",
    "create_table_from_data",
    "suggest_column_types",
    "bulk_insert_rows",
    "load_csv",
    "load_json",
    "export_csv",
    "export_json",
]
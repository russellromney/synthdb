"""Utility functions for SynthDB."""

import sqlite3
from .backends import get_backend
from .config import config


def query_view(view_name, where_clause=None, db_path: str = 'db.db', backend_name: str = None):
    """Run a query on a view with optional WHERE clause"""
    # Get the appropriate backend
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    backend = get_backend(backend_to_use)
    
    db = backend.connect(db_path)
    
    # Build the query
    query = f"SELECT * FROM {view_name}"
    if where_clause:
        query += f" WHERE {where_clause}"
    
    try:
        cur = backend.execute(db, query)
        results = backend.fetchall(cur)
        return results
    finally:
        backend.close(db)




def list_tables(db_path: str = 'db.db', backend_name: str = None):
    """List all tables in the database"""
    # Get the appropriate backend
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    backend = get_backend(backend_to_use)
    
    db = backend.connect(db_path)
    
    try:
        cur = backend.execute(db, """
            SELECT id, name, created_at 
            FROM table_definitions 
            WHERE deleted_at IS NULL 
            ORDER BY created_at
        """)
        tables = backend.fetchall(cur)
        return tables
    finally:
        backend.close(db)


def list_columns(table_name, include_deleted=False, db_path: str = 'db.db', backend_name: str = None):
    """
    List columns for a specific table.
    
    Args:
        table_name: Name of the table
        include_deleted: If True, include soft-deleted columns
        db_path: Database path
        backend_name: Backend to use
        
    Returns:
        List of column dictionaries with id, name, data_type, created_at, and deleted_at
    """
    # Get the appropriate backend
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    backend = get_backend(backend_to_use)
    
    db = backend.connect(db_path)
    
    try:
        # Get table ID
        cur = backend.execute(db, "SELECT id FROM table_definitions WHERE name = ? AND deleted_at IS NULL", (table_name,))
        result = backend.fetchone(cur)
        if not result:
            raise ValueError(f"Table '{table_name}' not found")
        table_id = result['id']
        
        if include_deleted:
            # Include all columns, even deleted ones
            cur = backend.execute(db, """
                SELECT id, name, data_type, created_at, deleted_at
                FROM column_definitions 
                WHERE table_id = ?
                ORDER BY id
            """, (table_id,))
        else:
            # Only non-deleted columns
            cur = backend.execute(db, """
                SELECT id, name, data_type, created_at, deleted_at
                FROM column_definitions 
                WHERE table_id = ? AND deleted_at IS NULL 
                ORDER BY id
            """, (table_id,))
        columns = backend.fetchall(cur)
        return columns
    finally:
        backend.close(db)
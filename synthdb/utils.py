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
        backend.close(db)
        return results
    except Exception as e:
        backend.close(db)
        raise e


def export_table_structure(table_name, db_path: str = 'db.db', backend_name: str = None):
    """Export the structure of a table in SQLite CREATE TABLE format"""
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
        
        # Get columns for this table
        cur = backend.execute(db, """
            SELECT name, data_type FROM column_definitions 
            WHERE table_id = ? AND deleted_at IS NULL
            ORDER BY id
        """, (table_id,))
        columns = backend.fetchall(cur)
        
    finally:
        backend.close(db)
    
    if not columns:
        return f"-- Table '{table_name}' has no columns"
    
    # Build CREATE TABLE statement
    column_defs = []
    for col in columns:
        col_name = col['name']
        data_type = col['data_type']
        # Map our internal types to SQLite types
        sqlite_type = {
            'text': 'TEXT',
            'integer': 'INTEGER', 
            'real': 'REAL',
            'boolean': 'INTEGER',  # SQLite doesn't have native boolean
            'json': 'TEXT',
            'timestamp': 'TIMESTAMP'
        }.get(data_type, 'TEXT')
        
        column_defs.append(f"    {col_name} {sqlite_type}")
    
    create_statement = f"CREATE TABLE {table_name} (\n" + ",\n".join(column_defs) + "\n);"
    return create_statement


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


def list_columns(table_name, db_path: str = 'db.db', backend_name: str = None):
    """List all columns for a specific table"""
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
        
        cur = backend.execute(db, """
            SELECT id, name, data_type, created_at 
            FROM column_definitions 
            WHERE table_id = ? AND deleted_at IS NULL 
            ORDER BY id
        """, (table_id,))
        columns = backend.fetchall(cur)
        return columns
    finally:
        backend.close(db)
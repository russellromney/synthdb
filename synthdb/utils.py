"""Utility functions for SynthDB."""

import sqlite3


def query_view(view_name, where_clause=None, db_path: str = 'db.db'):
    """Run a query on a view with optional WHERE clause"""
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    
    # Build the query
    query = f"SELECT * FROM {view_name}"
    if where_clause:
        query += f" WHERE {where_clause}"
    
    try:
        results = cur.execute(query).fetchall()
        columns = [desc[0] for desc in cur.description]
        db.close()
        return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        db.close()
        raise e


def export_table_structure(table_name, db_path: str = 'db.db'):
    """Export the structure of a table in SQLite CREATE TABLE format"""
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    
    # Get table ID
    cur.execute("SELECT id FROM table_definitions WHERE name = ? AND deleted_at IS NULL", (table_name,))
    result = cur.fetchone()
    if not result:
        raise ValueError(f"Table '{table_name}' not found")
    table_id = result[0]
    
    # Get columns for this table
    cur.execute("""
        SELECT name, data_type FROM column_definitions 
        WHERE table_id = ? AND deleted_at IS NULL
        ORDER BY id
    """, (table_id,))
    columns = cur.fetchall()
    
    db.close()
    
    if not columns:
        return f"-- Table '{table_name}' has no columns"
    
    # Build CREATE TABLE statement
    column_defs = []
    for col_name, data_type in columns:
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


def list_tables(db_path: str = 'db.db'):
    """List all tables in the database"""
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    
    cur.execute("""
        SELECT id, name, created_at 
        FROM table_definitions 
        WHERE deleted_at IS NULL 
        ORDER BY created_at
    """)
    tables = cur.fetchall()
    db.close()
    
    return [{"id": t[0], "name": t[1], "created_at": t[2]} for t in tables]


def list_columns(table_name, db_path: str = 'db.db'):
    """List all columns for a specific table"""
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    
    # Get table ID
    cur.execute("SELECT id FROM table_definitions WHERE name = ? AND deleted_at IS NULL", (table_name,))
    result = cur.fetchone()
    if not result:
        raise ValueError(f"Table '{table_name}' not found")
    table_id = result[0]
    
    cur.execute("""
        SELECT id, name, data_type, created_at 
        FROM column_definitions 
        WHERE table_id = ? AND deleted_at IS NULL 
        ORDER BY id
    """, (table_id,))
    columns = cur.fetchall()
    db.close()
    
    return [{"id": c[0], "name": c[1], "data_type": c[2], "created_at": c[3]} for c in columns]
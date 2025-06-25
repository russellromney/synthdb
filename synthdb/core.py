"""Core EAV operations for SynthDB."""

import sqlite3
import json
from .types import get_type_table_name


def insert_typed_value(row_id, table_id, column_id, value, data_type, db_path: str = 'db.db'):
    """Insert a value into the appropriate type-specific table"""
    table_name = get_type_table_name(data_type)
    history_table_name = get_type_table_name(data_type, is_history=True)
    
    # Convert value to appropriate type
    if data_type == 'boolean':
        value = 1 if value else 0
    elif data_type == 'json':
        value = json.dumps(value) if not isinstance(value, str) else value
    
    db = sqlite3.connect(db_path)
    try:
        cur = db.cursor()
        
        # Insert into main table
        statement = f"""
            INSERT INTO {table_name} (row_id, table_id, column_id, value)
            VALUES (?, ?, ?, ?)
        """
        cur.execute(statement, (row_id, table_id, column_id, value))
        
        # Insert into history table
        history_statement = f"""
            INSERT INTO {history_table_name} (row_id, table_id, column_id, value)
            VALUES (?, ?, ?, ?)
        """
        cur.execute(history_statement, (row_id, table_id, column_id, value))
        
        # Commit the transaction
        db.commit()
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise e
    finally:
        db.close()


def create_table(table_name, db_path: str = 'db.db'):
    """Create a new table definition"""
    db = sqlite3.connect(db_path)
    try:
        cur = db.cursor()
        
        # Get the next table ID
        cur.execute("SELECT COALESCE(MAX(id), -1) + 1 FROM table_definitions")
        table_id = cur.fetchone()[0]
        
        # Insert the new table
        cur.execute("""
            INSERT INTO table_definitions (id, version, name)
            VALUES (?, 0, ?)
        """, (table_id, table_name))
        
        # Commit the transaction
        db.commit()
        
        # Create initial view for the table (even if no columns yet)
        from .views import create_table_views
        create_table_views(db_path)
        return table_id
        
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise e
    finally:
        db.close()


def add_column(table_name, column_name, data_type, db_path: str = 'db.db'):
    """Add a column to an existing table"""
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    
    # Get table ID
    cur.execute("SELECT id FROM table_definitions WHERE name = ? AND deleted_at IS NULL", (table_name,))
    result = cur.fetchone()
    if not result:
        raise ValueError(f"Table '{table_name}' not found")
    table_id = result[0]
    
    # Get next column ID
    cur.execute("SELECT COALESCE(MAX(id), -1) + 1 FROM column_definitions")
    column_id = cur.fetchone()[0]
    
    # Insert the new column
    cur.execute("""
        INSERT INTO column_definitions (id, table_id, version, name, data_type)
        VALUES (?, ?, 0, ?, ?)
    """, (column_id, table_id, column_name, data_type))
    
    db.commit()
    db.close()
    
    # Recreate views to include the new column
    from .views import create_table_views
    create_table_views(db_path)
    return column_id
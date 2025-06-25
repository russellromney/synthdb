"""Core database operations for SynthDB."""

import sqlite3
import json
from .types import get_type_table_name
from .backends import get_backend, detect_backend_from_connection, parse_connection_string
from .config import config


def insert_typed_value(row_id, table_id, column_id, value, data_type, db_path: str = 'db.db', 
                      backend_name: str = None, backend=None, connection=None):
    """
    Insert a value into the appropriate type-specific table with ACID guarantees.
    
    Args:
        row_id: Row identifier
        table_id: Table identifier  
        column_id: Column identifier
        value: Value to insert
        data_type: Data type for value storage
        db_path: Database path (ignored if backend/connection provided)
        backend_name: Backend name (ignored if backend/connection provided)
        backend: Optional backend instance for transaction reuse
        connection: Optional connection for transaction reuse
    """
    table_name = get_type_table_name(data_type)
    history_table_name = get_type_table_name(data_type, is_history=True)
    
    # Convert value to appropriate type
    if data_type == 'boolean':
        value = 1 if value else 0
    elif data_type == 'json':
        value = json.dumps(value) if not isinstance(value, str) else value
    
    # Use provided backend/connection or create new transaction context
    if backend and connection:
        # Use existing transaction context
        _insert_with_connection(backend, connection, table_name, history_table_name, 
                              row_id, table_id, column_id, value)
    else:
        # Create new transaction context
        from .transactions import transaction_context
        
        backend_to_use = backend_name or config.get_backend_for_path(db_path)
        connection_info = db_path
        
        with transaction_context(connection_info, backend_to_use) as (txn_backend, txn_connection):
            _insert_with_connection(txn_backend, txn_connection, table_name, history_table_name,
                                  row_id, table_id, column_id, value)


def _insert_with_connection(backend, connection, table_name, history_table_name, 
                          row_id, table_id, column_id, value):
    """
    Perform atomic insert into both main and history tables using shared connection.
    
    This ensures ACID guarantees - both inserts succeed or both fail.
    """
    # Insert into main table
    statement = f"""
        INSERT INTO {table_name} (row_id, table_id, column_id, value)
        VALUES (?, ?, ?, ?)
    """
    backend.execute(connection, statement, (row_id, table_id, column_id, value))
    
    # Insert into history table (same transaction)
    history_statement = f"""
        INSERT INTO {history_table_name} (row_id, table_id, column_id, value)
        VALUES (?, ?, ?, ?)
    """
    backend.execute(connection, history_statement, (row_id, table_id, column_id, value))
    
    # Note: No commit here - handled by transaction context manager


def create_table(table_name, db_path: str = 'db.db', backend_name: str = None):
    """Create a new table definition"""
    # Get the appropriate backend
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    backend = get_backend(backend_to_use)
    
    db = backend.connect(db_path)
    try:
        # Get the next table ID
        cur = backend.execute(db, "SELECT COALESCE(MAX(id), -1) + 1 as next_id FROM table_definitions")
        result = backend.fetchone(cur)
        table_id = result['next_id'] if result else 0
        
        # Insert the new table
        backend.execute(db, """
            INSERT INTO table_definitions (id, version, name)
            VALUES (?, 0, ?)
        """, (table_id, table_name))
        
        # Commit the transaction
        backend.commit(db)
        
        # Create initial view for the table (even if no columns yet)
        from .views import create_table_views
        create_table_views(db_path, backend_name=backend_to_use)
        return table_id
        
    except Exception as e:
        # Rollback on error
        backend.rollback(db)
        raise e
    finally:
        backend.close(db)


def add_column(table_name, column_name, data_type, db_path: str = 'db.db', backend_name: str = None,
              backend=None, connection=None):
    """
    Add a column to an existing table with transaction support.
    
    Args:
        table_name: Name of the table
        column_name: Name of the new column  
        data_type: Data type for the column
        db_path: Database path (ignored if backend/connection provided)
        backend_name: Backend name (ignored if backend/connection provided)
        backend: Optional backend instance for transaction reuse
        connection: Optional connection for transaction reuse
    """
    # Use provided backend/connection or create new transaction context
    if backend and connection:
        # Use existing transaction context
        return _add_column_with_connection(backend, connection, table_name, column_name, data_type, db_path, backend_name)
    else:
        # Create new transaction context
        from .transactions import transaction_context
        
        backend_to_use = backend_name or config.get_backend_for_path(db_path)
        connection_info = db_path
        
        with transaction_context(connection_info, backend_to_use) as (txn_backend, txn_connection):
            return _add_column_with_connection(txn_backend, txn_connection, table_name, column_name, data_type, db_path, backend_name)


def _add_column_with_connection(backend, connection, table_name, column_name, data_type, db_path, backend_name):
    """Add a column using provided backend and connection."""
    # Get table ID
    cur = backend.execute(connection, "SELECT id FROM table_definitions WHERE name = ? AND deleted_at IS NULL", (table_name,))
    result = backend.fetchone(cur)
    if not result:
        raise ValueError(f"Table '{table_name}' not found")
    table_id = result['id']
    
    # Get next column ID
    cur = backend.execute(connection, "SELECT COALESCE(MAX(id), -1) + 1 as next_id FROM column_definitions")
    result = backend.fetchone(cur)
    column_id = result['next_id'] if result else 0
    
    # Insert the new column
    backend.execute(connection, """
        INSERT INTO column_definitions (id, table_id, version, name, data_type)
        VALUES (?, ?, 0, ?, ?)
    """, (column_id, table_id, column_name, data_type))
    
    # Note: Views recreation should be handled outside transaction for better performance
    # The transaction context manager will handle commit
    
    return column_id
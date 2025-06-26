"""Core database operations for SynthDB."""

import sqlite3
import json
from .types import get_type_table_name
from .backends import get_backend, detect_backend_from_connection, parse_connection_string
from .config import config
from .constants import validate_column_name, validate_table_name


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


def upsert_typed_value(row_id, table_id, column_id, value, data_type, 
                      backend=None, connection=None):
    """
    Insert or update a value in the appropriate type-specific table.
    
    This function handles both inserts and updates by soft-deleting existing values
    before inserting the new value.
    
    Args:
        row_id: Row identifier
        table_id: Table identifier  
        column_id: Column identifier
        value: Value to insert/update
        data_type: Data type for value storage
        backend: Backend instance for transaction reuse
        connection: Connection for transaction reuse
    """
    table_name = get_type_table_name(data_type)
    history_table_name = get_type_table_name(data_type, is_history=True)
    
    # Convert value to appropriate type
    if data_type == 'boolean':
        value = 1 if value else 0
    elif data_type == 'json':
        value = json.dumps(value) if not isinstance(value, str) else value
    
    # Soft delete existing values for this cell
    soft_delete_statement = f"""
        UPDATE {table_name} 
        SET deleted_at = CURRENT_TIMESTAMP 
        WHERE row_id = ? AND table_id = ? AND column_id = ? AND deleted_at IS NULL
    """
    backend.execute(connection, soft_delete_statement, (row_id, table_id, column_id))
    
    # Insert the new value
    insert_statement = f"""
        INSERT INTO {table_name} (row_id, table_id, column_id, value)
        VALUES (?, ?, ?, ?)
    """
    backend.execute(connection, insert_statement, (row_id, table_id, column_id, value))
    
    # Insert into history table (same transaction)
    history_statement = f"""
        INSERT INTO {history_table_name} (row_id, table_id, column_id, value)
        VALUES (?, ?, ?, ?)
    """
    backend.execute(connection, history_statement, (row_id, table_id, column_id, value))


def create_table(table_name, db_path: str = 'db.db', backend_name: str = None):
    """Create a new table definition"""
    # Validate table name is not protected
    validate_table_name(table_name)
    
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
    # Validate column name is not protected
    validate_column_name(column_name)
    
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


def copy_column_structure(source_table, source_column, target_table, target_column, 
                         db_path: str = 'db.db', backend_name: str = None):
    """
    Copy column structure (metadata) without data.
    
    Args:
        source_table: Name of source table
        source_column: Name of source column
        target_table: Name of target table
        target_column: Name of new column in target table
        db_path: Database path
        backend_name: Backend name
        
    Returns:
        ID of the newly created column
    """
    from .transactions import transaction_context
    
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    
    with transaction_context(db_path, backend_to_use) as (backend, connection):
        # Get source column metadata
        cur = backend.execute(connection, """
            SELECT cd.data_type 
            FROM column_definitions cd
            JOIN table_definitions td ON cd.table_id = td.id
            WHERE td.name = ? AND cd.name = ? 
            AND td.deleted_at IS NULL AND cd.deleted_at IS NULL
        """, (source_table, source_column))
        
        result = backend.fetchone(cur)
        if not result:
            raise ValueError(f"Column '{source_column}' not found in table '{source_table}'")
        
        data_type = result['data_type']
        
        # Add new column with same type
        column_id = _add_column_with_connection(backend, connection, target_table, 
                                              target_column, data_type, db_path, backend_to_use)
    
    # Recreate views after transaction completes
    from .views import create_table_views
    create_table_views(db_path, backend_name=backend_to_use)
    
    return column_id


def copy_column_with_data(source_table, source_column, target_table, target_column,
                         db_path: str = 'db.db', backend_name: str = None):
    """
    Copy column structure and all data.
    
    Args:
        source_table: Name of source table
        source_column: Name of source column  
        target_table: Name of target table
        target_column: Name of new column in target table
        db_path: Database path
        backend_name: Backend name
        
    Returns:
        ID of the newly created column
    """
    from .transactions import transaction_context
    
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    
    with transaction_context(db_path, backend_to_use) as (backend, connection):
        # Get source column metadata
        cur = backend.execute(connection, """
            SELECT cd.id as column_id, cd.data_type, td.id as table_id
            FROM column_definitions cd
            JOIN table_definitions td ON cd.table_id = td.id
            WHERE td.name = ? AND cd.name = ? 
            AND td.deleted_at IS NULL AND cd.deleted_at IS NULL
        """, (source_table, source_column))
        
        result = backend.fetchone(cur)
        if not result:
            raise ValueError(f"Column '{source_column}' not found in table '{source_table}'")
        
        source_column_id = result['column_id']
        source_table_id = result['table_id']
        data_type = result['data_type']
        
        # Get target table ID
        cur = backend.execute(connection, 
            "SELECT id FROM table_definitions WHERE name = ? AND deleted_at IS NULL", 
            (target_table,))
        target_result = backend.fetchone(cur)
        if not target_result:
            raise ValueError(f"Table '{target_table}' not found")
        target_table_id = target_result['id']
        
        # Add new column
        new_column_id = _add_column_with_connection(backend, connection, target_table, 
                                                   target_column, data_type, db_path, backend_to_use)
        
        # Copy all values from source column to target column
        type_table = get_type_table_name(data_type)
        history_table = get_type_table_name(data_type, is_history=True)
        
        # Copy main values
        backend.execute(connection, f"""
            INSERT INTO {type_table} (row_id, table_id, column_id, value)
            SELECT row_id, ?, ?, value
            FROM {type_table}
            WHERE table_id = ? AND column_id = ?
        """, (target_table_id, new_column_id, source_table_id, source_column_id))
        
        # Copy history values
        backend.execute(connection, f"""
            INSERT INTO {history_table} (row_id, table_id, column_id, value, created_at)
            SELECT row_id, ?, ?, value, created_at
            FROM {history_table}
            WHERE table_id = ? AND column_id = ?
        """, (target_table_id, new_column_id, source_table_id, source_column_id))
    
    # Recreate views after transaction completes
    from .views import create_table_views
    create_table_views(db_path, backend_name=backend_to_use)
    
    return new_column_id
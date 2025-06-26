"""
Modern, intuitive API for SynthDB operations.

This module provides the core API functions used by the Connection class.
"""

from typing import Dict, Any, Union, Optional, List
from .core import insert_typed_value, add_column as _add_column
from .utils import list_tables, list_columns, query_view
from .inference import infer_type
from .transactions import transaction_context


def _row_id_exists(backend, connection, table_id: int, row_id: int) -> bool:
    """Check if a row ID already exists in any type table for the given table."""
    type_tables = ['text_values', 'integer_values', 'real_values', 
                   'boolean_values', 'json_values', 'timestamp_values']
    
    for type_table in type_tables:
        try:
            cur = backend.execute(connection, 
                f"SELECT 1 FROM {type_table} WHERE table_id = ? AND row_id = ? LIMIT 1", 
                (table_id, row_id))
            result = backend.fetchone(cur)
            if result:
                return True
        except Exception:
            # Table might not exist yet, continue checking others
            continue
    
    return False


def _get_next_row_id(backend, connection, table_id: int) -> int:
    """Generate a new row ID using the database sequence table."""
    # Use RETURNING clause if supported for optimal performance
    if backend.supports_returning():
        cur = backend.execute(connection,
            "INSERT INTO row_id_sequence (table_id) VALUES (?) RETURNING id",
            (table_id,))
        result = backend.fetchone(cur)
        return result['id']
    else:
        # Fallback to INSERT + lastrowid
        cur = backend.execute(connection, 
            "INSERT INTO row_id_sequence (table_id) VALUES (?)", 
            (table_id,))
        return cur.lastrowid


def insert(table_name: str, data: Union[Dict[str, Any], str], value: Any = None, 
          connection_info: str = 'db.db', backend_name: str = None, 
          force_type: str = None, row_id: int = None) -> int:
    """
    Insert data into a table with automatic or explicit ID management and type inference.
    
    Args:
        table_name: Name of the table
        data: Dictionary of column->value pairs, OR column name (if value provided)
        value: Value to insert (if data is a column name)
        connection_info: Database connection
        backend_name: Backend to use
        force_type: Override automatic type inference
        row_id: Explicit row ID (if None, auto-generates next available ID)
        
    Returns:
        The row ID (auto-generated or explicitly provided)
        
    Raises:
        ValueError: If table/column not found, type conversion fails, or duplicate ID
        TypeError: If data types cannot be converted
        
    Examples:
        # Auto-generated ID
        row_id = insert("users", {"name": "John", "age": 25})
        
        # Explicit ID
        insert("users", {"name": "Jane"}, row_id=100)
        
        # Single column
        insert("users", "email", "john@example.com")
        
        # Force specific type
        insert("users", "age", "25", force_type="text")
    """
    # Handle single column insert
    if isinstance(data, str) and value is not None:
        column_name = data
        column_data = {column_name: value}
    elif isinstance(data, dict):
        column_data = data
    else:
        raise ValueError("data must be dict or column name with value")
    
    # Get table and column information
    tables = list_tables(connection_info, backend_name)
    table_info = next((t for t in tables if t['name'] == table_name), None)
    if not table_info:
        raise ValueError(f"Table '{table_name}' not found")
    
    table_id = table_info['id']
    columns = list_columns(table_name, connection_info, backend_name)
    column_lookup = {col['name']: col for col in columns}
    
    # Handle row ID - explicit or auto-generated
    with transaction_context(connection_info, backend_name) as (backend, connection):
        if row_id is not None:
            # Validate explicit row ID doesn't already exist (for new row creation)
            if _row_id_exists(backend, connection, table_id, row_id):
                raise ValueError(f"Row ID {row_id} already exists in table '{table_name}'")
            final_row_id = row_id
        else:
            # Auto-generate next available row ID
            final_row_id = _get_next_row_id(backend, connection, table_id)
        
        # Insert each column value with enhanced error handling
        for col_name, col_value in column_data.items():
            if col_name not in column_lookup:
                available_cols = list(column_lookup.keys())
                raise ValueError(f"Column '{col_name}' not found in table '{table_name}'. "
                               f"Available columns: {available_cols}")
            
            column_info = column_lookup[col_name]
            column_id = column_info['id']
            
            # Use force_type if provided, otherwise use column's defined type
            if force_type:
                data_type = force_type
            else:
                data_type = column_info['data_type']
            
            try:
                # Insert the value using existing function with transaction context
                insert_typed_value(
                    final_row_id, table_id, column_id, col_value, data_type,
                    backend=backend, connection=connection
                )
            except (ValueError, TypeError) as e:
                # Enhanced error messages for type conversion failures
                raise TypeError(f"Cannot convert value '{col_value}' to type '{data_type}' "
                              f"for column '{col_name}': {e}") from e
            except Exception as e:
                # Wrap unexpected errors with context
                raise ValueError(f"Failed to insert value '{col_value}' into column '{col_name}': {e}") from e
    
    return final_row_id


def query(table_name: str, where: str = None, connection_info: str = 'db.db', 
         backend_name: str = None) -> List[Dict[str, Any]]:
    """
    Query data from a table.
    
    Args:
        table_name: Name of the table to query
        where: Optional WHERE clause
        connection_info: Database connection
        backend_name: Backend to use
        
    Returns:
        List of dictionaries representing rows
        
    Examples:
        # Get all rows
        rows = query("users")
        
        # Filter rows
        rows = query("users", "age > 25")
    """
    return query_view(table_name, where, connection_info, backend_name)


def add_columns(table_name: str, columns: Dict[str, Union[str, Any]], 
               connection_info: str = 'db.db', backend_name: str = None) -> Dict[str, int]:
    """
    Add multiple columns to a table at once.
    
    Args:
        table_name: Name of the table
        columns: Dictionary of column_name -> type_or_sample_value
        connection_info: Database connection
        backend_name: Backend to use
        
    Returns:
        Dictionary mapping column names to their IDs
        
    Examples:
        # Explicit types
        ids = add_columns("users", {
            "email": "text",
            "created_at": "timestamp",
            "metadata": "json"
        })
        
        # Inferred types from sample values
        ids = add_columns("users", {
            "email": "user@example.com",      # -> text
            "age": 25,                        # -> integer
            "active": True,                   # -> boolean
            "created_at": "2023-12-25"        # -> timestamp
        })
    """
    valid_types = {"text", "integer", "real", "boolean", "json", "timestamp"}
    column_ids = {}
    
    with transaction_context(connection_info, backend_name) as (backend, connection):
        for col_name, type_or_value in columns.items():
            # Determine if it's a type name or sample value
            if isinstance(type_or_value, str) and type_or_value in valid_types:
                # It's an explicit type
                data_type = type_or_value
            else:
                # It's a sample value - infer the type
                data_type, _ = infer_type(type_or_value)
            
            # Add the column using transaction context
            column_id = _add_column(
                table_name, col_name, data_type, connection_info, backend_name,
                backend=backend, connection=connection
            )
            column_ids[col_name] = column_id
    
    # Recreate views to include new columns
    from .views import create_table_views
    create_table_views(connection_info, backend_name)
    
    return column_ids


def upsert(table_name: str, data: Dict[str, Any], key_columns: List[str],
          connection_info: str = 'db.db', backend_name: str = None, row_id: int = None) -> int:
    """
    Insert or update data based on key columns.
    
    Args:
        table_name: Name of the table
        data: Column data to insert/update
        key_columns: Columns to use for matching existing rows
        connection_info: Database connection  
        backend_name: Backend to use
        row_id: Explicit row ID for new inserts (ignored for updates)
        
    Returns:
        Row ID of inserted or updated row
        
    Examples:
        # Insert new user or update if email exists
        row_id = upsert("users", 
            {"name": "John", "email": "john@example.com", "age": 25},
            key_columns=["email"]
        )
        
        # Insert with explicit ID if not found
        upsert("users", {"name": "Jane"}, key_columns=["email"], row_id=100)
    """
    # Build WHERE clause from key columns
    key_conditions = []
    for key_col in key_columns:
        if key_col not in data:
            raise ValueError(f"Key column '{key_col}' not found in data")
        key_conditions.append(f"{key_col} = '{data[key_col]}'")
    
    where_clause = " AND ".join(key_conditions)
    
    # Check if row exists
    existing_rows = query(table_name, where_clause, connection_info, backend_name)
    
    if existing_rows:
        # Update existing row
        existing_row = existing_rows[0]
        row_id = existing_row['row_id']
        
        # Update each column (excluding key columns if unchanged)
        with transaction_context(connection_info, backend_name) as (backend, connection):
            tables = list_tables(connection_info, backend_name)
            table_info = next((t for t in tables if t['name'] == table_name), None)
            table_id = table_info['id']
            
            columns = list_columns(table_name, connection_info, backend_name)
            column_lookup = {col['name']: col for col in columns}
            
            for col_name, col_value in data.items():
                if col_name in column_lookup:
                    column_info = column_lookup[col_name]
                    column_id = column_info['id']
                    data_type = column_info['data_type']
                    
                    insert_typed_value(
                        row_id, table_id, column_id, col_value, data_type,
                        backend=backend, connection=connection
                    )
        
        return row_id
    else:
        # Insert new row (with optional explicit ID)
        return insert(table_name, data, connection_info=connection_info, backend_name=backend_name, row_id=row_id)



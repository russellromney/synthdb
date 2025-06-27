"""
Modern, intuitive API for SynthDB operations.

This module provides the core API functions used by the Connection class.
"""

from typing import Dict, Any, Union, List
from .core import insert_typed_value, add_column as _add_column, get_table_id, get_table_columns, delete_row_metadata, get_row_metadata
from .utils import list_tables, list_columns, query_view
from .inference import infer_type
from .transactions import transaction_context
from .config import config



def _column_value_exists(backend, connection, table_id: int, row_id: Union[str, int], column_id: int) -> bool:
    """Check if a specific (row_id, column_id) combination already has a value."""
    type_tables = ['text_values', 'integer_values', 'real_values', 'timestamp_values']
    
    for type_table in type_tables:
        try:
            cur = backend.execute(connection, 
                f"SELECT 1 FROM {type_table} WHERE table_id = ? AND row_id = ? AND column_id = ? AND deleted_at IS NULL LIMIT 1", 
                (table_id, str(row_id), column_id))
            result = backend.fetchone(cur)
            if result:
                return True
        except Exception:
            # Table might not exist yet, continue checking others
            continue
    
    return False


def _get_next_row_id() -> str:
    """Generate a new globally unique row ID using UUID4."""
    import uuid
    return str(uuid.uuid4())


def insert(table_name: str, data: Union[Dict[str, Any], str], value: Any = None, 
          connection_info: str = 'db.db', backend_name: str = None, 
          force_type: str = None, row_id: str = None) -> str:
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
        insert("users", {"name": "Jane"}, row_id="100")
        
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
    columns = list_columns(table_name, False, connection_info, backend_name)
    column_lookup = {col['name']: col for col in columns}
    
    # Handle row ID - explicit or auto-generated
    with transaction_context(connection_info, backend_name) as (backend, connection):
        if row_id is not None:
            # Validate that row_id is a string
            if not isinstance(row_id, str):
                raise ValueError(f"row_id must be a string, got {type(row_id).__name__}: {row_id}")
            final_row_id = row_id
        else:
            # Auto-generate next available row ID
            final_row_id = _get_next_row_id()
        
        # Insert each column value with enhanced error handling
        for col_name, col_value in column_data.items():
            if col_name not in column_lookup:
                available_cols = list(column_lookup.keys())
                raise ValueError(f"Column '{col_name}' not found in table '{table_name}'. "
                               f"Available columns: {available_cols}")
            
            column_info = column_lookup[col_name]
            column_id = column_info['id']
            
            # Check if this specific (row_id, column_id) combination already has a value
            if row_id is not None:
                # For explicit row_id, check if this column already has a value
                existing_check = _column_value_exists(backend, connection, table_id, final_row_id, column_id)
                if existing_check:
                    raise ValueError(f"Row ID {final_row_id} already has a value for column '{col_name}' in table '{table_name}'")
            
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
            "age": "integer", 
            "created_at": "timestamp"
        })
        
        # Inferred types from sample values
        ids = add_columns("users", {
            "email": "user@example.com",      # -> text
            "age": 25,                        # -> integer
            "score": 98.5,                    # -> real
            "created_at": "2023-12-25"        # -> timestamp
        })
    """
    valid_types = {"text", "integer", "real", "timestamp"}
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


def upsert(table_name: str, data: Dict[str, Any], row_id: str,
          connection_info: str = 'db.db', backend_name: str = None) -> str:
    """
    Insert or update data for a specific row_id.
    
    If the row_id exists, updates the existing row with new data.
    If the row_id doesn't exist, creates a new row with that row_id.
    
    Args:
        table_name: Name of the table
        data: Column data to insert/update
        row_id: Specific row ID to insert or update
        connection_info: Database connection  
        backend_name: Backend to use
        
    Returns:
        The row_id that was inserted or updated
        
    Examples:
        # Update existing row or create new row with ID 100
        upsert("users", {"name": "Jane", "age": 30}, row_id="100")
        
        # Update row 1 with new data
        upsert("users", {"name": "John Updated", "email": "john.new@example.com"}, row_id="1")
    """
    # Validate that row_id is a string
    if not isinstance(row_id, str):
        raise ValueError(f"row_id must be a string, got {type(row_id).__name__}: {row_id}")
    
    # Check if the specific row_id exists
    row_id_str = row_id
    existing_rows = query(table_name, f"row_id = '{row_id_str}'", connection_info, backend_name)
    
    if existing_rows:
        # Update existing row with specified row_id
        with transaction_context(connection_info, backend_name) as (backend, connection):
            tables = list_tables(connection_info, backend_name)
            table_info = next((t for t in tables if t['name'] == table_name), None)
            table_id = table_info['id']
            
            columns = list_columns(table_name, False, connection_info, backend_name)
            column_lookup = {col['name']: col for col in columns}
            
            for col_name, col_value in data.items():
                if col_name in column_lookup:
                    column_info = column_lookup[col_name]
                    column_id = column_info['id']
                    data_type = column_info['data_type']
                    
                    from .core import upsert_typed_value
                    upsert_typed_value(
                        row_id_str, table_id, column_id, col_value, data_type,
                        backend=backend, connection=connection
                    )
        
        return row_id_str
    else:
        # Insert new row with the specified row_id
        return insert(table_name, data, connection_info=connection_info, backend_name=backend_name, row_id=row_id)


def copy_column(source_table: str, source_column: str, target_table: str, target_column: str,
               copy_data: bool = False, connection_info: str = 'db.db', backend_name: str = None) -> int:
    """
    Copy a column from one table to another, optionally including data.
    
    Args:
        source_table: Name of source table
        source_column: Name of source column
        target_table: Name of target table  
        target_column: Name of new column in target table
        copy_data: If True, copy data; if False, only copy structure
        connection_info: Database connection
        backend_name: Backend to use
        
    Returns:
        ID of the newly created column
        
    Examples:
        # Copy structure only (fast)
        copy_column("users", "email", "customers", "contact_email")
        
        # Copy structure and data (slower)
        copy_column("users", "email", "customers", "contact_email", copy_data=True)
        
        # Copy within same table
        copy_column("users", "email", "users", "backup_email", copy_data=True)
    """
    from .core import copy_column_structure, copy_column_with_data
    
    if copy_data:
        return copy_column_with_data(source_table, source_column, target_table, target_column,
                                   connection_info, backend_name)
    else:
        return copy_column_structure(source_table, source_column, target_table, target_column,
                                   connection_info, backend_name)


def copy_table(source_table: str, target_table: str, copy_data: bool = False,
              connection_info: str = 'db.db', backend_name: str = None) -> int:
    """
    Copy a table's structure and optionally its data.
    
    Creates a new table that is a copy of an existing table. Can copy just the
    structure (table and column definitions) or include all data as well.
    When copying data, new row IDs are generated to avoid conflicts.
    
    Args:
        source_table: Name of table to copy from
        target_table: Name of new table to create
        copy_data: If True, copy all data; if False, structure only
        connection_info: Database connection
        backend_name: Backend to use
        
    Returns:
        ID of the newly created table
        
    Raises:
        ValueError: If source table doesn't exist or target already exists
        
    Examples:
        # Copy structure only (fast)
        table_id = copy_table("users", "users_template")
        
        # Copy structure and all data (slower)
        table_id = copy_table("users", "users_backup", copy_data=True)
        
        # Create archive copy
        table_id = copy_table("orders_2023", "orders_2023_archive", copy_data=True)
    """
    from .core import copy_table as _copy_table
    
    return _copy_table(source_table, target_table, copy_data,
                      connection_info, backend_name)


def rename_column(table_name: str, old_column_name: str, new_column_name: str,
                  connection_info: str = 'db.db', backend_name: str = None) -> None:
    """
    Rename a column in a table.
    
    Args:
        table_name: Name of the table
        old_column_name: Current column name
        new_column_name: New column name
        connection_info: Database connection
        backend_name: Backend to use
        
    Raises:
        ValueError: If table/column not found or new name already exists
        
    Examples:
        # Rename a column
        rename_column("users", "email", "email_address")
        
        # Fix typo in column name
        rename_column("products", "descrption", "description")
    """
    from .core import rename_column as _rename_column
    
    _rename_column(table_name, old_column_name, new_column_name,
                   connection_info, backend_name)


def delete_column(table_name: str, column_name: str, hard_delete: bool = False,
                  connection_info: str = 'db.db', backend_name: str = None) -> None:
    """
    Delete a column from a table.
    
    Args:
        table_name: Name of the table
        column_name: Name of the column to delete
        hard_delete: If True, permanently delete all column data; if False, soft delete
        connection_info: Database connection
        backend_name: Backend to use
        
    Raises:
        ValueError: If table/column not found
        
    Examples:
        # Soft delete (preserves data)
        delete_column("users", "deprecated_field")
        
        # Hard delete (permanently removes data)
        delete_column("products", "old_price", hard_delete=True)
        
        # Hard delete a previously soft-deleted column
        delete_column("users", "removed_field", hard_delete=True)
    """
    from .core import delete_column as _delete_column
    
    _delete_column(table_name, column_name, hard_delete, connection_info, backend_name)


def delete_table(table_name: str, hard_delete: bool = False,
                 connection_info: str = 'db.db', backend_name: str = None) -> None:
    """
    Delete a table and all its associated data.
    
    Args:
        table_name: Name of the table to delete
        hard_delete: If True, permanently delete all data; if False, soft delete
        connection_info: Database connection
        backend_name: Backend to use
        
    Raises:
        ValueError: If table not found
        
    Examples:
        # Soft delete (can be recovered)
        delete_table("old_users")
        
        # Hard delete (permanent, frees space)
        delete_table("temp_import", hard_delete=True)
    """
    from .core import delete_table as _delete_table
    
    _delete_table(table_name, hard_delete, connection_info, backend_name)


def delete_value(table_name: str, row_id: Union[str, int], column_name: str,
                connection_info: str = 'db.db', backend_name: str = None) -> bool:
    """
    DEPRECATED: Cell-level deletes no longer supported.
    
    Use delete_row() instead for row-level deletion.
    
    Args:
        table_name: Name of the table
        row_id: Row identifier
        column_name: Name of the column
        connection_info: Database connection
        backend_name: Backend to use
        
    Returns:
        bool: Always raises NotImplementedError
    """
    raise NotImplementedError(
        "Cell-level deletes are no longer supported. Use delete_row() for row-level deletion instead."
    )


def delete_row(table_name: str, row_id: str,
              connection_info: str = 'db.db', backend_name: str = None) -> bool:
    """
    Soft delete an entire row by updating row metadata.
    
    Args:
        table_name: Name of the table
        row_id: Row identifier
        connection_info: Database connection
        backend_name: Backend to use
        
    Returns:
        bool: True if the row was deleted, False if row didn't exist or was already deleted
        
    Examples:
        # Delete entire row efficiently
        was_deleted = delete_row("users", "user-123")
    """
    from .transactions import transaction_context
    
    # Validate that row_id is a string
    if not isinstance(row_id, str):
        raise ValueError(f"row_id must be a string, got {type(row_id).__name__}: {row_id}")
    
    backend_to_use = backend_name or config.get_backend_for_path(connection_info)
    
    with transaction_context(connection_info, backend_to_use) as (backend, connection):
        # Simply delete the row metadata - much more efficient
        return delete_row_metadata(row_id, backend, connection)


def undelete_row(table_name: str, row_id: str,
                connection_info: str = 'db.db', backend_name: str = None) -> bool:
    """
    Un-delete (resurrect) a previously deleted row.
    
    Args:
        table_name: Name of the table
        row_id: Row identifier
        connection_info: Database connection
        backend_name: Backend to use
        
    Returns:
        bool: True if the row was resurrected, False if row didn't exist or wasn't deleted
        
    Examples:
        # Manually resurrect a deleted row
        was_resurrected = undelete_row("users", "user-123")
    """
    from .transactions import transaction_context
    from .core import resurrect_row_metadata
    
    # Validate that row_id is a string
    if not isinstance(row_id, str):
        raise ValueError(f"row_id must be a string, got {type(row_id).__name__}: {row_id}")
    
    backend_to_use = backend_name or config.get_backend_for_path(connection_info)
    
    with transaction_context(connection_info, backend_to_use) as (backend, connection):
        return resurrect_row_metadata(row_id, backend, connection)


def get_row_status(table_name: str, row_id: str,
                  connection_info: str = 'db.db', backend_name: str = None) -> Dict:
    """
    Get row metadata including deletion status.
    
    Args:
        table_name: Name of the table
        row_id: Row identifier
        connection_info: Database connection
        backend_name: Backend to use
        
    Returns:
        Dict: Row metadata or None if row doesn't exist
        
    Examples:
        # Check if row exists and its status
        status = get_row_status("users", "user-123")
        if status:
            print(f"Row exists, deleted: {status['is_deleted']}")
    """
    from .transactions import transaction_context
    
    # Validate that row_id is a string
    if not isinstance(row_id, str):
        raise ValueError(f"row_id must be a string, got {type(row_id).__name__}: {row_id}")
    
    backend_to_use = backend_name or config.get_backend_for_path(connection_info)
    
    with transaction_context(connection_info, backend_to_use) as (backend, connection):
        return get_row_metadata(row_id, backend, connection)


def get_table_history(table_name: str, row_id: str = None, column_name: str = None,
                     include_deleted: bool = True, connection_info: str = 'db.db', 
                     backend_name: str = None) -> List[Dict]:
    """
    Get complete history for a table, row, or specific cell.
    
    Args:
        table_name: Name of the table
        row_id: Optional row identifier to filter by
        column_name: Optional column name to filter by
        include_deleted: Whether to include values from deleted rows
        connection_info: Database connection
        backend_name: Backend to use
        
    Returns:
        List[Dict]: History entries sorted by timestamp (newest first)
        
    Examples:
        # Get all history for a table
        history = get_table_history("users")
        
        # Get history for a specific row
        user_history = get_table_history("users", row_id="user-123")
        
        # Get history for a specific cell
        email_history = get_table_history("users", row_id="user-123", column_name="email")
        
        # Exclude values from deleted rows
        active_history = get_table_history("users", include_deleted=False)
    """
    from .transactions import transaction_context
    from .types import get_type_table_name
    
    backend_to_use = backend_name or config.get_backend_for_path(connection_info)
    
    with transaction_context(connection_info, backend_to_use) as (backend, connection):
        table_id = get_table_id(table_name, backend, connection)
        columns = get_table_columns(table_name, backend, connection)
        
        history_entries = []
        
        for column in columns:
            if column_name and column['name'] != column_name:
                continue
                
            type_table = get_type_table_name(column['data_type'])
            
            # Build query with row metadata JOIN for delete checking
            if include_deleted:
                # Include values even from deleted rows
                cur = backend.execute(connection, f"""
                    SELECT 
                        tv.row_id, 
                        tv.version,
                        tv.value,
                        tv.created_at,
                        tv.is_current,
                        rm.is_deleted,
                        rm.deleted_at,
                        '{column['name']}' as column_name,
                        '{column['data_type']}' as data_type
                    FROM {type_table} tv
                    LEFT JOIN row_metadata rm ON tv.row_id = rm.row_id
                    WHERE tv.table_id = {table_id} AND tv.column_id = {column['id']}
                    {f"AND tv.row_id = '{row_id}'" if row_id else ""}
                    ORDER BY tv.row_id, tv.version DESC
                """)
            else:
                # Only include values from active rows
                cur = backend.execute(connection, f"""
                    SELECT 
                        tv.row_id, 
                        tv.version,
                        tv.value,
                        tv.created_at,
                        tv.is_current,
                        rm.is_deleted,
                        rm.deleted_at,
                        '{column['name']}' as column_name,
                        '{column['data_type']}' as data_type
                    FROM {type_table} tv
                    JOIN row_metadata rm ON tv.row_id = rm.row_id
                    WHERE tv.table_id = {table_id} AND tv.column_id = {column['id']}
                    AND rm.is_deleted = 0
                    {f"AND tv.row_id = '{row_id}'" if row_id else ""}
                    ORDER BY tv.row_id, tv.version DESC
                """)
            
            for row in backend.fetchall(cur):
                history_entries.append(dict(row))
        
        # Sort by timestamp for chronological order
        history_entries.sort(key=lambda x: x['created_at'], reverse=True)
        return history_entries



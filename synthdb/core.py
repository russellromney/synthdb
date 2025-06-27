"""Core database operations for SynthDB."""

from .types import get_type_table_name
from .backends import get_backend
from .config import config
from .constants import validate_column_name, validate_table_name


def _validate_row_id(row_id):
    """
    Validate that row_id is a string.
    
    Raises ValueError if row_id is not a string.
    """
    if not isinstance(row_id, str):
        raise ValueError(f"row_id must be a string, got {type(row_id).__name__}: {row_id}")



def insert_typed_value(row_id, table_id, column_id, value, data_type, db_path: str = 'db.db', 
                      backend_name: str = None, backend=None, connection=None):
    """
    Insert a value into the appropriate type-specific table with versioned storage.
    
    This is a convenience wrapper around upsert_typed_value for new insertions.
    
    Args:
        row_id: Row identifier (must be string)
        table_id: Table identifier  
        column_id: Column identifier
        value: Value to insert
        data_type: Data type for value storage
        db_path: Database path (ignored if backend/connection provided)
        backend_name: Backend name (ignored if backend/connection provided)
        backend: Optional backend instance for transaction reuse
        connection: Optional connection for transaction reuse
    """
    # Validate row_id is a string
    _validate_row_id(row_id)
    # Use upsert for consistency - it handles both insert and update cases
    if backend and connection:
        return upsert_typed_value(row_id, table_id, column_id, value, data_type, backend, connection)
    else:
        # Create new transaction context
        from .transactions import transaction_context
        
        backend_to_use = backend_name or config.get_backend_for_path(db_path)
        connection_info = db_path
        
        with transaction_context(connection_info, backend_to_use) as (txn_backend, txn_connection):
            return upsert_typed_value(row_id, table_id, column_id, value, data_type, txn_backend, txn_connection)


def upsert_typed_value(row_id, table_id, column_id, value, data_type, 
                      backend=None, connection=None):
    """
    Smart upsert with automatic row resurrection and versioning.
    
    This function MUST be called within a transaction context.
    
    Args:
        row_id: Row identifier (must be string)
        table_id: Table identifier  
        column_id: Column identifier
        value: Value to insert/update
        data_type: Data type for value storage
        backend: Backend instance for transaction reuse
        connection: Connection for transaction reuse
    
    Returns:
        version: Version number of the new value
    """
    # Validate row_id is a string
    _validate_row_id(row_id)
    
    if not backend or not connection:
        raise ValueError("upsert_typed_value requires existing transaction context")
    
    table_name = get_type_table_name(data_type)
    
    # No value conversion needed - simplified types only
    
    try:
        # Step 1: Check if row is deleted and resurrect if needed
        if is_row_deleted(row_id, backend, connection):
            resurrect_row_metadata(row_id, backend, connection)
        
        # Step 2: Ensure row metadata exists
        ensure_row_metadata_exists(row_id, table_id, backend, connection)
        
        # Step 3: Mark current value as historical (atomic)
        backend.execute(connection, f"""
            UPDATE {table_name} 
            SET is_current = 0 
            WHERE row_id = ? AND table_id = ? AND column_id = ? 
            AND is_current = 1
        """, (row_id, table_id, column_id))
        
        # Step 4: Get next version number (within same transaction)
        cur = backend.execute(connection, f"""
            SELECT COALESCE(MAX(version), -1) + 1 as next_version
            FROM {table_name} 
            WHERE row_id = ? AND table_id = ? AND column_id = ?
        """, (row_id, table_id, column_id))
        
        result = backend.fetchone(cur)
        next_version = result['next_version'] if result else 0
        
        # Step 5: Insert new current value (atomic)
        backend.execute(connection, f"""
            INSERT INTO {table_name} (row_id, table_id, column_id, version, value, is_current)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (row_id, table_id, column_id, next_version, value))
        
        # Step 6: Update row metadata timestamp
        update_row_metadata_timestamp(row_id, backend, connection)
        
        # Transaction will be committed by caller
        return next_version
        
    except Exception as e:
        # Transaction will be rolled back by caller
        raise ValueError(f"Failed to upsert value: {e}")


# Cell-level deletes no longer supported - use row-level deletes instead
# This function is kept for backward compatibility but will raise an error
def soft_delete_typed_value(row_id, table_id, column_id, data_type, 
                           backend=None, connection=None):
    """
    DEPRECATED: Cell-level deletes no longer supported.
    
    Use delete_row_metadata() instead for row-level deletion.
    """
    raise NotImplementedError(
        "Cell-level deletes are no longer supported. Use row-level deletion instead."
    )


def get_typed_value(row_id, table_id, column_id, data_type, 
                   include_deleted=False, backend=None, connection=None):
    """
    Get current value with option to include deleted rows.
    
    Args:
        row_id: Row identifier
        table_id: Table identifier  
        column_id: Column identifier
        data_type: Data type for value storage
        include_deleted: Whether to include values from deleted rows
        backend: Backend instance for transaction reuse
        connection: Connection for transaction reuse
    
    Returns:
        dict: Value record or None if not found
    """
    if not backend or not connection:
        raise ValueError("get_typed_value requires existing transaction context")
    
    table_name = get_type_table_name(data_type)
    
    # Build query with row metadata JOIN for delete checking
    if include_deleted:
        # Include values even from deleted rows
        cur = backend.execute(connection, f"""
            SELECT tv.value, rm.is_deleted, rm.deleted_at, tv.created_at, tv.version
            FROM {table_name} tv
            LEFT JOIN row_metadata rm ON tv.row_id = rm.row_id
            WHERE tv.row_id = ? AND tv.table_id = ? AND tv.column_id = ? 
            AND tv.is_current = 1
        """, (row_id, table_id, column_id))
    else:
        # Only include values from active rows
        cur = backend.execute(connection, f"""
            SELECT tv.value, rm.is_deleted, rm.deleted_at, tv.created_at, tv.version
            FROM {table_name} tv
            JOIN row_metadata rm ON tv.row_id = rm.row_id
            WHERE tv.row_id = ? AND tv.table_id = ? AND tv.column_id = ? 
            AND tv.is_current = 1 AND rm.is_deleted = 0
        """, (row_id, table_id, column_id))
    
    return backend.fetchone(cur)


def get_table_id(table_name: str, backend, connection) -> int:
    """Get table ID from table name."""
    cur = backend.execute(connection, "SELECT id FROM table_definitions WHERE name = ? AND deleted_at IS NULL", (table_name,))
    result = backend.fetchone(cur)
    if not result:
        raise ValueError(f"Table '{table_name}' not found")
    return result['id']


def get_column_info(table_name: str, column_name: str, backend, connection) -> dict:
    """Get column information including ID and data type."""
    cur = backend.execute(connection, """
        SELECT cd.id, cd.data_type, cd.name
        FROM column_definitions cd
        JOIN table_definitions td ON cd.table_id = td.id
        WHERE td.name = ? AND cd.name = ? 
        AND td.deleted_at IS NULL AND cd.deleted_at IS NULL
    """, (table_name, column_name))
    return backend.fetchone(cur)


def get_table_columns(table_name: str, backend, connection) -> list:
    """Get all columns for a table."""
    cur = backend.execute(connection, """
        SELECT cd.id, cd.name, cd.data_type
        FROM column_definitions cd
        JOIN table_definitions td ON cd.table_id = td.id
        WHERE td.name = ? 
        AND td.deleted_at IS NULL AND cd.deleted_at IS NULL
        ORDER BY cd.id
    """, (table_name,))
    return backend.fetchall(cur)


def create_row_metadata(row_id: str, table_id: int, backend, connection) -> None:
    """Create row metadata entry for a new row."""
    backend.execute(connection, """
        INSERT INTO row_metadata (row_id, table_id, is_deleted, version)
        VALUES (?, ?, 0, 1)
    """, (row_id, table_id))


def ensure_row_metadata_exists(row_id: str, table_id: int, backend, connection) -> None:
    """Ensure row metadata exists, create if missing."""
    cur = backend.execute(connection, """
        SELECT row_id FROM row_metadata WHERE row_id = ?
    """, (row_id,))
    
    if not backend.fetchone(cur):
        create_row_metadata(row_id, table_id, backend, connection)


def get_row_metadata(row_id: str, backend, connection) -> dict:
    """Get row metadata for a specific row."""
    cur = backend.execute(connection, """
        SELECT row_id, table_id, created_at, updated_at, deleted_at, is_deleted, version
        FROM row_metadata 
        WHERE row_id = ?
    """, (row_id,))
    return backend.fetchone(cur)


def is_row_deleted(row_id: str, backend, connection) -> bool:
    """Check if a row is deleted."""
    cur = backend.execute(connection, """
        SELECT is_deleted FROM row_metadata WHERE row_id = ?
    """, (row_id,))
    result = backend.fetchone(cur)
    return result and result['is_deleted']


def delete_row_metadata(row_id: str, backend, connection) -> bool:
    """Soft delete a row by updating metadata only."""
    changes_before = getattr(connection, 'total_changes', 0) if hasattr(connection, 'total_changes') else 0
    
    backend.execute(connection, """
        UPDATE row_metadata 
        SET is_deleted = 1, deleted_at = strftime('%Y-%m-%d %H:%M:%f', 'now'), updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now')
        WHERE row_id = ? AND is_deleted = 0
    """, (row_id,))
    
    changes_after = getattr(connection, 'total_changes', 0) if hasattr(connection, 'total_changes') else 0
    return changes_after > changes_before


def resurrect_row_metadata(row_id: str, backend, connection) -> bool:
    """Un-delete a row by clearing deleted_at."""
    changes_before = getattr(connection, 'total_changes', 0) if hasattr(connection, 'total_changes') else 0
    
    backend.execute(connection, """
        UPDATE row_metadata 
        SET is_deleted = 0, deleted_at = NULL, updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now'), version = version + 1
        WHERE row_id = ? AND is_deleted = 1
    """, (row_id,))
    
    changes_after = getattr(connection, 'total_changes', 0) if hasattr(connection, 'total_changes') else 0
    return changes_after > changes_before


def update_row_metadata_timestamp(row_id: str, backend, connection) -> None:
    """Update the updated_at timestamp for a row."""
    backend.execute(connection, """
        UPDATE row_metadata 
        SET updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now')
        WHERE row_id = ?
    """, (row_id,))


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
        
        # Copy values
        backend.execute(connection, f"""
            INSERT INTO {type_table} (row_id, table_id, column_id, value)
            SELECT row_id, ?, ?, value
            FROM {type_table}
            WHERE table_id = ? AND column_id = ?
        """, (target_table_id, new_column_id, source_table_id, source_column_id))
    
    # Recreate views after transaction completes
    from .views import create_table_views
    create_table_views(db_path, backend_name=backend_to_use)
    
    return new_column_id


def copy_table(source_table: str, target_table: str, copy_data: bool = False,
               db_path: str = 'db.db', backend_name: str = None) -> int:
    """
    Copy a table's structure and optionally its data.
    
    Args:
        source_table: Name of table to copy from
        target_table: Name of new table to create
        copy_data: If True, copy all data; if False, structure only
        db_path: Database path
        backend_name: Backend to use
        
    Returns:
        ID of the newly created table
        
    Raises:
        ValueError: If source table doesn't exist or target already exists
    """
    from .transactions import transaction_context
    
    # Validate table names
    validate_table_name(source_table)
    validate_table_name(target_table)
    
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    
    with transaction_context(db_path, backend_to_use) as (backend, connection):
        # Check source exists
        try:
            source_table_id = get_table_id(source_table, backend, connection)
        except ValueError:
            raise ValueError(f"Source table '{source_table}' not found")
        
        # Check target doesn't exist
        try:
            get_table_id(target_table, backend, connection)
            # If we reach here, table exists - that's an error
            raise ValueError(f"Target table '{target_table}' already exists")
        except ValueError as e:
            if "already exists" in str(e):
                # Re-raise the "already exists" error
                raise
            # Otherwise, table doesn't exist - that's good
        
        # Phase 1: Copy structure
        new_table_id = _copy_table_structure(
            source_table_id, target_table, backend, connection
        )
        
        if copy_data:
            # Phase 2: Copy data
            _copy_table_data(source_table_id, new_table_id, backend, connection)
        
        # Views will be recreated after transaction commits
        
    # Recreate views after transaction
    from .views import create_table_views
    create_table_views(db_path, backend_name=backend_to_use)
    
    return new_table_id


def _copy_table_structure(source_table_id: int, target_name: str, 
                         backend, connection) -> int:
    """Copy table structure efficiently within a transaction."""
    # 1. Get next table ID
    cur = backend.execute(connection, 
        "SELECT COALESCE(MAX(id), -1) + 1 as next_id FROM table_definitions")
    result = backend.fetchone(cur)
    new_table_id = result['next_id'] if result else 0
    
    # 2. Create new table entry
    backend.execute(connection, """
        INSERT INTO table_definitions (id, version, name)
        VALUES (?, 0, ?)
    """, (new_table_id, target_name))
    
    # 3. Get source columns
    cur = backend.execute(connection, """
        SELECT id, name, data_type
        FROM column_definitions
        WHERE table_id = ? AND deleted_at IS NULL
        ORDER BY id
    """, (source_table_id,))
    source_columns = backend.fetchall(cur)
    
    if source_columns:
        # 4. Get starting column ID
        cur = backend.execute(connection, 
            "SELECT COALESCE(MAX(id), -1) + 1 as next_id FROM column_definitions")
        result = backend.fetchone(cur)
        next_col_id = result['next_id'] if result else 0
        
        # 5. Insert all columns
        for i, col in enumerate(source_columns):
            backend.execute(connection, """
                INSERT INTO column_definitions (id, table_id, version, name, data_type)
                VALUES (?, ?, 0, ?, ?)
            """, (next_col_id + i, new_table_id, col['name'], col['data_type']))
    
    return new_table_id


def _copy_table_data(source_table_id: int, target_table_id: int, 
                    backend, connection) -> None:
    """Copy table data efficiently within a transaction."""
    # 1. Get column mappings
    column_map = _get_column_mapping(source_table_id, target_table_id, backend, connection)
    
    if not column_map:
        return  # No columns to copy
    
    # 2. Get all source rows
    cur = backend.execute(connection, """
        SELECT DISTINCT row_id 
        FROM row_metadata
        WHERE table_id = ? AND is_deleted = 0
    """, (source_table_id,))
    source_rows = backend.fetchall(cur)
    
    if not source_rows:
        return  # No data to copy
    
    # 3. Create row mappings
    import uuid
    row_map = {}
    for row in source_rows:
        old_row_id = row['row_id']
        new_row_id = str(uuid.uuid4())
        row_map[old_row_id] = new_row_id
        
        # Create row metadata
        create_row_metadata(new_row_id, target_table_id, backend, connection)
    
    # 4. Copy values for each data type
    for data_type in ['text', 'integer', 'real', 'timestamp']:
        _copy_values_by_type(
            source_table_id, target_table_id, column_map, row_map,
            data_type, backend, connection
        )


def _get_column_mapping(source_table_id: int, target_table_id: int, 
                       backend, connection) -> dict:
    """Get mapping of source column IDs to target column IDs."""
    # Get source columns
    cur = backend.execute(connection, """
        SELECT id, name 
        FROM column_definitions
        WHERE table_id = ? AND deleted_at IS NULL
        ORDER BY id
    """, (source_table_id,))
    source_cols = {col['name']: col['id'] for col in backend.fetchall(cur)}
    
    # Get target columns
    cur = backend.execute(connection, """
        SELECT id, name 
        FROM column_definitions
        WHERE table_id = ? AND deleted_at IS NULL
        ORDER BY id
    """, (target_table_id,))
    target_cols = {col['name']: col['id'] for col in backend.fetchall(cur)}
    
    # Create mapping (source_id -> target_id)
    column_map = {}
    for name, source_id in source_cols.items():
        if name in target_cols:
            column_map[source_id] = target_cols[name]
    
    return column_map


def _copy_values_by_type(source_table_id: int, target_table_id: int,
                        column_map: dict, row_map: dict, data_type: str,
                        backend, connection) -> None:
    """Copy values for a specific data type."""
    table_name = get_type_table_name(data_type)
    
    # Get values to copy
    source_col_ids = ','.join(map(str, column_map.keys()))
    if not source_col_ids:
        return
    
    cur = backend.execute(connection, f"""
        SELECT row_id, column_id, version, value, is_current
        FROM {table_name}
        WHERE table_id = ? 
          AND column_id IN ({source_col_ids})
          AND row_id IN ({','.join(['?' for _ in row_map])})
    """, [source_table_id] + list(row_map.keys()))
    
    values = backend.fetchall(cur)
    
    # Insert values with new IDs
    for val in values:
        new_row_id = row_map[val['row_id']]
        new_col_id = column_map[val['column_id']]
        
        backend.execute(connection, f"""
            INSERT INTO {table_name} (row_id, table_id, column_id, version, value, is_current)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (new_row_id, target_table_id, new_col_id, 
              val['version'], val['value'], val['is_current']))


def rename_column(table_name: str, old_column_name: str, new_column_name: str,
                  db_path: str = 'db.db', backend_name: str = None) -> None:
    """
    Rename a column in a table.
    
    Args:
        table_name: Name of the table
        old_column_name: Current column name
        new_column_name: New column name
        db_path: Database path
        backend_name: Backend to use
        
    Raises:
        ValueError: If table/column not found or new name already exists
    """
    from .transactions import transaction_context
    
    # Validate new column name is not protected
    validate_column_name(new_column_name)
    
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    
    with transaction_context(db_path, backend_to_use) as (backend, connection):
        # Get table ID
        table_id = get_table_id(table_name, backend, connection)
        
        # Check old column exists
        cur = backend.execute(connection, """
            SELECT id FROM column_definitions 
            WHERE table_id = ? AND name = ? AND deleted_at IS NULL
        """, (table_id, old_column_name))
        result = backend.fetchone(cur)
        if not result:
            raise ValueError(f"Column '{old_column_name}' not found in table '{table_name}'")
        column_id = result['id']
        
        # Check new name doesn't exist
        cur = backend.execute(connection, """
            SELECT id FROM column_definitions 
            WHERE table_id = ? AND name = ? AND deleted_at IS NULL
        """, (table_id, new_column_name))
        if backend.fetchone(cur):
            raise ValueError(f"Column '{new_column_name}' already exists in table '{table_name}'")
        
        # Update column name
        backend.execute(connection, """
            UPDATE column_definitions 
            SET name = ?, version = version + 1
            WHERE id = ?
        """, (new_column_name, column_id))
    
    # Recreate views after transaction
    from .views import create_table_views
    create_table_views(db_path, backend_name=backend_to_use)


def delete_column(table_name: str, column_name: str, hard_delete: bool = False,
                  db_path: str = 'db.db', backend_name: str = None) -> None:
    """
    Delete a column from a table.
    
    Args:
        table_name: Name of the table
        column_name: Name of the column to delete
        hard_delete: If True, permanently delete all column data; if False, soft delete
        db_path: Database path
        backend_name: Backend to use
        
    Raises:
        ValueError: If table/column not found
    """
    from .transactions import transaction_context
    
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    
    with transaction_context(db_path, backend_to_use) as (backend, connection):
        # Get table ID
        table_id = get_table_id(table_name, backend, connection)
        
        # Check column exists (including soft-deleted columns for hard delete)
        if hard_delete:
            # Allow hard deletion of soft-deleted columns
            cur = backend.execute(connection, """
                SELECT id, data_type FROM column_definitions 
                WHERE table_id = ? AND name = ?
            """, (table_id, column_name))
        else:
            # Only check non-deleted columns for soft delete
            cur = backend.execute(connection, """
                SELECT id, data_type FROM column_definitions 
                WHERE table_id = ? AND name = ? AND deleted_at IS NULL
            """, (table_id, column_name))
        
        result = backend.fetchone(cur)
        if not result:
            raise ValueError(f"Column '{column_name}' not found in table '{table_name}'")
        column_id = result['id']
        data_type = result['data_type']
        
        if hard_delete:
            # Permanently delete all column data
            _hard_delete_column(table_id, column_id, data_type, backend, connection)
        else:
            # Soft delete the column
            backend.execute(connection, """
                UPDATE column_definitions 
                SET deleted_at = strftime('%Y-%m-%d %H:%M:%f', 'now'), version = version + 1
                WHERE id = ?
            """, (column_id,))
    
    # Recreate views after transaction
    from .views import create_table_views
    create_table_views(db_path, backend_name=backend_to_use)


def delete_table(table_name: str, hard_delete: bool = False,
                 db_path: str = 'db.db', backend_name: str = None) -> None:
    """
    Delete a table and all its associated data.
    
    Args:
        table_name: Name of the table to delete
        hard_delete: If True, permanently delete all data; if False, soft delete
        db_path: Database path
        backend_name: Backend to use
        
    Raises:
        ValueError: If table not found
    """
    from .transactions import transaction_context
    
    # Validate table name is not protected
    validate_table_name(table_name)
    
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    
    with transaction_context(db_path, backend_to_use) as (backend, connection):
        # Get table ID
        table_id = get_table_id(table_name, backend, connection)
        
        if hard_delete:
            # Permanently delete all data
            _hard_delete_table(table_id, backend, connection)
        else:
            # Soft delete - mark table and columns as deleted
            _soft_delete_table(table_id, backend, connection)
    
    # Recreate views after transaction
    from .views import create_table_views
    create_table_views(db_path, backend_name=backend_to_use)


def _soft_delete_table(table_id: int, backend, connection) -> None:
    """Soft delete a table by marking it and its columns as deleted."""
    # Mark table as deleted
    backend.execute(connection, """
        UPDATE table_definitions 
        SET deleted_at = strftime('%Y-%m-%d %H:%M:%f', 'now'), version = version + 1
        WHERE id = ?
    """, (table_id,))
    
    # Mark all columns as deleted
    backend.execute(connection, """
        UPDATE column_definitions 
        SET deleted_at = strftime('%Y-%m-%d %H:%M:%f', 'now'), version = version + 1
        WHERE table_id = ? AND deleted_at IS NULL
    """, (table_id,))


def _hard_delete_table(table_id: int, backend, connection) -> None:
    """Permanently delete a table and all associated data."""
    # Delete from all value tables
    for type_table in ['text_values', 'integer_values', 'real_values', 'timestamp_values']:
        backend.execute(connection, 
            f"DELETE FROM {type_table} WHERE table_id = ?", (table_id,))
    
    # Delete row metadata
    backend.execute(connection, 
        "DELETE FROM row_metadata WHERE table_id = ?", (table_id,))
    
    # Delete column definitions
    backend.execute(connection, 
        "DELETE FROM column_definitions WHERE table_id = ?", (table_id,))
    
    # Delete table definition
    backend.execute(connection, 
        "DELETE FROM table_definitions WHERE id = ?", (table_id,))


def _hard_delete_column(table_id: int, column_id: int, data_type: str, 
                       backend, connection) -> None:
    """Permanently delete a column and all its data."""
    # Get the value table name for this data type
    table_name = get_type_table_name(data_type)
    
    # Delete all values for this column
    backend.execute(connection, 
        f"DELETE FROM {table_name} WHERE table_id = ? AND column_id = ?", 
        (table_id, column_id))
    
    # Delete column definition
    backend.execute(connection, 
        "DELETE FROM column_definitions WHERE id = ?", (column_id,))
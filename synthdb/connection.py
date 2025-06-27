"""
Connection class for SynthDB - provides a clean, object-oriented interface.

This class encapsulates database connection information and provides all 
database operations as methods, eliminating the need to pass connection 
details to every function call.
"""

from typing import Optional, Dict, Any, Union, List
from .database import make_db
from .core import create_table as _create_table, add_column as _add_column
from .utils import list_tables, list_columns, query_view
from .views import create_table_views
from .inference import infer_type
from .transactions import transaction_context


class Connection:
    """
    SynthDB connection class providing a clean, object-oriented interface.
    
    This class encapsulates connection details and provides all database operations
    as methods, eliminating the need to pass connection info to every function.
    
    Examples:
        # Initialize with file database
        db = synthdb.connect('myapp.db', backend='sqlite')
        
        # Create and use tables
        db.create_table('users')
        db.add_columns('users', {
            'name': 'text',
            'age': 25,
            'email': 'user@example.com'
        })
        
        # Insert data with auto-generated ID
        user_id = db.insert('users', {
            'name': 'John Doe',
            'age': 30,
            'email': 'john@example.com'
        })
        
        # Query data
        users = db.query('users', 'age > 25')
    """
    
    def __init__(self, connection_info: Union[str, Dict[str, Any]] = 'db.db', 
                 backend: Optional[str] = None, auto_init: bool = True):
        """
        Initialize SynthDB connection.
        
        Args:
            connection_info: Database file path or dict
            backend: Database backend ('sqlite', 'libsql')
            auto_init: Automatically initialize database if it doesn't exist
        
        Examples:
            # File databases
            db = synthdb.connect('app.db', 'sqlite')
            db = synthdb.connect('data.db', 'libsql')
            
            # Remote LibSQL
            db = synthdb.connect('libsql://your-db.turso.io', 'libsql')
            
            # Auto-detection
            db = synthdb.connect('app.db')  # Uses SQLite (default)
            
            # Connection dict
            db = synthdb.connect({
                'backend': 'sqlite',
                'path': 'app.db'
            })
        """
        self.connection_info = connection_info
        self.backend_name = backend
        
        # Auto-detect backend from connection string if not specified
        if backend is None and isinstance(connection_info, str) and '://' in connection_info:
            from .backends import parse_connection_string
            self.backend_name, _ = parse_connection_string(connection_info)
        
        # Auto-initialize database if requested
        if auto_init:
            try:
                self.init_db()
            except Exception:
                # Database might already exist, which is fine
                pass
    
    def init_db(self) -> None:
        """
        Initialize the database schema.
        """
        make_db(self.connection_info, self.backend_name)
    
    def create_table(self, name: str) -> int:
        """
        Create a new table.
        
        Args:
            name: Table name
            
        Returns:
            Table ID
        """
        return _create_table(name, self.connection_info, self.backend_name)
    
    def add_column(self, table_name: str, column_name: str, data_type: str) -> int:
        """
        Add a single column to a table.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column
            data_type: Data type ('text', 'integer', 'real', 'timestamp')
            
        Returns:
            Column ID
        """
        return _add_column(table_name, column_name, data_type, 
                          self.connection_info, self.backend_name)
    
    def add_columns(self, table_name: str, columns: Dict[str, Union[str, Any]]) -> Dict[str, int]:
        """
        Add multiple columns to a table at once with type inference.
        
        Args:
            table_name: Name of the table
            columns: Dictionary of column_name -> type_or_sample_value
            
        Returns:
            Dictionary mapping column names to their IDs
            
        Examples:
            # Explicit types
            ids = db.add_columns('users', {
                'email': 'text',
                'age': 'integer',
                'created_at': 'timestamp'
            })
            
            # Inferred types from sample values
            ids = db.add_columns('users', {
                'email': 'user@example.com',      # -> text
                'age': 25,                        # -> integer
                'score': 98.5,                    # -> real
                'created_at': '2023-12-25'        # -> timestamp
            })
        """
        valid_types = {"text", "integer", "real", "timestamp"}
        column_ids = {}
        
        with transaction_context(self.connection_info, self.backend_name) as (backend, connection):
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
                    table_name, col_name, data_type, self.connection_info, self.backend_name,
                    backend=backend, connection=connection
                )
                column_ids[col_name] = column_id
        
        # Recreate views to include new columns
        create_table_views(self.connection_info, self.backend_name)
        
        return column_ids
    
    def insert(self, table_name: str, data: Union[Dict[str, Any], str], 
               value: Optional[Any] = None, force_type: Optional[str] = None, row_id: Optional[Union[str, int]] = None) -> str:
        """
        Insert data into a table with automatic or explicit ID management.
        
        Args:
            table_name: Name of the table
            data: Dictionary of column->value pairs, OR column name (if value provided)
            value: Value to insert (if data is a column name)
            force_type: Override automatic type inference
            row_id: Explicit row ID (if None, auto-generates next available ID)
            
        Returns:
            The row ID (auto-generated or explicitly provided)
            
        Examples:
            # Auto-generated ID
            user_id = db.insert('users', {'name': 'John', 'age': 25})
            
            # Explicit ID
            db.insert('users', {'name': 'Jane'}, row_id="100")
            
            # Single column
            db.insert('users', 'email', 'john@example.com')
            
            # Force specific type
            db.insert('users', 'age', '25', force_type='text')
        """
        from .api import insert
        return insert(table_name, data, value, self.connection_info, 
                     self.backend_name, force_type, row_id)
    
    def query(self, table_name: str, where: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query data from a table.
        
        Args:
            table_name: Name of the table to query
            where: Optional WHERE clause
            
        Returns:
            List of dictionaries representing rows
            
        Examples:
            # Get all rows
            rows = db.query('users')
            
            # Filter rows
            rows = db.query('users', 'age > 25')
        """
        return query_view(table_name, where, self.connection_info, self.backend_name)
    
    def upsert(self, table_name: str, data: Dict[str, Any], row_id: Union[str, int]) -> str:
        """
        Insert or update data for a specific row_id.
        
        If the row_id exists, updates the existing row with new data.
        If the row_id doesn't exist, creates a new row with that row_id.
        
        Args:
            table_name: Name of the table
            data: Column data to insert/update
            row_id: Specific row ID to insert or update
            
        Returns:
            The row_id that was inserted or updated
            
        Examples:
            # Update existing row or create new row with ID 100
            db.upsert('users', {'name': 'Jane', 'age': 30}, row_id="100")
            
            # Update row 1 with new data
            db.upsert('users', {'name': 'John Updated', 'email': 'john.new@example.com'}, row_id="1")
        """
        from .api import upsert
        return upsert(table_name, data, row_id, self.connection_info, self.backend_name)
    
    def copy_column(self, source_table: str, source_column: str, target_table: str, 
                   target_column: str, copy_data: bool = False) -> int:
        """
        Copy a column from one table to another, optionally including data.
        
        Args:
            source_table: Name of source table
            source_column: Name of source column
            target_table: Name of target table
            target_column: Name of new column in target table
            copy_data: If True, copy data; if False, only copy structure
            
        Returns:
            ID of the newly created column
            
        Examples:
            # Copy structure only (fast)
            db.copy_column("users", "email", "customers", "contact_email")
            
            # Copy structure and data (slower)
            db.copy_column("users", "email", "customers", "contact_email", copy_data=True)
            
            # Copy within same table
            db.copy_column("users", "email", "users", "backup_email", copy_data=True)
        """
        from .api import copy_column
        return copy_column(source_table, source_column, target_table, target_column,
                          copy_data, self.connection_info, self.backend_name)
    
    def copy_table(self, source_table: str, target_table: str, copy_data: bool = False) -> int:
        """
        Copy a table's structure and optionally its data.
        
        Creates a new table that is a copy of an existing table. Can copy just the
        structure (table and column definitions) or include all data as well.
        When copying data, new row IDs are generated to avoid conflicts.
        
        Args:
            source_table: Name of table to copy from
            target_table: Name of new table to create
            copy_data: If True, copy all data; if False, structure only
            
        Returns:
            ID of the newly created table
            
        Raises:
            ValueError: If source table doesn't exist or target already exists
            
        Examples:
            # Copy structure only (fast)
            table_id = db.copy_table("users", "users_template")
            
            # Copy structure and all data (slower)
            table_id = db.copy_table("users", "users_backup", copy_data=True)
            
            # Create archive copy
            table_id = db.copy_table("orders_2023", "orders_2023_archive", copy_data=True)
        """
        from .core import copy_table as _copy_table
        return _copy_table(source_table, target_table, copy_data, 
                          self.connection_info, self.backend_name)
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """
        List all tables in the database.
        
        Returns:
            List of table information dictionaries
        """
        return list_tables(self.connection_info, self.backend_name)
    
    def list_columns(self, table_name: str, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        List columns in a table.
        
        Args:
            table_name: Name of the table
            include_deleted: If True, include soft-deleted columns
            
        Returns:
            List of column information dictionaries with id, name, data_type, created_at, and deleted_at
        """
        return list_columns(table_name, include_deleted, self.connection_info, self.backend_name)
    
    def delete_value(self, table_name: str, row_id: Union[str, int], column_name: str) -> bool:
        """
        DEPRECATED: Cell-level deletes no longer supported.
        
        Use delete_row() instead for row-level deletion.
        
        Args:
            table_name: Name of the table
            row_id: Row identifier
            column_name: Name of the column
            
        Returns:
            bool: Always raises NotImplementedError
        """
        from .api import delete_value
        return delete_value(table_name, row_id, column_name, self.connection_info, self.backend_name)
    
    def delete_row(self, table_name: str, row_id: Union[str, int]) -> bool:
        """
        Soft delete an entire row by updating row metadata.
        
        Args:
            table_name: Name of the table
            row_id: Row identifier
            
        Returns:
            bool: True if the row was deleted, False if row didn't exist or was already deleted
            
        Examples:
            # Delete entire row efficiently
            was_deleted = db.delete_row("users", "user-123")
        """
        from .api import delete_row
        return delete_row(table_name, row_id, self.connection_info, self.backend_name)
    
    def undelete_row(self, table_name: str, row_id: Union[str, int]) -> bool:
        """
        Un-delete (resurrect) a previously deleted row.
        
        Args:
            table_name: Name of the table
            row_id: Row identifier
            
        Returns:
            bool: True if the row was resurrected, False if row didn't exist or wasn't deleted
            
        Examples:
            # Manually resurrect a deleted row
            was_resurrected = db.undelete_row("users", "user-123")
        """
        from .api import undelete_row
        return undelete_row(table_name, row_id, self.connection_info, self.backend_name)
    
    def get_row_status(self, table_name: str, row_id: Union[str, int]) -> Dict:
        """
        Get row metadata including deletion status.
        
        Args:
            table_name: Name of the table
            row_id: Row identifier
            
        Returns:
            Dict: Row metadata or None if row doesn't exist
            
        Examples:
            # Check if row exists and its status
            status = db.get_row_status("users", "user-123")
            if status:
                print(f"Row exists, deleted: {status['is_deleted']}")
        """
        from .api import get_row_status
        return get_row_status(table_name, row_id, self.connection_info, self.backend_name)
    
    def get_table_history(self, table_name: str, row_id: Optional[str] = None, column_name: Optional[str] = None,
                         include_deleted: bool = True) -> List[Dict]:
        """
        Get complete history for a table, row, or specific cell.
        
        Args:
            table_name: Name of the table
            row_id: Optional row identifier to filter by
            column_name: Optional column name to filter by
            include_deleted: Whether to include values from deleted rows
            
        Returns:
            List[Dict]: History entries sorted by timestamp (newest first)
            
        Examples:
            # Get all history for a table
            history = db.get_table_history("users")
            
            # Get history for a specific row
            user_history = db.get_table_history("users", row_id="user-123")
            
            # Get history for a specific cell
            email_history = db.get_table_history("users", row_id="user-123", column_name="email")
            
            # Exclude values from deleted rows
            active_history = db.get_table_history("users", include_deleted=False)
        """
        from .api import get_table_history
        return get_table_history(table_name, row_id, column_name, include_deleted, 
                                self.connection_info, self.backend_name)
    
    def refresh_views(self) -> None:
        """
        Refresh all table views in the database.
        """
        create_table_views(self.connection_info, self.backend_name)
    
    def rename_column(self, table_name: str, old_column_name: str, new_column_name: str) -> None:
        """
        Rename a column in a table.
        
        Args:
            table_name: Name of the table
            old_column_name: Current column name
            new_column_name: New column name
            
        Raises:
            ValueError: If table/column not found or new name already exists
            
        Examples:
            # Rename a column
            db.rename_column("users", "email", "email_address")
            
            # Fix typo in column name
            db.rename_column("products", "descrption", "description")
        """
        from .api import rename_column
        rename_column(table_name, old_column_name, new_column_name,
                     self.connection_info, self.backend_name)
    
    def delete_column(self, table_name: str, column_name: str, hard_delete: bool = False) -> None:
        """
        Delete a column from a table.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column to delete
            hard_delete: If True, permanently delete all column data; if False, soft delete
            
        Raises:
            ValueError: If table/column not found
            
        Examples:
            # Soft delete (preserves data)
            db.delete_column("users", "deprecated_field")
            
            # Hard delete (permanently removes data)
            db.delete_column("products", "old_price", hard_delete=True)
            
            # Hard delete a previously soft-deleted column
            db.delete_column("users", "removed_field", hard_delete=True)
        """
        from .api import delete_column
        delete_column(table_name, column_name, hard_delete, self.connection_info, self.backend_name)
    
    def delete_table(self, table_name: str, hard_delete: bool = False) -> None:
        """
        Delete a table and all its associated data.
        
        Args:
            table_name: Name of the table to delete
            hard_delete: If True, permanently delete all data; if False, soft delete
            
        Raises:
            ValueError: If table not found
            
        Examples:
            # Soft delete (can be recovered)
            db.delete_table("old_users")
            
            # Hard delete (permanent, frees space)
            db.delete_table("temp_import", hard_delete=True)
        """
        from .api import delete_table
        delete_table(table_name, hard_delete, self.connection_info, self.backend_name)
    
    def __repr__(self) -> str:
        """String representation of the connection."""
        backend = self.backend_name or 'auto'
        if isinstance(self.connection_info, dict):
            conn_desc = f"{self.connection_info.get('backend', 'unknown')} connection"
        elif '://' in str(self.connection_info):
            conn_desc = str(self.connection_info).split('://')[0] + ' connection'
        else:
            conn_desc = f"file: {self.connection_info}"
        return f"Connection({conn_desc}, backend={backend})"
    
    def close(self) -> None:
        """
        Close the database connection.
        
        Note: This is primarily useful for testing and cleanup.
        In normal usage, connections are managed automatically.
        """
        # Since we don't maintain a persistent connection,
        # this method is provided for compatibility
        pass
    
    def __enter__(self) -> 'Connection':
        """Support context manager protocol."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Support context manager protocol."""
        self.close()
        return False


# Main connection function
def connect(connection_info: Union[str, Dict[str, Any]] = 'db.db', 
           backend: Optional[str] = None, auto_init: bool = True) -> Connection:
    """
    Create a SynthDB connection.
    
    This is the primary way to connect to a SynthDB database.
    
    Args:
        connection_info: Database file path or dict
        backend: Database backend ('libsql', 'sqlite')
        auto_init: Automatically initialize database if it doesn't exist
        
    Returns:
        Connection instance
        
    Examples:
        # Quick connection
        db = synthdb.connect('myapp.db', 'libsql')
        
        # Auto-detect backend
        db = synthdb.connect('app.db')
    """
    return Connection(connection_info, backend, auto_init)
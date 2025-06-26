"""
Connection class for SynthDB - provides a clean, object-oriented interface.

This class encapsulates database connection information and provides all 
database operations as methods, eliminating the need to pass connection 
details to every function call.
"""

from typing import Dict, Any, Union, List
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
                 backend: str = None, auto_init: bool = True):
        """
        Initialize SynthDB connection.
        
        Args:
            connection_info: Database file path or dict
            backend: Database backend ('limbo', 'sqlite')
            auto_init: Automatically initialize database if it doesn't exist
        
        Examples:
            # File databases
            db = synthdb.connect('app.db', 'sqlite')
            db = synthdb.connect('app.limbo', 'limbo')
            
            # Auto-detection by extension
            db = synthdb.connect('app.db')     # Uses SQLite
            db = synthdb.connect('app.limbo')  # Uses Limbo
            
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
            data_type: Data type ('text', 'integer', 'real', 'boolean', 'json', 'timestamp')
            
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
                'created_at': 'timestamp',
                'metadata': 'json'
            })
            
            # Inferred types from sample values
            ids = db.add_columns('users', {
                'email': 'user@example.com',      # -> text
                'age': 25,                        # -> integer
                'active': True,                   # -> boolean
                'created_at': '2023-12-25'        # -> timestamp
            })
        """
        valid_types = {"text", "integer", "real", "boolean", "json", "timestamp"}
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
               value: Any = None, force_type: str = None, row_id: Union[str, int] = None) -> str:
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
            db.insert('users', {'name': 'Jane'}, row_id=100)
            
            # Single column
            db.insert('users', 'email', 'john@example.com')
            
            # Force specific type
            db.insert('users', 'age', '25', force_type='text')
        """
        from .api import insert
        return insert(table_name, data, value, self.connection_info, 
                     self.backend_name, force_type, row_id)
    
    def query(self, table_name: str, where: str = None) -> List[Dict[str, Any]]:
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
            db.upsert('users', {'name': 'Jane', 'age': 30}, row_id=100)
            
            # Update row 1 with new data
            db.upsert('users', {'name': 'John Updated', 'email': 'john.new@example.com'}, row_id=1)
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
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """
        List all tables in the database.
        
        Returns:
            List of table information dictionaries
        """
        return list_tables(self.connection_info, self.backend_name)
    
    def list_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        List all columns in a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        return list_columns(table_name, self.connection_info, self.backend_name)
    
    def refresh_views(self) -> None:
        """
        Refresh all table views in the database.
        """
        create_table_views(self.connection_info, self.backend_name)
    
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


# Main connection function
def connect(connection_info: Union[str, Dict[str, Any]] = 'db.db', 
           backend: str = None, auto_init: bool = True) -> Connection:
    """
    Create a SynthDB connection.
    
    This is the primary way to connect to a SynthDB database.
    
    Args:
        connection_info: Database file path or dict
        backend: Database backend ('limbo', 'sqlite')
        auto_init: Automatically initialize database if it doesn't exist
        
    Returns:
        Connection instance
        
    Examples:
        # Quick connection
        db = synthdb.connect('myapp.db', 'sqlite')
        
        # Auto-detect backend
        db = synthdb.connect('app.db')
    """
    return Connection(connection_info, backend, auto_init)
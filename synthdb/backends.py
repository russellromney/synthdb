"""Database backend abstraction layer for SynthDB."""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Tuple, Optional, Union
import sqlite3


class DatabaseBackend(ABC):
    """Abstract base class for database backends."""
    
    @abstractmethod
    def connect(self, connection_info: Union[str, Dict[str, Any]]) -> Any:
        """Connect to the database."""
        pass
    
    @abstractmethod
    def execute(self, connection: Any, query: str, params: Optional[Tuple[Any, ...]] = None) -> Any:
        """Execute a query."""
        pass
    
    @abstractmethod
    def fetchall(self, cursor: Any) -> List[Dict[str, Any]]:
        """Fetch all results from a cursor."""
        pass
    
    @abstractmethod
    def fetchone(self, cursor: Any) -> Optional[Dict[str, Any]]:
        """Fetch one result from a cursor."""
        pass
    
    @abstractmethod
    def commit(self, connection: Any) -> None:
        """Commit the transaction."""
        pass
    
    @abstractmethod
    def rollback(self, connection: Any) -> None:
        """Rollback the transaction."""
        pass
    
    @abstractmethod
    def close(self, connection: Any) -> None:
        """Close the connection."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the backend name."""
        pass
    
    @abstractmethod
    def supports_returning(self) -> bool:
        """Whether the backend supports RETURNING clause."""
        pass
    
    @abstractmethod
    def get_sql_type(self, synthdb_type: str) -> str:
        """Convert SynthDB type to backend-specific SQL type."""
        pass
    
    @abstractmethod
    def get_autoincrement_sql(self) -> str:
        """Get the SQL for auto-incrementing primary keys."""
        pass


class LocalBackend(DatabaseBackend):
    """Base class for local file-based backends."""
    
    def connect(self, connection_info: Union[str, Dict[str, Any]]) -> Any:
        """Connect using file path."""
        if isinstance(connection_info, dict):
            db_path = connection_info.get('path', 'db.db')
        else:
            db_path = connection_info
        return self._connect_file(db_path)
    
    @abstractmethod
    def _connect_file(self, db_path: str) -> Any:
        """Connect to local file database."""
        pass




class SqliteBackend(LocalBackend):
    """SQLite database backend."""
    
    def _connect_file(self, db_path: str) -> sqlite3.Connection:
        """Connect to SQLite database."""
        return sqlite3.connect(db_path)
    
    def execute(self, connection: sqlite3.Connection, query: str, params: Optional[Tuple[Any, ...]] = None) -> sqlite3.Cursor:
        """Execute a query on SQLite."""
        cursor = connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor
    
    def fetchall(self, cursor: sqlite3.Cursor) -> List[Dict[str, Any]]:
        """Fetch all results from SQLite cursor."""
        columns = [description[0] for description in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    
    def fetchone(self, cursor: sqlite3.Cursor) -> Optional[Dict[str, Any]]:
        """Fetch one result from SQLite cursor."""
        columns = [description[0] for description in cursor.description] if cursor.description else []
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None
    
    def commit(self, connection: sqlite3.Connection) -> None:
        """Commit SQLite transaction."""
        connection.commit()
    
    def rollback(self, connection: sqlite3.Connection) -> None:
        """Rollback SQLite transaction."""
        connection.rollback()
    
    def close(self, connection: sqlite3.Connection) -> None:
        """Close SQLite connection."""
        connection.close()
    
    def get_name(self) -> str:
        """Get the backend name."""
        return "sqlite"
    
    def supports_returning(self) -> bool:
        """SQLite supports RETURNING in newer versions."""
        return True
    
    def get_sql_type(self, synthdb_type: str) -> str:
        """Convert SynthDB type to SQLite SQL type."""
        type_mapping = {
            'text': 'TEXT',
            'integer': 'INTEGER',
            'real': 'REAL',
            'timestamp': 'TIMESTAMP'
        }
        return type_mapping.get(synthdb_type, 'TEXT')
    
    def get_autoincrement_sql(self) -> str:
        """Get SQLite autoincrement SQL."""
        return "INTEGER PRIMARY KEY"




class LibSQLBackend(LocalBackend):
    """LibSQL database backend (SQLite-compatible with additional features)."""
    
    def __init__(self) -> None:
        try:
            import libsql_experimental as libsql
            self._libsql = libsql
        except ImportError:
            raise ImportError(
                "LibSQL backend requires 'libsql-experimental' package. "
                "Install with: uv add libsql-experimental"
            )
    
    def _connect_file(self, db_path: str) -> Any:
        """Connect to LibSQL database."""
        # LibSQL can connect to local files or remote databases
        if db_path.startswith(('http://', 'https://', 'libsql://')):
            # Remote database
            return self._libsql.connect(db_path)
        else:
            # Local file
            return self._libsql.connect(f"file:{db_path}")
    
    def execute(self, connection: Any, query: str, params: Optional[Tuple[Any, ...]] = None) -> Any:
        """Execute a query on LibSQL."""
        cursor = connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor
    
    def fetchall(self, cursor: Any) -> List[Dict[str, Any]]:
        """Fetch all results from LibSQL cursor."""
        results = cursor.fetchall()
        if not results:
            return []
        
        # Get column names from the cursor description
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in results]
    
    def fetchone(self, cursor: Any) -> Optional[Dict[str, Any]]:
        """Fetch one result from LibSQL cursor."""
        row = cursor.fetchone()
        if not row:
            return None
        
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return dict(zip(columns, row))
    
    def commit(self, connection: Any) -> None:
        """Commit LibSQL transaction."""
        connection.commit()
    
    def rollback(self, connection: Any) -> None:
        """Rollback LibSQL transaction."""
        connection.rollback()
    
    def close(self, connection: Any) -> None:
        """Close LibSQL connection."""
        # LibSQL connections may not have a close method
        if hasattr(connection, 'close'):
            connection.close()
    
    def get_name(self) -> str:
        """Get the backend name."""
        return "libsql"
    
    def supports_returning(self) -> bool:
        """LibSQL supports RETURNING (SQLite 3.35.0+)."""
        return True
    
    def get_sql_type(self, synthdb_type: str) -> str:
        """Convert SynthDB type to LibSQL type (SQLite-compatible)."""
        type_mapping = {
            'text': 'TEXT',
            'integer': 'INTEGER',
            'real': 'REAL',
            'timestamp': 'TEXT'
        }
        return type_mapping.get(synthdb_type, 'TEXT')
    
    def get_autoincrement_sql(self) -> str:
        """Get LibSQL autoincrement SQL."""
        return "INTEGER PRIMARY KEY AUTOINCREMENT"


def get_backend(backend_name: str = "sqlite") -> DatabaseBackend:
    """Get a database backend instance."""
    if backend_name == "sqlite":
        return SqliteBackend()
    elif backend_name == "libsql":
        try:
            return LibSQLBackend()
        except ImportError:
            # Fall back to SQLite if LibSQL is not available
            print("Warning: LibSQL backend not available, falling back to SQLite")
            return SqliteBackend()
    else:
        raise ValueError(f"Unknown backend: {backend_name}. Supported backends: libsql, sqlite")


def detect_backend_from_connection(connection_info: Union[str, Dict[str, Any]]) -> str:
    """Detect which backend to use based on connection info."""
    if isinstance(connection_info, dict):
        # Local database
        path = connection_info.get('path', 'db.db')
        return detect_backend_from_path(path)
    elif isinstance(connection_info, str):
        # Treat as file path
        return detect_backend_from_path(connection_info)
    
    return "sqlite"  # Default


def detect_backend_from_path(db_path: str) -> str:
    """Detect which backend to use based on file extension or existing database."""
    # Check for remote LibSQL URLs
    if isinstance(db_path, str) and db_path.startswith(('http://', 'https://', 'libsql://')):
        return "libsql"
    
    # Default to sqlite for local files
    return "sqlite"


def parse_connection_string(connection_string: str) -> Tuple[str, Union[str, Dict[str, Any]]]:
    """Parse a connection string and return (backend, connection_info)."""
    if '://' in connection_string:
        raise ValueError(f"Unsupported connection string format: {connection_string}")
    else:
        # Treat as file path
        backend = detect_backend_from_path(connection_string)
        return backend, connection_string
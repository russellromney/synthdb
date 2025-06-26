"""Database backend abstraction layer for SynthDB."""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Tuple, Optional, Union
import sqlite3
from pathlib import Path
import re


class DatabaseBackend(ABC):
    """Abstract base class for database backends."""
    
    @abstractmethod
    def connect(self, connection_info: Union[str, Dict[str, Any]]) -> Any:
        """Connect to the database."""
        pass
    
    @abstractmethod
    def execute(self, connection: Any, query: str, params: Optional[Tuple] = None) -> Any:
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
    
    def execute(self, connection: sqlite3.Connection, query: str, params: Optional[Tuple] = None) -> sqlite3.Cursor:
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
            'boolean': 'INTEGER',  # SQLite doesn't have native boolean
            'json': 'TEXT',
            'timestamp': 'TIMESTAMP'
        }
        return type_mapping.get(synthdb_type, 'TEXT')
    
    def get_autoincrement_sql(self) -> str:
        """Get SQLite autoincrement SQL."""
        return "INTEGER PRIMARY KEY"


class LimboBackend(LocalBackend):
    """Limbo database backend."""
    
    def __init__(self):
        try:
            import limbo
            self._limbo = limbo
        except ImportError:
            raise ImportError(
                "Limbo backend requires 'pylimbo' package. Install with: pip install pylimbo"
            )
    
    def _connect_file(self, db_path: str) -> Any:
        """Connect to Limbo database."""
        return self._limbo.connect(db_path)
    
    def execute(self, connection: Any, query: str, params: Optional[Tuple] = None) -> Any:
        """Execute a query on Limbo."""
        cursor = connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor
    
    def fetchall(self, cursor: Any) -> List[Dict[str, Any]]:
        """Fetch all results from Limbo cursor."""
        results = cursor.fetchall()
        if not results:
            return []
        
        # Get column names from the cursor description
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in results]
    
    def fetchone(self, cursor: Any) -> Optional[Dict[str, Any]]:
        """Fetch one result from Limbo cursor."""
        row = cursor.fetchone()
        if not row:
            return None
        
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return dict(zip(columns, row))
    
    def commit(self, connection: Any) -> None:
        """Commit Limbo transaction."""
        connection.commit()
    
    def rollback(self, connection: Any) -> None:
        """Rollback Limbo transaction."""
        connection.rollback()
    
    def close(self, connection: Any) -> None:
        """Close Limbo connection."""
        connection.close()
    
    def get_name(self) -> str:
        """Get the backend name."""
        return "limbo"
    
    def supports_returning(self) -> bool:
        """Limbo supports RETURNING (SQLite-compatible)."""
        return True
    
    def get_sql_type(self, synthdb_type: str) -> str:
        """Convert SynthDB type to Limbo SQL type."""
        # Limbo is SQLite-compatible
        type_mapping = {
            'text': 'TEXT',
            'integer': 'INTEGER',
            'real': 'REAL',
            'boolean': 'INTEGER',
            'json': 'TEXT',
            'timestamp': 'TIMESTAMP'
        }
        return type_mapping.get(synthdb_type, 'TEXT')
    
    def get_autoincrement_sql(self) -> str:
        """Get Limbo autoincrement SQL."""
        return "INTEGER PRIMARY KEY"


def get_backend(backend_name: str = "limbo") -> DatabaseBackend:
    """Get a database backend instance."""
    if backend_name == "sqlite":
        return SqliteBackend()
    elif backend_name == "limbo":
        try:
            return LimboBackend()
        except ImportError:
            # Fall back to SQLite if Limbo is not available
            print("Warning: Limbo backend not available, falling back to SQLite")
            return SqliteBackend()
    else:
        raise ValueError(f"Unknown backend: {backend_name}. Supported backends: limbo, sqlite")


def detect_backend_from_connection(connection_info: Union[str, Dict[str, Any]]) -> str:
    """Detect which backend to use based on connection info."""
    if isinstance(connection_info, dict):
        # Local database
        path = connection_info.get('path', 'db.db')
        return detect_backend_from_path(path)
    elif isinstance(connection_info, str):
        # Treat as file path
        return detect_backend_from_path(connection_info)
    
    return "limbo"  # Default


def detect_backend_from_path(db_path: str) -> str:
    """Detect which backend to use based on file extension or existing database."""
    path = Path(db_path)
    
    # Check file extension hints
    if path.suffix in ('.sqlite', '.sqlite3', '.db'):
        return "sqlite"
    elif path.suffix == '.limbo':
        return "limbo"
    
    # If file exists, try to detect the backend
    if path.exists():
        # For now, assume SQLite for existing files unless explicitly specified
        # In the future, we could add magic number detection
        return "sqlite"
    
    # For new files, use limbo by default (with fallback)
    return "limbo"


def parse_connection_string(connection_string: str) -> Tuple[str, Union[str, Dict[str, Any]]]:
    """Parse a connection string and return (backend, connection_info)."""
    if '://' in connection_string:
        raise ValueError(f"Unsupported connection string format: {connection_string}")
    else:
        # Treat as file path
        backend = detect_backend_from_path(connection_string)
        return backend, connection_string
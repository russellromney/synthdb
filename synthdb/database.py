"""Database setup and connection management for SynthDB."""

import sqlite3
from .backends import get_backend, detect_backend_from_connection
from .config import config
from .schema import create_schema


def do_statement(s: str, many: bool = False, db_path: str = 'db.db', backend_name: str = None):
    """Execute a SQL statement on the database."""
    # Get the appropriate backend
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    backend = get_backend(backend_to_use)
    
    db = backend.connect(db_path)
    print(s)
    
    if many:
        # For multiple statements, split and execute individually
        statements = [stmt.strip() for stmt in s.split(';') if stmt.strip()]
        for stmt in statements:
            backend.execute(db, stmt)
    else: 
        backend.execute(db, s)
    
    backend.commit(db)
    backend.close(db)


def make_db(connection_info = 'db.db', backend_name: str = None):
    """Initialize the SynthDB database with all required tables."""
    # Get the appropriate backend
    if backend_name:
        backend_to_use = backend_name
    else:
        backend_to_use = detect_backend_from_connection(connection_info)
    
    backend = get_backend(backend_to_use)
    connection = backend.connect(connection_info)
    
    try:
        # Use the new schema creation system
        create_schema(backend, connection)
        print(f"Successfully initialized SynthDB using {backend_to_use} backend")
    except Exception as e:
        backend.rollback(connection)
        raise e
    finally:
        backend.close(connection)

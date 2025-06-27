"""Database setup and connection management for SynthDB."""

from .backends import get_backend, detect_backend_from_connection
from .schema import create_schema
from typing import Optional, Any



def make_db(connection_info: str | dict[str, Any] = 'db.db', backend_name: Optional[str] = None) -> None:
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

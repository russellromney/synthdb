"""Transaction management for SynthDB operations."""

from contextlib import contextmanager
from typing import Any, Optional, Tuple, Generator


@contextmanager
def transaction_context(connection_info: Any, backend_name: Optional[str] = None) -> Generator[Tuple[Any, Any], None, None]:
    """
    Context manager that provides a shared database connection with transaction management.
    
    Ensures ACID guarantees by:
    - Using a single connection for multiple operations
    - Automatically committing on successful completion
    - Rolling back all changes if any operation fails
    
    Args:
        connection_info: Database connection information
        backend_name: Optional backend name override
        
    Yields:
        Tuple of (backend, connection) for use in operations
        
    Example:
        with transaction_context(db_path, 'sqlite') as (backend, conn):
            insert_typed_value(..., backend=backend, connection=conn)
            add_column(..., backend=backend, connection=conn)
            # Both operations committed atomically
    """
    from .backends import get_backend, detect_backend_from_connection
    
    # Determine backend
    if backend_name:
        backend_to_use = backend_name
    else:
        backend_to_use = detect_backend_from_connection(connection_info)
    
    backend = get_backend(backend_to_use)
    connection = None
    
    try:
        # Establish connection
        connection = backend.connect(connection_info)
        
        # Begin transaction (for backends that support explicit transactions)
        if hasattr(backend, 'begin_transaction'):
            backend.begin_transaction(connection)
        
        # Yield backend and connection to caller
        yield backend, connection
        
        # Commit transaction on successful completion
        backend.commit(connection)
        
    except Exception as e:
        # Rollback on any error
        if connection:
            try:
                backend.rollback(connection)
            except Exception:
                # Ignore rollback errors, the original exception is more important
                pass
        raise e
        
    finally:
        # Always close connection
        if connection:
            try:
                backend.close(connection)
            except Exception:
                # Ignore close errors
                pass


@contextmanager
def bulk_transaction_context(connection_info: Any, backend_name: Optional[str] = None, 
                           batch_size: int = 5000) -> Generator[Tuple[Any, Any, int], None, None]:
    """
    Context manager optimized for bulk operations with configurable batch size.
    
    Args:
        connection_info: Database connection information  
        backend_name: Optional backend name override
        batch_size: Number of operations per batch before intermediate commit
        
    Yields:
        Tuple of (backend, connection, batch_size) for use in bulk operations
    """
    with transaction_context(connection_info, backend_name) as (backend, connection):
        yield backend, connection, batch_size


def is_transactional_operation(operation_name: str) -> bool:
    """
    Check if an operation should be wrapped in a transaction.
    
    Args:
        operation_name: Name of the operation
        
    Returns:
        True if operation should use transactions
    """
    transactional_ops = {
        'insert_typed_value',
        'create_table', 
        'add_column',
        'bulk_insert_rows',
        'create_table_from_data'
    }
    return operation_name in transactional_ops


def get_operation_timeout(operation_name: str) -> int:
    """
    Get appropriate timeout for different operation types.
    
    Args:
        operation_name: Name of the operation
        
    Returns:
        Timeout in seconds
    """
    timeouts = {
        'insert_typed_value': 30,
        'bulk_insert_rows': 300,  # 5 minutes for bulk operations
        'create_table': 60,
        'add_column': 60,
        'create_table_from_data': 180  # 3 minutes for schema inference
    }
    return timeouts.get(operation_name, 30)
"""Bulk operations for efficient data insertion and manipulation in SynthDB."""

import csv
import json
from typing import List, Dict, Any
from pathlib import Path
from .inference import create_table_from_data, suggest_column_types
from .utils import list_tables, list_columns
from .core import add_column, insert_typed_value


def bulk_insert_rows(table_name: str, data: List[Dict[str, Any]], 
                    connection_info = 'db.db', backend_name: str = None,
                    create_missing_columns: bool = True) -> Dict[str, int]:
    """
    Insert multiple rows into a table efficiently.
    
    Args:
        table_name: Name of the target table
        data: List of dictionaries representing rows
        connection_info: Database connection information
        backend_name: Backend to use
        create_missing_columns: Whether to create missing columns automatically
        
    Returns:
        Dictionary with statistics: {'inserted': count, 'errors': count}
    """
    if not data:
        return {'inserted': 0, 'errors': 0}
    
    from .backends import detect_backend_from_connection
    
    # Get backend
    if backend_name:
        backend_to_use = backend_name
    else:
        backend_to_use = detect_backend_from_connection(connection_info)
    
    # Check if table exists
    try:
        tables = list_tables(connection_info, backend_name)
        table_exists = any(t['name'] == table_name for t in tables)
        
        if not table_exists:
            raise ValueError(f"Table '{table_name}' does not exist. Create it first.")
        
        # Get existing columns
        existing_columns = list_columns(table_name, False, connection_info, backend_name)
        existing_column_names = {col['name']: col for col in existing_columns}
        
        # Find missing columns
        all_column_names = set()
        for row in data:
            all_column_names.update(row.keys())
        
        missing_columns = all_column_names - set(existing_column_names.keys())
        
        if missing_columns and create_missing_columns:
            # Infer types for missing columns
            column_suggestions = suggest_column_types(data)
            
            for col_name in missing_columns:
                col_type = column_suggestions.get(col_name, 'text')
                add_column(table_name, col_name, col_type, connection_info, backend_name)
                print(f"Created column '{col_name}' with type '{col_type}'")
            
            # Refresh column list
            existing_columns = list_columns(table_name, False, connection_info, backend_name)
            existing_column_names = {col['name']: col for col in existing_columns}
        
        elif missing_columns:
            raise ValueError(f"Missing columns: {', '.join(missing_columns)}. Set create_missing_columns=True to auto-create.")
        
        # Get table info
        table_info = next((t for t in tables if t['name'] == table_name), None)
        table_id = table_info['id']
        
        # Batch insert with proper transaction handling
        stats = {'inserted': 0, 'errors': 0}
        
        from .transactions import transaction_context
        
        # Process all data in a single transaction for ACID guarantees
        with transaction_context(connection_info, backend_to_use) as (txn_backend, txn_connection):
            # Handle schema changes first (if any missing columns)
            if missing_columns and create_missing_columns:
                # Add columns in same transaction as data
                column_suggestions = suggest_column_types(data)
                
                for col_name in missing_columns:
                    col_type = column_suggestions.get(col_name, 'text')
                    add_column(table_name, col_name, col_type, connection_info, backend_name,
                             backend=txn_backend, connection=txn_connection)
                    print(f"Created column '{col_name}' with type '{col_type}'")
                
                # Refresh column list
                existing_columns = list_columns(table_name, False, connection_info, backend_name)
                existing_column_names = {col['name']: col for col in existing_columns}
            
            # Insert all rows in the same transaction
            for row_idx, row in enumerate(data):
                row_id = row_idx  # Use sequential row IDs
                
                for col_name, value in row.items():
                    if col_name in existing_column_names:
                        column_info = existing_column_names[col_name]
                        column_id = column_info['id']
                        column_type = column_info['data_type']
                        
                        try:
                            # Insert using shared transaction
                            insert_typed_value(
                                row_id, table_id, column_id, value, column_type,
                                backend=txn_backend, connection=txn_connection
                            )
                            stats['inserted'] += 1
                        except Exception as e:
                            stats['errors'] += 1
                            print(f"Error inserting {col_name}={value} for row {row_id}: {e}")
                            # Continue with other values, but transaction will rollback if any error occurs
            
            # Transaction commits automatically on successful completion
        
        return stats
        
    except Exception as e:
        raise ValueError(f"Bulk insert failed: {e}")


def load_csv(file_path: str, table_name: str = None, 
            connection_info = 'db.db', backend_name: str = None,
            create_table: bool = True, delimiter: str = ',',
            encoding: str = 'utf-8') -> Dict[str, Any]:
    """
    Load data from CSV file into SynthDB.
    
    Args:
        file_path: Path to CSV file
        table_name: Name of target table (defaults to filename)
        connection_info: Database connection information
        backend_name: Backend to use
        create_table: Whether to create table if it doesn't exist
        delimiter: CSV delimiter
        encoding: File encoding
        
    Returns:
        Dictionary with load statistics
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")
    
    if table_name is None:
        table_name = file_path.stem
    
    # Read CSV data
    data = []
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                # Convert empty strings to None
                cleaned_row = {k: (None if v == '' else v) for k, v in row.items()}
                data.append(cleaned_row)
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")
    
    if not data:
        raise ValueError("CSV file is empty or has no data rows")
    
    # Create table if needed
    if create_table:
        try:
            tables = list_tables(connection_info, backend_name)
            table_exists = any(t['name'] == table_name for t in tables)
            
            if not table_exists:
                create_table_from_data(table_name, data, connection_info, backend_name)
                print(f"Created table '{table_name}' with inferred schema")
        except Exception as e:
            raise ValueError(f"Error creating table: {e}")
    
    # Bulk insert data
    stats = bulk_insert_rows(table_name, data, connection_info, backend_name)
    
    return {
        'table_name': table_name,
        'file_path': str(file_path),
        'rows_processed': len(data),
        **stats
    }


def load_json(file_path: str, table_name: str = None,
             connection_info = 'db.db', backend_name: str = None,
             create_table: bool = True, json_key: str = None) -> Dict[str, Any]:
    """
    Load data from JSON file into SynthDB.
    
    Args:
        file_path: Path to JSON file
        table_name: Name of target table (defaults to filename)
        connection_info: Database connection information
        backend_name: Backend to use
        create_table: Whether to create table if it doesn't exist
        json_key: Key to extract array from (if JSON is object with array inside)
        
    Returns:
        Dictionary with load statistics
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")
    
    if table_name is None:
        table_name = file_path.stem
    
    # Read JSON data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except Exception as e:
        raise ValueError(f"Error reading JSON file: {e}")
    
    # Extract data array
    if json_key:
        if not isinstance(json_data, dict) or json_key not in json_data:
            raise ValueError(f"JSON key '{json_key}' not found in file")
        data = json_data[json_key]
    else:
        data = json_data
    
    if not isinstance(data, list):
        raise ValueError("JSON data must be an array of objects")
    
    if not data:
        raise ValueError("JSON array is empty")
    
    # Validate that all items are objects
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} is not an object")
    
    # Create table if needed
    if create_table:
        try:
            tables = list_tables(connection_info, backend_name)
            table_exists = any(t['name'] == table_name for t in tables)
            
            if not table_exists:
                create_table_from_data(table_name, data, connection_info, backend_name)
                print(f"Created table '{table_name}' with inferred schema")
        except Exception as e:
            raise ValueError(f"Error creating table: {e}")
    
    # Bulk insert data
    stats = bulk_insert_rows(table_name, data, connection_info, backend_name)
    
    return {
        'table_name': table_name,
        'file_path': str(file_path),
        'rows_processed': len(data),
        **stats
    }


def export_csv(table_name: str, file_path: str,
              connection_info = 'db.db', backend_name: str = None,
              where_clause: str = None, delimiter: str = ',') -> Dict[str, Any]:
    """
    Export table data to CSV file.
    
    Args:
        table_name: Name of source table
        file_path: Output CSV file path
        connection_info: Database connection information
        backend_name: Backend to use
        where_clause: Optional WHERE clause for filtering
        delimiter: CSV delimiter
        
    Returns:
        Export statistics
    """
    from .utils import query_view
    
    # Query data
    try:
        data = query_view(table_name, where_clause, connection_info, backend_name)
    except Exception as e:
        raise ValueError(f"Error querying table: {e}")
    
    if not data:
        raise ValueError(f"No data found in table '{table_name}'")
    
    # Write CSV
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys(), delimiter=delimiter)
            writer.writeheader()
            writer.writerows(data)
    except Exception as e:
        raise ValueError(f"Error writing CSV file: {e}")
    
    return {
        'table_name': table_name,
        'file_path': file_path,
        'rows_exported': len(data)
    }


def export_json(table_name: str, file_path: str,
               connection_info = 'db.db', backend_name: str = None,
               where_clause: str = None, indent: int = 2) -> Dict[str, Any]:
    """
    Export table data to JSON file.
    
    Args:
        table_name: Name of source table
        file_path: Output JSON file path
        connection_info: Database connection information
        backend_name: Backend to use
        where_clause: Optional WHERE clause for filtering
        indent: JSON indentation
        
    Returns:
        Export statistics
    """
    from .utils import query_view
    
    # Query data
    try:
        data = query_view(table_name, where_clause, connection_info, backend_name)
    except Exception as e:
        raise ValueError(f"Error querying table: {e}")
    
    if not data:
        data = []
    
    # Write JSON
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, default=str)
    except Exception as e:
        raise ValueError(f"Error writing JSON file: {e}")
    
    return {
        'table_name': table_name,
        'file_path': file_path,
        'rows_exported': len(data)
    }
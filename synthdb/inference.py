"""Type inference for automatic data type detection in SynthDB."""

import re
from datetime import datetime
from typing import Any, Tuple, Optional, List, Dict
from dateutil import parser as date_parser


def infer_type(value: Any) -> Tuple[str, Any]:
    """
    Infer the SynthDB type from a Python value.
    
    Returns:
        Tuple of (synthdb_type, converted_value)
    """
    if value is None:
        raise ValueError("Cannot infer a type from a null value")

    
    # Handle explicit types first
    if isinstance(value, int):
        return "integer", value
    elif isinstance(value, float):
        return "real", value
    elif isinstance(value, datetime):
        return "timestamp", value
    elif isinstance(value, str):
        return "text", value
    else:
        # only those types are valid, raise an error otherwise
        raise ValueError("Only allowed types are integer, real (float), timestamp, and text")


def infer_column_type(values: List[Any]) -> str:
    """
    Infer the best column type from a list of values.
    
    Uses majority voting with type hierarchy:
    timestamp > real > integer > text
    """
    if not values:
        return "text"
    
    # Count types
    type_counts = {}
    non_null_values = [v for v in values if v is not None]
    
    if not non_null_values:
        return "text"
    
    for value in non_null_values:
        inferred_type, _ = infer_type(value)
        type_counts[inferred_type] = type_counts.get(inferred_type, 0) + 1
    
    # Type hierarchy - more specific types win
    type_hierarchy = ["timestamp", "real", "integer", "text"]
    
    # If we have a clear majority (>50%), use that
    total_count = len(non_null_values)
    for data_type in type_hierarchy:
        if type_counts.get(data_type, 0) > total_count * 0.5:
            return data_type
    
    # Otherwise, pick the most specific type that appears
    for data_type in type_hierarchy:
        if type_counts.get(data_type, 0) > 0:
            return data_type
    
    return "text"


def smart_insert(table_name: str, row_id: int, column_name: str, value: Any, 
                connection_info = 'db.db', backend_name: str = None) -> Tuple[str, Any]:
    """
    Insert a value with automatic type inference.
    
    Returns:
        Tuple of (inferred_type, converted_value)
    """
    from .core import insert_typed_value
    from .utils import list_columns
    
    # Infer the type
    inferred_type, converted_value = infer_type(value)
    
    try:
        # Check if column exists and has a defined type
        columns = list_columns(table_name, connection_info, backend_name)
        existing_column = next((c for c in columns if c['name'] == column_name), None)
        
        if existing_column:
            # Use existing column type
            column_type = existing_column['data_type']
            converted_value = converted_value
        else:
            # Create new column with inferred type
            from .core import add_column
            add_column(table_name, column_name, inferred_type, connection_info, backend_name)
            column_type = inferred_type
        
        # Get table and column IDs for insertion
        from .utils import list_tables
        tables = list_tables(connection_info, backend_name)
        table_info = next((t for t in tables if t['name'] == table_name), None)
        
        if not table_info:
            raise ValueError(f"Table '{table_name}' not found")
        
        columns = list_columns(table_name, connection_info, backend_name)
        column_info = next((c for c in columns if c['name'] == column_name), None)
        
        if not column_info:
            raise ValueError(f"Column '{column_name}' not found in table '{table_name}'")
        
        # Insert the value
        try:
            insert_typed_value(row_id, table_info['id'], column_info['id'], 
                              converted_value, column_type, connection_info, backend_name)
        except (ValueError, TypeError) as insert_error:
            # Provide helpful error message for type mismatches
            if existing_column and inferred_type != column_type:
                raise TypeError(
                    f"Type mismatch: Cannot insert {inferred_type} value '{value}' "
                    f"into {column_type} column '{column_name}'. "
                    f"Expected {column_type}, got {inferred_type}. "
                    f"Suggestion: Convert the value to {column_type} before inserting."
                ) from insert_error
            else:
                raise TypeError(f"Failed to insert value '{value}' into column '{column_name}': {insert_error}") from insert_error
        
        return column_type, converted_value
        
    except Exception as e:
        raise ValueError(f"Failed to insert value: {e}")


def convert_value_to_type(value: Any, target_type: str) -> Any:
    """
    Convert a value to match a target SynthDB type.
    
    WARNING: This function performs aggressive type conversion and should be used 
    sparingly. Consider letting users explicitly convert values instead of doing 
    automatic conversions that may lead to unexpected behavior.
    """
    if target_type == "text":
        return str(value) if value is not None else None
    elif target_type == "integer":
        if isinstance(value, str):
            return int(float(value))  # Handle "1.0" -> 1
        return int(value)
    elif target_type == "real":
        return float(value)
    elif target_type == "timestamp":
        if isinstance(value, str):
            return date_parser.parse(value)
        return value
    else:
        return value


def suggest_column_types(data: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Suggest column types for a dataset.
    
    Args:
        data: List of dictionaries representing rows
        
    Returns:
        Dictionary mapping column names to suggested types
    """
    if not data:
        return {}
    
    # Collect all column names
    all_columns = set()
    for row in data:
        all_columns.update(row.keys())
    
    # Analyze each column
    suggestions = {}
    for column in all_columns:
        values = [row.get(column) for row in data]
        suggestions[column] = infer_column_type(values)
    
    return suggestions


def create_table_from_data(table_name: str, data: List[Dict[str, Any]], 
                          connection_info = 'db.db', backend_name: str = None) -> Dict[str, str]:
    """
    Create a table and columns automatically from data with type inference.
    
    Returns:
        Dictionary mapping column names to their inferred types
    """
    from .core import create_table, add_column
    
    if not data:
        raise ValueError("Cannot create table from empty data")
    
    # Create the table
    create_table(table_name, connection_info, backend_name)
    
    # Infer column types
    column_types = suggest_column_types(data)
    
    # Create columns
    for column_name, column_type in column_types.items():
        add_column(table_name, column_name, column_type, connection_info, backend_name)
    
    return column_types
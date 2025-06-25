"""Type inference for automatic data type detection in SynthDB."""

import json
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
        return "text", None
    
    # Handle explicit types first
    if isinstance(value, bool):
        return "boolean", value
    elif isinstance(value, int):
        return "integer", value
    elif isinstance(value, float):
        return "real", value
    elif isinstance(value, (dict, list)):
        return "json", value
    elif isinstance(value, datetime):
        return "timestamp", value
    elif isinstance(value, str):
        return infer_string_type(value)
    else:
        # Fallback to string representation
        return "text", str(value)


def infer_string_type(value: str) -> Tuple[str, Any]:
    """
    Infer type from string value by trying different parsers.
    
    Priority order:
    1. Boolean (true/false, yes/no, 1/0)
    2. Integer
    3. Real/Float
    4. JSON (objects/arrays)
    5. Timestamp/Date
    6. Text (fallback)
    """
    if not value or not isinstance(value, str):
        return "text", value
    
    value_lower = value.lower().strip()
    
    # Boolean detection
    if value_lower in ("true", "false", "yes", "no", "1", "0", "on", "off"):
        boolean_value = value_lower in ("true", "yes", "1", "on")
        return "boolean", boolean_value
    
    # Integer detection
    try:
        # Handle common integer formats
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return "integer", int(value)
    except ValueError:
        pass
    
    # Float detection
    try:
        # Handle scientific notation, decimals
        if '.' in value or 'e' in value_lower or 'E' in value:
            float_val = float(value)
            # If it's actually a whole number, keep as integer
            if float_val.is_integer() and '.' not in value and 'e' not in value_lower:
                return "integer", int(float_val)
            return "real", float_val
    except ValueError:
        pass
    
    # JSON detection
    try:
        if (value.startswith(('{', '[')) and value.endswith(('}', ']'))) or value_lower in ('null',):
            json_val = json.loads(value)
            return "json", json_val
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Timestamp detection
    try:
        # Try to parse various date/time formats
        if re.match(r'\d{4}-\d{2}-\d{2}', value) or re.match(r'\d{2}/\d{2}/\d{4}', value):
            parsed_date = date_parser.parse(value)
            return "timestamp", parsed_date
    except (ValueError, date_parser.ParserError):
        pass
    
    # Fallback to text
    return "text", value


def infer_column_type(values: List[Any]) -> str:
    """
    Infer the best column type from a list of values.
    
    Uses majority voting with type hierarchy:
    timestamp > json > real > integer > boolean > text
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
    type_hierarchy = ["timestamp", "json", "real", "integer", "boolean", "text"]
    
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
            # Use existing column type if it exists
            column_type = existing_column['data_type']
            # Convert value to match existing column type
            if column_type != inferred_type:
                converted_value = convert_value_to_type(value, column_type)
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
        insert_typed_value(row_id, table_info['id'], column_info['id'], 
                          converted_value, column_type, connection_info, backend_name)
        
        return column_type, converted_value
        
    except Exception as e:
        raise ValueError(f"Failed to insert value: {e}")


def convert_value_to_type(value: Any, target_type: str) -> Any:
    """Convert a value to match a target SynthDB type."""
    if target_type == "text":
        return str(value) if value is not None else None
    elif target_type == "integer":
        if isinstance(value, str):
            return int(float(value))  # Handle "1.0" -> 1
        return int(value)
    elif target_type == "real":
        return float(value)
    elif target_type == "boolean":
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", "on")
        return bool(value)
    elif target_type == "json":
        if isinstance(value, str):
            return json.loads(value)
        return value
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
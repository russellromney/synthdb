"""Constants for SynthDB, including protected names and reserved identifiers."""

# Protected column names that cannot be used for user-defined columns
PROTECTED_COLUMN_NAMES = {
    'row_id',  # Reserved for SynthDB's internal row identifier
}

# Core internal table names that cannot be used for user-defined tables
PROTECTED_TABLE_NAMES = {
    # Core metadata tables
    'table_definitions',
    'column_definitions', 
    'row_id_sequence',
    
    # Value storage tables
    'text_values',
    'integer_values', 
    'real_values',
    'boolean_values',
    'json_values',
    'timestamp_values',
    
    # History/audit tables
    'text_value_history',
    'integer_value_history',
    'real_value_history', 
    'boolean_value_history',
    'json_value_history',
    'timestamp_value_history',
}

def validate_column_name(column_name: str) -> None:
    """
    Validate that a column name is not protected.
    
    Args:
        column_name: The column name to validate
        
    Raises:
        ValueError: If the column name is protected
    """
    if column_name.lower() in PROTECTED_COLUMN_NAMES:
        raise ValueError(
            f"Column name '{column_name}' is protected and cannot be used. "
            f"Protected column names: {', '.join(sorted(PROTECTED_COLUMN_NAMES))}"
        )

def validate_table_name(table_name: str) -> None:
    """
    Validate that a table name is not a core internal table.
    
    Args:
        table_name: The table name to validate
        
    Raises:
        ValueError: If the table name conflicts with internal tables
    """
    if table_name.lower() in PROTECTED_TABLE_NAMES:
        raise ValueError(
            f"Table name '{table_name}' conflicts with internal SynthDB tables and cannot be used. "
            f"Please choose a different name."
        )
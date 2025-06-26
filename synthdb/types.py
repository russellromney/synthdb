"""Type mapping utilities for SynthDB."""


def get_type_table_name(data_type, is_history=False):
    """Get the appropriate table name for a given data type.
    
    Note: is_history parameter is deprecated but kept for backward compatibility.
    All data (current and historical) is now stored in the same versioned tables.
    """
    type_map = {
        'text': 'text_values',
        'boolean': 'boolean_values', 
        'real': 'real_values',
        'integer': 'integer_values',
        'json': 'json_values',
        'timestamp': 'timestamp_values'
    }
    
    # Always return the main table name since we use versioned storage
    return type_map[data_type]
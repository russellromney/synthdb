"""Type mapping utilities for SynthDB."""


def get_type_table_name(data_type, is_history=False):
    """Get the appropriate table name for a given data type.
    
    Supported types: text, integer, real, timestamp
    
    Note: is_history parameter is deprecated but kept for backward compatibility.
    All data (current and historical) is now stored in the same versioned tables.
    """
    type_map = {
        'text': 'text_values',
        'integer': 'integer_values',
        'real': 'real_values',
        'timestamp': 'timestamp_values'
    }
    
    if data_type not in type_map:
        raise ValueError(f"Unsupported data type: {data_type}. Supported types: {', '.join(type_map.keys())}")
    
    # Always return the main table name since we use versioned storage
    return type_map[data_type]
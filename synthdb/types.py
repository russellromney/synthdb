"""Type mapping utilities for SynthDB."""


def get_type_table_name(data_type, is_history=False):
    """Get the appropriate table name for a given data type"""
    type_map = {
        'text': 'text_values',
        'boolean': 'boolean_values', 
        'real': 'real_values',
        'integer': 'integer_values',
        'json': 'json_values',
        'timestamp': 'timestamp_values'
    }
    
    if is_history:
        return type_map[data_type].replace('_values', '_value_history')
    return type_map[data_type]
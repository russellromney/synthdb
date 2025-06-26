"""
Helper functions for SynthDB tests.
"""

def assert_valid_uuid(uuid_str):
    """Assert that a string is a valid UUID."""
    import uuid
    try:
        uuid.UUID(uuid_str)
        return True
    except (ValueError, TypeError):
        return False

def is_uuid_format(value):
    """Check if a value looks like a UUID (36 chars with 4 dashes)."""
    return isinstance(value, str) and len(value) == 36 and value.count('-') == 4

def assert_uuid_or_custom_id(row_id):
    """Assert that row_id is either a valid UUID or a custom string ID."""
    assert isinstance(row_id, str), f"Expected string row_id, got {type(row_id)}: {row_id}"
    # Allow either UUID format or custom string IDs
    if len(row_id) == 36 and row_id.count('-') == 4:
        # Looks like UUID, validate it
        assert assert_valid_uuid(row_id), f"Invalid UUID format: {row_id}"
    # Otherwise, just accept it as a custom string ID
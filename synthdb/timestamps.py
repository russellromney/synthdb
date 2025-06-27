"""Timestamp utilities for SynthDB with millisecond precision.

All timestamps in SynthDB use exactly 3 decimal places of precision.
Format: YYYY-MM-DD HH:MM:SS.fff
"""

from datetime import datetime, timezone
from typing import Union
import re


# Regex pattern for our millisecond timestamp format
TIMESTAMP_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$')


def get_current_timestamp() -> str:
    """
    Get current timestamp with exactly 3 decimal places of millisecond precision.
    
    Returns:
        String timestamp in format: YYYY-MM-DD HH:MM:SS.fff
    """
    # Get current UTC time
    now = datetime.now(timezone.utc)
    
    # Format with exactly 3 decimal places (milliseconds)
    # First get the base format
    base = now.strftime('%Y-%m-%d %H:%M:%S')
    
    # Get milliseconds from microseconds (first 3 digits)
    milliseconds = now.microsecond // 1000
    milliseconds_str = f"{milliseconds:03d}"
    
    return f"{base}.{milliseconds_str}"


def format_timestamp(dt: Union[datetime, str]) -> str:
    """
    Format a datetime object or string to our standard millisecond format.
    
    Args:
        dt: datetime object or string to format
        
    Returns:
        String timestamp with exactly 3 decimal places
    """
    if isinstance(dt, str):
        # If it's already in our format, return as-is
        if TIMESTAMP_PATTERN.match(dt):
            return dt
        # Otherwise parse and format
        dt = parse_timestamp(dt)
    
    # Ensure we have a datetime object
    if not isinstance(dt, datetime):
        raise ValueError(f"Expected datetime or string, got {type(dt)}")
    
    # Format with exactly 3 decimal places
    base = dt.strftime('%Y-%m-%d %H:%M:%S')
    milliseconds = dt.microsecond // 1000
    milliseconds_str = f"{milliseconds:03d}"
    
    return f"{base}.{milliseconds_str}"


def parse_timestamp(timestamp_str: str) -> datetime:
    """
    Parse a timestamp string to datetime object.
    
    Args:
        timestamp_str: Timestamp string to parse
        
    Returns:
        datetime object with microsecond precision
    """
    if not isinstance(timestamp_str, str):
        raise ValueError(f"Expected string, got {type(timestamp_str)}")
    
    # Check if it matches our standard format
    if TIMESTAMP_PATTERN.match(timestamp_str):
        # Parse our standard format: YYYY-MM-DD HH:MM:SS.fff
        # strptime expects microseconds, so we need to pad to 6 digits
        base, millis = timestamp_str.rsplit('.', 1)
        microseconds = millis.ljust(6, '0')  # Pad with zeros to get 6 digits
        full_timestamp = f"{base}.{microseconds}"
        return datetime.strptime(full_timestamp, '%Y-%m-%d %H:%M:%S.%f')
    
    # Try other common formats
    try:
        # ISO format with T separator
        if 'T' in timestamp_str:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        # Standard datetime without microseconds
        elif '.' not in timestamp_str:
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        else:
            # Try with variable microsecond precision
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
    except ValueError as e:
        raise ValueError(f"Cannot parse timestamp '{timestamp_str}': {e}")


def timestamp_to_iso(timestamp_str: str) -> str:
    """
    Convert our timestamp format to ISO-8601 with milliseconds.
    
    Args:
        timestamp_str: Timestamp in our format
        
    Returns:
        ISO-8601 formatted string with milliseconds
    """
    dt = parse_timestamp(timestamp_str)
    return dt.isoformat(timespec='milliseconds')


def ensure_millisecond_precision(timestamp_str: str) -> str:
    """
    Ensure a timestamp has exactly 3 decimal places.
    
    Args:
        timestamp_str: Timestamp string
        
    Returns:
        Timestamp with exactly 3 decimal places
    """
    return format_timestamp(parse_timestamp(timestamp_str))


def sql_timestamp_function() -> str:
    """
    Get the SQL function for generating timestamps with millisecond precision.
    
    Returns:
        SQL function string for use in queries
    """
    return "strftime('%Y-%m-%d %H:%M:%f', 'now')"


def compare_timestamps(ts1: str, ts2: str) -> int:
    """
    Compare two timestamps.
    
    Args:
        ts1: First timestamp
        ts2: Second timestamp
        
    Returns:
        -1 if ts1 < ts2, 0 if equal, 1 if ts1 > ts2
    """
    dt1 = parse_timestamp(ts1)
    dt2 = parse_timestamp(ts2)
    
    if dt1 < dt2:
        return -1
    elif dt1 > dt2:
        return 1
    else:
        return 0


def add_microseconds(timestamp_str: str, microseconds: int) -> str:
    """
    Add microseconds to a timestamp.
    
    Args:
        timestamp_str: Base timestamp
        microseconds: Number of microseconds to add (can be negative)
        
    Returns:
        New timestamp with microseconds added
    """
    from datetime import timedelta
    
    dt = parse_timestamp(timestamp_str)
    new_dt = dt + timedelta(microseconds=microseconds)
    return format_timestamp(new_dt)
"""Tests for SynthDB database initialization."""

import sqlite3
import tempfile
import os
from synthdb.database import make_db


def test_make_db():
    """Test database initialization creates all required tables"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database
        make_db(db_path)
        
        # Connect and verify tables exist
        db = sqlite3.connect(db_path)
        cur = db.cursor()
        
        # Get all table names
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [row[0] for row in cur.fetchall()]
        
        # Check that all required tables exist
        required_tables = [
            'table_definitions',
            'column_definitions',
            'row_metadata',
            'text_values',
            'real_values',
            'integer_values', 
            'timestamp_values'
        ]
        
        for table in required_tables:
            assert table in table_names, f"Table '{table}' should exist"
        
        # Verify table_definitions structure
        cur.execute("PRAGMA table_info(table_definitions)")
        columns = [row[1] for row in cur.fetchall()]
        expected_columns = ['id', 'version', 'created_at', 'deleted_at', 'name']
        for col in expected_columns:
            assert col in columns, f"Column '{col}' should exist in table_definitions"
        
        # Verify column_definitions structure
        cur.execute("PRAGMA table_info(column_definitions)")
        columns = [row[1] for row in cur.fetchall()]
        expected_columns = ['id', 'table_id', 'version', 'created_at', 'deleted_at', 'name', 'data_type']
        for col in expected_columns:
            assert col in columns, f"Column '{col}' should exist in column_definitions"
        
        # Verify a type-specific table structure (text_values)
        cur.execute("PRAGMA table_info(text_values)")
        columns = [row[1] for row in cur.fetchall()]
        expected_columns = ['id', 'table_id', 'column_id', 'version', 'created_at', 'value', 'is_current']
        for col in expected_columns:
            assert col in columns, f"Column '{col}' should exist in text_values"
        
        db.close()
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)
"""Tests for core SynthDB operations."""

import pytest
import sqlite3
import tempfile
import os
import synthdb


def test_create_table(temp_db):
    """Test creating a new table"""
    # Create a new table using connection API
    db = synthdb.connect(temp_db, backend='sqlite')
    table_id = db.create_table("products")
    
    # Verify table was created
    db = sqlite3.connect(temp_db)
    cur = db.cursor()
    result = cur.execute(
        "SELECT id, name FROM table_definitions WHERE name = 'products'"
    ).fetchone()
    db.close()
    
    assert result is not None, "Table should be created"
    assert result[1] == "products", "Table name should match"
    assert result[0] == table_id, "Table ID should match"


def test_add_column(temp_db):
    """Test adding a column to an existing table"""
    # Setup: create table first using connection API
    db = synthdb.connect(temp_db, backend='sqlite')
    table_id = db.create_table("products")
    
    # Add a column
    column_ids = db.add_columns("products", {"price": "real"})
    column_id = column_ids["price"]
    
    # Verify column was added
    db = sqlite3.connect(temp_db)
    cur = db.cursor()
    result = cur.execute("""
        SELECT id, name, data_type FROM column_definitions 
        WHERE table_id = ? AND name = 'price'
    """, (table_id,)).fetchone()
    db.close()
    
    assert result is not None, "Column should be created"
    assert result[1] == "price", "Column name should match"
    assert result[2] == "real", "Column type should match"
    assert result[0] == column_id, "Column ID should match"


def test_add_column_nonexistent_table(temp_db):
    """Test adding a column to a non-existent table"""
    db = synthdb.connect(temp_db, backend='sqlite')
    with pytest.raises(ValueError, match="not found"):
        db.add_columns("nonexistent", {"col": "text"})


def test_insert_typed_value(temp_db):
    """Test inserting typed values"""
    # Setup: create table and column using connection API
    db = synthdb.connect(temp_db, backend='sqlite')
    table_id = db.create_table("products")
    column_ids = db.add_columns("products", {"name": "text"})
    column_id = column_ids["name"]
    
    # Insert a value
    db.insert("products", {"name": "Widget"}, row_id=0)
    
    # Verify value was inserted in both tables
    db = sqlite3.connect(temp_db)
    cur = db.cursor()
    
    # Check main table
    main_result = cur.execute(
        "SELECT value FROM text_values WHERE row_id = ? AND table_id = ? AND column_id = ?",
        (0, table_id, column_id)
    ).fetchone()
    
    # Check history table
    history_result = cur.execute(
        "SELECT value FROM text_value_history WHERE row_id = ? AND table_id = ? AND column_id = ?",
        (0, table_id, column_id)
    ).fetchone()
    
    db.close()
    
    assert main_result is not None, "Value should be in main table"
    assert main_result[0] == "Widget", "Main table value should match"
    assert history_result is not None, "Value should be in history table"
    assert history_result[0] == "Widget", "History table value should match"


def test_insert_boolean_value(temp_db):
    """Test inserting boolean values (converted to integers)"""
    db = synthdb.connect(temp_db, backend='sqlite')
    table_id = db.create_table("products")
    column_ids = db.add_columns("products", {"active": "boolean"})
    column_id = column_ids["active"]
    
    # Insert True value
    db.insert("products", {"active": True}, row_id=0)
    
    # Verify value was converted to 1
    db = sqlite3.connect(temp_db)
    cur = db.cursor()
    result = cur.execute(
        "SELECT value FROM boolean_values WHERE row_id = ? AND table_id = ? AND column_id = ?",
        (0, table_id, column_id)
    ).fetchone()
    db.close()
    
    assert result is not None, "Boolean value should be inserted"
    assert result[0] == 1, "True should be converted to 1"
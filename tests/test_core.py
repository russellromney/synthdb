"""Tests for core SynthDB operations."""

import pytest
import sqlite3
from synthdb import create_table, add_column, insert_typed_value


def test_create_table(temp_db):
    """Test creating a new table"""
    # Create a new table
    table_id = create_table("products", temp_db)
    
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
    # Setup: create table first
    table_id = create_table("products", temp_db)
    
    # Add a column
    column_id = add_column("products", "price", "real", temp_db)
    
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
    with pytest.raises(ValueError, match="not found"):
        add_column("nonexistent", "col", "text", temp_db)


def test_insert_typed_value(temp_db):
    """Test inserting typed values"""
    # Setup: create table and column
    table_id = create_table("products", temp_db)
    column_id = add_column("products", "name", "text", temp_db)
    
    # Insert a value
    insert_typed_value(0, table_id, column_id, "Widget", "text", temp_db)
    
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
    table_id = create_table("products", temp_db)
    column_id = add_column("products", "active", "boolean", temp_db)
    
    # Insert True value
    insert_typed_value(0, table_id, column_id, True, "boolean", temp_db)
    
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
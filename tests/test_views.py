"""Tests for SynthDB view creation."""

import sqlite3
import tempfile
import os
import synthdb
from synthdb.views import create_table_views


def test_create_empty_table_view(temp_db):
    """Test that views are created for tables with no columns"""
    # Create table with no columns using connection API
    db = synthdb.connect(temp_db, backend='sqlite')
    db.create_table("empty_table")
    
    # Verify view was created
    db = sqlite3.connect(temp_db)
    cur = db.cursor()
    
    # Check that view exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='empty_table'")
    result = cur.fetchone()
    assert result is not None, "View should be created for empty table"
    
    # Query the view (should return empty result)
    cur.execute("SELECT * FROM empty_table")
    rows = cur.fetchall()
    assert len(rows) == 0, "Empty table view should return no rows"
    
    db.close()


def test_create_table_view_with_data(temp_db):
    """Test that views work correctly with actual data"""
    # Setup table with columns and data using connection API
    db = synthdb.connect(temp_db, backend='sqlite')
    db.create_table("products")
    db.add_columns("products", {
        "name": "text",
        "price": "real", 
        "quantity": "integer"
    })
    
    # Insert test data
    db.insert("products", {
        "name": "Widget",
        "price": 19.99,
        "quantity": 100
    }, row_id="0")
    
    db.insert("products", {
        "name": "Gadget", 
        "price": 29.99,
        "active": False
    }, row_id="1")
    
    # Query the view
    db = sqlite3.connect(temp_db)
    cur = db.cursor()
    
    cur.execute("SELECT * FROM products ORDER BY row_id")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    
    # Verify structure
    assert 'row_id' in columns, "View should include row_id"
    assert 'created_at' in columns, "View should include created_at"
    assert 'updated_at' in columns, "View should include updated_at"
    assert 'name' in columns, "View should include name column"
    assert 'price' in columns, "View should include price column"
    assert 'active' in columns, "View should include active column"
    
    # Verify data
    assert len(rows) == 2, "Should have 2 rows"
    
    # Convert to dict for easier testing
    results = [dict(zip(columns, row)) for row in rows]
    
    # Check first row
    assert results[0]['name'] == "Widget"
    assert float(results[0]['price']) == 19.99
    assert results[0]['active'] == "true"  # Boolean converted to string
    
    # Check second row
    assert results[1]['name'] == "Gadget"
    assert float(results[1]['price']) == 29.99
    assert results[1]['active'] == "false"  # Boolean converted to string
    
    db.close()


def test_view_recreated_after_column_addition(temp_db):
    """Test that views are updated when columns are added"""
    # Create table and initial column using connection API
    db = synthdb.connect(temp_db, backend='sqlite')
    db.create_table("products")
    db.add_columns("products", {"name": "text"})
    
    # Insert some data
    db.insert("products", {"name": "Widget"}, row_id="0")
    
    # Query initial view
    db = sqlite3.connect(temp_db)
    cur = db.cursor()
    cur.execute("PRAGMA table_info(products)")
    initial_columns = [row[1] for row in cur.fetchall()]
    db.close()
    
    # Add new column using connection API
    synthdb_conn = synthdb.connect(temp_db, backend='sqlite')
    synthdb_conn.add_columns("products", {"price": "real"})
    synthdb_conn.insert("products", {"price": 19.99})
    
    # Query updated view
    db = sqlite3.connect(temp_db)
    cur = db.cursor()
    cur.execute("PRAGMA table_info(products)")
    updated_columns = [row[1] for row in cur.fetchall()]
    
    # Verify new column is included
    assert "price" in updated_columns, "New column should be in view"
    assert len(updated_columns) > len(initial_columns), "View should have more columns"
    
    # Verify data is accessible
    cur.execute("SELECT name, price FROM products WHERE row_id = 0")
    result = cur.fetchone()
    assert result[0] == "Widget"
    assert float(result[1]) == 19.99
    
    db.close()
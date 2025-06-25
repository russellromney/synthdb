"""Tests for SynthDB view creation."""

import sqlite3
from synthdb import create_table, add_column, insert_typed_value
from synthdb.views import create_table_views


def test_create_empty_table_view(temp_db):
    """Test that views are created for tables with no columns"""
    # Create table with no columns
    create_table("empty_table", temp_db)
    
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
    # Setup table with columns and data
    table_id = create_table("products", temp_db)
    name_col = add_column("products", "name", "text", temp_db)
    price_col = add_column("products", "price", "real", temp_db)
    active_col = add_column("products", "active", "boolean", temp_db)
    
    # Insert test data
    insert_typed_value(0, table_id, name_col, "Widget", "text", temp_db)
    insert_typed_value(0, table_id, price_col, 19.99, "real", temp_db)
    insert_typed_value(0, table_id, active_col, True, "boolean", temp_db)
    
    insert_typed_value(1, table_id, name_col, "Gadget", "text", temp_db)
    insert_typed_value(1, table_id, price_col, 29.99, "real", temp_db)
    insert_typed_value(1, table_id, active_col, False, "boolean", temp_db)
    
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
    # Create table and initial column
    table_id = create_table("products", temp_db)
    name_col = add_column("products", "name", "text", temp_db)
    
    # Insert some data
    insert_typed_value(0, table_id, name_col, "Widget", "text", temp_db)
    
    # Query initial view
    db = sqlite3.connect(temp_db)
    cur = db.cursor()
    cur.execute("PRAGMA table_info(products)")
    initial_columns = [row[1] for row in cur.fetchall()]
    db.close()
    
    # Add new column
    price_col = add_column("products", "price", "real", temp_db)
    insert_typed_value(0, table_id, price_col, 19.99, "real", temp_db)
    
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
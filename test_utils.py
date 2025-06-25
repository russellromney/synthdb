#!/usr/bin/env python3
import os
import sqlite3
from synth import (
    make_db, create_table, add_column, query_view, 
    export_table_structure, create_table_views, insert_typed_value
)

def test_create_table():
    """Test creating a new table"""
    print("Testing create_table...")
    
    # Setup fresh database
    make_db()
    
    # Create a new table
    table_id = create_table("products")
    
    # Verify table was created
    db = sqlite3.connect('db.db')
    cur = db.cursor()
    result = cur.execute(
        "SELECT id, name FROM table_definitions WHERE name = 'products'"
    ).fetchone()
    db.close()
    
    assert result is not None, "Table should be created"
    assert result[1] == "products", "Table name should match"
    assert result[0] == table_id, "Table ID should match"
    print("✓ create_table test passed")


def test_add_column():
    """Test adding a column to an existing table"""
    print("Testing add_column...")
    
    # Setup fresh database with a table
    make_db()
    table_id = create_table("products")
    
    # Add a column
    column_id = add_column("products", "price", "real")
    
    # Verify column was added
    db = sqlite3.connect('db.db')
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
    print("✓ add_column test passed")


def test_add_column_nonexistent_table():
    """Test adding a column to a non-existent table"""
    print("Testing add_column with non-existent table...")
    
    make_db()
    
    try:
        add_column("nonexistent", "col", "text")
        assert False, "Should raise ValueError for non-existent table"
    except ValueError as e:
        assert "not found" in str(e), "Should mention table not found"
        print("✓ add_column error handling test passed")


def test_query_view():
    """Test querying a view"""
    print("Testing query_view...")
    
    # Setup database with data
    make_db()
    table_id = create_table("products")
    add_column("products", "name", "text")
    add_column("products", "price", "real")
    
    # Insert some data
    insert_typed_value(0, table_id, 0, "Widget", "text")  # name column
    insert_typed_value(0, table_id, 1, 19.99, "real")    # price column
    insert_typed_value(1, table_id, 0, "Gadget", "text")
    insert_typed_value(1, table_id, 1, 29.99, "real")
    
    # Create views
    create_table_views()
    
    # Test basic query
    results = query_view("products")
    assert len(results) == 2, f"Should have 2 rows, got {len(results)}"
    assert results[0]['name'] == "Widget", "First row name should be Widget"
    assert float(results[0]['price']) == 19.99, "First row price should be 19.99"
    
    # Test query with WHERE clause
    results = query_view("products", "price > 25")
    assert len(results) == 1, f"Should have 1 row with price > 25, got {len(results)}"
    assert results[0]['name'] == "Gadget", "Filtered result should be Gadget"
    
    print("✓ query_view test passed")


def test_export_table_structure():
    """Test exporting table structure"""
    print("Testing export_table_structure...")
    
    # Setup database with table and columns
    make_db()
    create_table("products")
    add_column("products", "name", "text")
    add_column("products", "price", "real")
    add_column("products", "in_stock", "boolean")
    add_column("products", "quantity", "integer")
    
    # Export structure
    create_sql = export_table_structure("products")
    
    # Verify the CREATE TABLE statement
    assert "CREATE TABLE products" in create_sql, "Should contain CREATE TABLE statement"
    assert "name TEXT" in create_sql, "Should contain name column"
    assert "price REAL" in create_sql, "Should contain price column"
    assert "in_stock INTEGER" in create_sql, "Should contain boolean as INTEGER"
    assert "quantity INTEGER" in create_sql, "Should contain quantity column"
    
    print("✓ export_table_structure test passed")
    print(f"Generated SQL:\n{create_sql}")


def test_export_table_structure_nonexistent():
    """Test exporting structure of non-existent table"""
    print("Testing export_table_structure with non-existent table...")
    
    make_db()
    
    try:
        export_table_structure("nonexistent")
        assert False, "Should raise ValueError for non-existent table"
    except ValueError as e:
        assert "not found" in str(e), "Should mention table not found"
        print("✓ export_table_structure error handling test passed")


def test_export_empty_table():
    """Test exporting structure of table with no columns"""
    print("Testing export_table_structure with empty table...")
    
    make_db()
    create_table("empty_table")
    
    result = export_table_structure("empty_table")
    assert "has no columns" in result, "Should mention no columns"
    print("✓ export_empty_table test passed")


def run_all_tests():
    """Run all tests"""
    print("Running utility function tests...\n")
    
    # Clean up existing test db if it exists
    if os.path.exists('db.db'):
        os.unlink('db.db')
    
    try:
        test_create_table()
        test_add_column()
        test_add_column_nonexistent_table()
        test_query_view()
        test_export_table_structure()
        test_export_table_structure_nonexistent()
        test_export_empty_table()
        
        print("\n✅ All tests passed!")
        
    finally:
        # Clean up test database
        if os.path.exists('db.db'):
            os.unlink('db.db')


if __name__ == "__main__":
    run_all_tests()
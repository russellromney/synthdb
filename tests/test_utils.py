"""Tests for SynthDB utility functions."""

import pytest
from synthdb import (
    create_table, add_column, insert_typed_value, 
    query_view, export_table_structure, list_tables, list_columns
)


def test_query_view(temp_db):
    """Test querying a view"""
    # Setup database with data
    table_id = create_table("products", temp_db)
    name_col = add_column("products", "name", "text", temp_db)
    price_col = add_column("products", "price", "real", temp_db)
    
    # Insert some data
    insert_typed_value(0, table_id, name_col, "Widget", "text", temp_db)
    insert_typed_value(0, table_id, price_col, 19.99, "real", temp_db)
    insert_typed_value(1, table_id, name_col, "Gadget", "text", temp_db)
    insert_typed_value(1, table_id, price_col, 29.99, "real", temp_db)
    
    # Test basic query
    results = query_view("products", db_path=temp_db)
    assert len(results) == 2, f"Should have 2 rows, got {len(results)}"
    assert results[0]['name'] == "Widget", "First row name should be Widget"
    assert float(results[0]['price']) == 19.99, "First row price should be 19.99"
    
    # Verify timestamp columns are included
    assert 'row_id' in results[0], "Should include row_id"
    assert 'created_at' in results[0], "Should include created_at"
    assert 'updated_at' in results[0], "Should include updated_at"
    assert results[0]['created_at'] is not None, "created_at should not be null"
    assert results[0]['updated_at'] is not None, "updated_at should not be null"
    
    # Test query with WHERE clause
    results = query_view("products", "price > 25", temp_db)
    assert len(results) == 1, f"Should have 1 row with price > 25, got {len(results)}"
    assert results[0]['name'] == "Gadget", "Filtered result should be Gadget"


def test_export_table_structure(temp_db):
    """Test exporting table structure"""
    # Setup database with table and columns
    create_table("products", temp_db)
    add_column("products", "name", "text", temp_db)
    add_column("products", "price", "real", temp_db)
    add_column("products", "in_stock", "boolean", temp_db)
    add_column("products", "quantity", "integer", temp_db)
    
    # Export structure
    create_sql = export_table_structure("products", temp_db)
    
    # Verify the CREATE TABLE statement
    assert "CREATE TABLE products" in create_sql, "Should contain CREATE TABLE statement"
    assert "name TEXT" in create_sql, "Should contain name column"
    assert "price REAL" in create_sql, "Should contain price column"
    assert "in_stock INTEGER" in create_sql, "Should contain boolean as INTEGER"
    assert "quantity INTEGER" in create_sql, "Should contain quantity column"


def test_export_table_structure_nonexistent(temp_db):
    """Test exporting structure of non-existent table"""
    with pytest.raises(ValueError, match="not found"):
        export_table_structure("nonexistent", temp_db)


def test_export_empty_table(temp_db):
    """Test exporting structure of table with no columns"""
    create_table("empty_table", temp_db)
    
    result = export_table_structure("empty_table", temp_db)
    assert "has no columns" in result, "Should mention no columns"


def test_list_tables(temp_db):
    """Test listing all tables"""
    # Create some tables
    create_table("products", temp_db)
    create_table("users", temp_db)
    
    # List tables
    tables = list_tables(temp_db)
    
    assert len(tables) == 2, "Should have 2 tables"
    table_names = [t['name'] for t in tables]
    assert "products" in table_names, "Should include products table"
    assert "users" in table_names, "Should include users table"
    
    # Check structure of returned data
    for table in tables:
        assert 'id' in table, "Should include table ID"
        assert 'name' in table, "Should include table name"
        assert 'created_at' in table, "Should include creation timestamp"


def test_list_columns(temp_db):
    """Test listing columns for a table"""
    # Setup
    create_table("products", temp_db)
    add_column("products", "name", "text", temp_db)
    add_column("products", "price", "real", temp_db)
    
    # List columns
    columns = list_columns("products", temp_db)
    
    assert len(columns) == 2, "Should have 2 columns"
    column_names = [c['name'] for c in columns]
    assert "name" in column_names, "Should include name column"
    assert "price" in column_names, "Should include price column"
    
    # Check structure of returned data
    for column in columns:
        assert 'id' in column, "Should include column ID"
        assert 'name' in column, "Should include column name"
        assert 'data_type' in column, "Should include data type"
        assert 'created_at' in column, "Should include creation timestamp"


def test_list_columns_nonexistent_table(temp_db):
    """Test listing columns for non-existent table"""
    with pytest.raises(ValueError, match="not found"):
        list_columns("nonexistent", temp_db)
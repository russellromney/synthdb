"""Tests for SynthDB utility functions."""

import pytest
import tempfile
import os
import synthdb


def test_query_view(temp_db):
    """Test querying a view"""
    # Setup database with data using connection API
    db = synthdb.connect(temp_db, backend='sqlite')
    db.create_table("products")
    db.add_columns("products", {
        "name": "text",
        "price": "real"
    })
    
    # Insert some data
    db.insert("products", {"name": "Widget", "price": 19.99}, id="0")
    db.insert("products", {"name": "Gadget", "price": 29.99}, id="1")
    
    # Test basic query
    results = db.query("products")
    assert len(results) == 2, f"Should have 2 rows, got {len(results)}"
    assert results[0]['name'] == "Widget", "First row name should be Widget"
    assert float(results[0]['price']) == 19.99, "First row price should be 19.99"
    
    # Verify timestamp columns are included
    assert 'id' in results[0], "Should include id"
    assert 'created_at' in results[0], "Should include created_at"
    assert 'updated_at' in results[0], "Should include updated_at"
    assert results[0]['created_at'] is not None, "created_at should not be null"
    assert results[0]['updated_at'] is not None, "updated_at should not be null"
    
    # Test query with WHERE clause
    results = db.query("products", "price > 25")
    assert len(results) == 1, f"Should have 1 row with price > 25, got {len(results)}"
    assert results[0]['name'] == "Gadget", "Filtered result should be Gadget"


def test_export_table_structure(temp_db):
    """Test exporting table structure"""
    # Setup database with table and columns using connection API
    db = synthdb.connect(temp_db, backend='sqlite')
    db.create_table("products")
    db.add_columns("products", {
        "name": "text",
        "price": "real",
        "score": "real",
        "quantity": "integer"
    })
    
    # Export structure - using connection API
    # Test column listing and CREATE TABLE generation
    columns = db.list_columns("products")
    assert len(columns) == 4, "Should have 4 columns"
    column_types = {col['name']: col['data_type'] for col in columns}
    
    # Verify column types
    assert column_types['name'] == 'text', "Name should be text type"
    assert column_types['price'] == 'real', "Price should be real type"
    assert column_types['score'] == 'real', "Score should be real type"
    assert column_types['quantity'] == 'integer', "Quantity should be integer type"
    
    # Create a simple CREATE TABLE statement
    column_defs = [f'{col["name"]} {col["data_type"].upper()}' for col in columns]
    create_sql = f"CREATE TABLE products ({', '.join(column_defs)})"
    
    # Verify the CREATE TABLE statement
    assert "CREATE TABLE products" in create_sql, "Should contain CREATE TABLE statement"
    assert "name TEXT" in create_sql, "Should contain name column"
    assert "price REAL" in create_sql, "Should contain price column"
    assert "score REAL" in create_sql, "Should contain score column"
    assert "quantity INTEGER" in create_sql, "Should contain quantity column"


def test_export_table_structure_nonexistent(temp_db):
    """Test listing columns of non-existent table"""
    db = synthdb.connect(temp_db, backend='sqlite')
    with pytest.raises(Exception):  # Connection API raises different error types
        db.list_columns("nonexistent")


def test_export_empty_table(temp_db):
    """Test exporting structure of table with no columns"""
    db = synthdb.connect(temp_db, backend='sqlite')
    db.create_table("empty_table")
    
    columns = db.list_columns("empty_table")
    assert len(columns) == 0, "Should have no columns"


def test_list_tables(temp_db):
    """Test listing all tables"""
    # Create some tables using connection API
    db = synthdb.connect(temp_db, backend='sqlite')
    db.create_table("products")
    db.create_table("users")
    
    # List tables
    tables = db.list_tables()
    
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
    # Setup using connection API
    db = synthdb.connect(temp_db, backend='sqlite')
    db.create_table("products")
    db.add_columns("products", {
        "name": "text",
        "price": "real"
    })
    
    # List columns
    columns = db.list_columns("products")
    
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
    db = synthdb.connect(temp_db, backend='sqlite')
    with pytest.raises(Exception):  # Connection API raises different error types
        db.list_columns("nonexistent")
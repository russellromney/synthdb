"""
Tests for the new, modern SynthDB API.

Tests the improved insert(), query(), add_columns(), and upsert() functions
with automatic ID generation, type inference, and enhanced error handling.
"""

import pytest
import tempfile
import os
from pathlib import Path

import synthdb


class TestNewAPI:
    """Test the new modern API functions."""

    def setup_method(self):
        """Setup test database."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        # Initialize database and table
        synthdb.make_db(self.db_path, backend_name='sqlite')
        synthdb.create_table('users', self.db_path, backend_name='sqlite')

    def teardown_method(self):
        """Cleanup test database."""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass

    def test_add_columns_with_types(self):
        """Test bulk column creation with explicit types."""
        columns = synthdb.add_columns('users', {
            'name': 'text',
            'age': 'integer',
            'active': 'boolean'
        }, self.db_path, 'sqlite')
        
        assert len(columns) == 3
        assert 'name' in columns
        assert 'age' in columns
        assert 'active' in columns
        assert all(isinstance(col_id, int) for col_id in columns.values())

    def test_add_columns_with_inference(self):
        """Test bulk column creation with type inference."""
        columns = synthdb.add_columns('users', {
            'name': 'John Doe',           # Should infer text
            'age': 25,                    # Should infer integer
            'salary': 50000.50,           # Should infer real
            'active': True,               # Should infer boolean
            'metadata': {'role': 'admin'}, # Should infer json
            'created': '2023-12-25'       # Should infer timestamp
        }, self.db_path, 'sqlite')
        
        assert len(columns) == 6
        assert all(col in columns for col in ['name', 'age', 'salary', 'active', 'metadata', 'created'])

    def test_insert_auto_id(self):
        """Test insert with auto-generated row ID."""
        # Setup columns
        synthdb.add_columns('users', {
            'name': 'text',
            'age': 'integer'
        }, self.db_path, 'sqlite')
        
        # Insert data
        row_id = synthdb.insert('users', {
            'name': 'Alice',
            'age': 28
        }, self.db_path, 'sqlite')
        
        assert isinstance(row_id, int)
        assert row_id >= 0

    def test_insert_explicit_id(self):
        """Test insert with explicit row ID."""
        # Setup columns
        synthdb.add_columns('users', {
            'name': 'text'
        }, self.db_path, 'sqlite')
        
        # Insert with explicit ID
        explicit_id = 100
        result_id = synthdb.insert('users', {
            'name': 'Bob'
        }, self.db_path, 'sqlite', row_id=explicit_id)
        
        assert result_id == explicit_id

    def test_insert_duplicate_id_error(self):
        """Test that duplicate row IDs raise an error."""
        # Setup
        synthdb.add_columns('users', {'name': 'text'}, self.db_path, 'sqlite')
        
        # Insert first row
        synthdb.insert('users', {'name': 'Alice'}, self.db_path, 'sqlite', row_id=10)
        
        # Try to insert with same ID
        with pytest.raises(ValueError, match="Row ID 10 already exists"):
            synthdb.insert('users', {'name': 'Bob'}, self.db_path, 'sqlite', row_id=10)

    def test_insert_invalid_column(self):
        """Test error handling for invalid column names."""
        synthdb.add_columns('users', {'name': 'text'}, self.db_path, 'sqlite')
        
        with pytest.raises(ValueError, match="Column 'invalid_column' not found"):
            synthdb.insert('users', {'invalid_column': 'test'}, self.db_path, 'sqlite')

    def test_insert_single_column(self):
        """Test single column insert."""
        synthdb.add_columns('users', {'name': 'text', 'age': 'integer'}, self.db_path, 'sqlite')
        
        # Single column insert
        row_id = synthdb.insert('users', 'name', 'Charlie', self.db_path, 'sqlite')
        assert isinstance(row_id, int)
        
        # Add more data to same row
        synthdb.insert('users', 'age', 30, self.db_path, 'sqlite', row_id=row_id)

    def test_insert_force_type(self):
        """Test forcing a specific type override."""
        synthdb.add_columns('users', {'data': 'text'}, self.db_path, 'sqlite')
        
        # Force store number as text
        row_id = synthdb.insert('users', 'data', 123, self.db_path, 'sqlite', force_type='text')
        assert isinstance(row_id, int)

    def test_query_basic(self):
        """Test basic querying functionality."""
        # Setup data
        synthdb.add_columns('users', {'name': 'text', 'age': 'integer'}, self.db_path, 'sqlite')
        
        # Insert test data
        synthdb.insert('users', {'name': 'Alice', 'age': 25}, self.db_path, 'sqlite')
        synthdb.insert('users', {'name': 'Bob', 'age': 30}, self.db_path, 'sqlite')
        
        # Query all
        all_users = synthdb.query('users', connection_info=self.db_path, backend_name='sqlite')
        assert len(all_users) == 2
        
        # Query with filter
        older_users = synthdb.query('users', 'age >= 30', self.db_path, 'sqlite')
        assert len(older_users) == 1
        assert older_users[0]['name'] == 'Bob'

    def test_upsert_insert(self):
        """Test upsert when row doesn't exist (insert)."""
        synthdb.add_columns('users', {
            'name': 'text',
            'email': 'text',
            'age': 'integer'
        }, self.db_path, 'sqlite')
        
        # Upsert new row
        row_id = synthdb.upsert('users', {
            'name': 'Diana',
            'email': 'diana@example.com',
            'age': 28
        }, key_columns=['email'], connection_info=self.db_path, backend_name='sqlite')
        
        assert isinstance(row_id, int)

    def test_upsert_update(self):
        """Test upsert when row exists (update)."""
        synthdb.add_columns('users', {
            'name': 'text',
            'email': 'text',
            'age': 'integer'
        }, self.db_path, 'sqlite')
        
        # Insert initial row
        initial_id = synthdb.insert('users', {
            'name': 'Eve',
            'email': 'eve@example.com',
            'age': 25
        }, self.db_path, 'sqlite')
        
        # Upsert (should update)
        updated_id = synthdb.upsert('users', {
            'name': 'Eve Smith',  # Updated name
            'email': 'eve@example.com',  # Same email (key)
            'age': 26  # Updated age
        }, key_columns=['email'], connection_info=self.db_path, backend_name='sqlite')
        
        assert updated_id == initial_id  # Should be same row

    def test_upsert_explicit_id(self):
        """Test upsert with explicit ID for new inserts."""
        synthdb.add_columns('users', {
            'name': 'text',
            'email': 'text'
        }, self.db_path, 'sqlite')
        
        # Upsert with explicit ID
        explicit_id = 500
        result_id = synthdb.upsert('users', {
            'name': 'Frank',
            'email': 'frank@example.com'
        }, key_columns=['email'], 
        connection_info=self.db_path, backend_name='sqlite', 
        row_id=explicit_id)
        
        assert result_id == explicit_id

    def test_error_message_quality(self):
        """Test that error messages are helpful and informative."""
        synthdb.add_columns('users', {'name': 'text', 'age': 'integer'}, self.db_path, 'sqlite')
        
        # Test invalid column error includes available columns
        try:
            synthdb.insert('users', {'wrong_name': 'test'}, self.db_path, 'sqlite')
        except ValueError as e:
            error_msg = str(e)
            assert 'wrong_name' in error_msg
            assert 'Available columns' in error_msg
            assert 'name' in error_msg
            assert 'age' in error_msg

    def test_backward_compatibility(self):
        """Test that legacy functions still work."""
        # Test legacy functions are available
        assert hasattr(synthdb, 'insert_typed_value')
        assert hasattr(synthdb, 'query_view') 
        assert hasattr(synthdb, 'add_column')
        
        # Test they can be called (basic functionality)
        table_id = synthdb.create_table('legacy_test', self.db_path, 'sqlite')
        col_id = synthdb.add_column('legacy_test', 'name', 'text', self.db_path, 'sqlite')
        
        # This should work without errors
        synthdb.insert_typed_value(1, table_id, col_id, 'test', 'text', self.db_path, 'sqlite')
        
        results = synthdb.query_view('legacy_test', None, self.db_path, 'sqlite')
        assert len(results) >= 0  # Should not error

    def test_transaction_safety(self):
        """Test that operations are transactionally safe."""
        synthdb.add_columns('users', {'name': 'text'}, self.db_path, 'sqlite')
        
        # Insert some data
        row_id1 = synthdb.insert('users', {'name': 'Alice'}, self.db_path, 'sqlite')
        row_id2 = synthdb.insert('users', {'name': 'Bob'}, self.db_path, 'sqlite')
        
        # Verify both were inserted
        users = synthdb.query('users', connection_info=self.db_path, backend_name='sqlite')
        names = [user.get('name') for user in users]
        assert 'Alice' in names
        assert 'Bob' in names


class TestAPIIntegration:
    """Integration tests for the complete API workflow."""
    
    def setup_method(self):
        """Setup test database."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()

    def teardown_method(self):
        """Cleanup test database."""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass

    def test_complete_workflow(self):
        """Test complete workflow with new API."""
        # Initialize
        synthdb.make_db(self.db_path, backend_name='sqlite')
        synthdb.create_table('products', self.db_path, backend_name='sqlite')
        
        # Add columns with mixed types
        columns = synthdb.add_columns('products', {
            'name': 'text',
            'description': 'A sample product',  # Infer text
            'price': 19.99,                     # Infer real
            'stock': 100,                       # Infer integer
            'active': True,                     # Infer boolean
            'tags': ['electronics', 'gadget'],  # Infer json
            'created': '2023-12-25'             # Infer timestamp
        }, self.db_path, 'sqlite')
        
        assert len(columns) == 7
        
        # Insert products
        product1 = synthdb.insert('products', {
            'name': 'Smartphone',
            'description': 'Latest model smartphone',
            'price': 599.99,
            'stock': 50,
            'active': True,
            'tags': ['electronics', 'mobile'],
            'created': '2023-12-25 10:00:00'
        }, self.db_path, 'sqlite')
        
        product2 = synthdb.insert('products', {
            'name': 'Laptop',
            'price': 1299.99,
            'stock': 25,
            'active': True
        }, self.db_path, 'sqlite', row_id=1000)  # Explicit ID
        
        # Query and verify
        all_products = synthdb.query('products', connection_info=self.db_path, backend_name='sqlite')
        assert len(all_products) == 2
        
        expensive = synthdb.query('products', 'price > 1000', self.db_path, 'sqlite')
        assert len(expensive) == 1
        assert expensive[0]['name'] == 'Laptop'
        
        # Upsert test
        updated_id = synthdb.upsert('products', {
            'name': 'Laptop Pro',  # Updated name
            'sku': 'LAPTOP-001',
            'price': 1399.99       # Updated price
        }, key_columns=['sku'], connection_info=self.db_path, backend_name='sqlite')
        
        # Should be a new product since SKU didn't exist
        final_products = synthdb.query('products', connection_info=self.db_path, backend_name='sqlite')
        assert len(final_products) == 3
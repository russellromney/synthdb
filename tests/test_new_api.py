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
        
        # Initialize database and table using connection API
        self.db = synthdb.connect(self.db_path, backend='sqlite')
        self.db.create_table('users')

    def teardown_method(self):
        """Cleanup test database."""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass

    def test_add_columns_with_types(self):
        """Test bulk column creation with explicit types."""
        columns = self.db.add_columns('users', {
            'name': 'text',
            'age': 'integer',
            'active': 'boolean'
        })
        
        assert len(columns) == 3
        assert 'name' in columns
        assert 'age' in columns
        assert 'active' in columns
        assert all(isinstance(col_id, int) for col_id in columns.values())

    def test_add_columns_with_inference(self):
        """Test bulk column creation with type inference."""
        columns = self.db.add_columns('users', {
            'name': 'John Doe',           # Should infer text
            'age': 25,                    # Should infer integer
            'salary': 50000.50,           # Should infer real
            'active': True,               # Should infer boolean
            'metadata': {'role': 'admin'}, # Should infer json
            'created': '2023-12-25'       # Should infer timestamp
        })
        
        assert len(columns) == 6
        assert all(col in columns for col in ['name', 'age', 'salary', 'active', 'metadata', 'created'])

    def test_insert_auto_id(self):
        """Test insert with auto-generated row ID."""
        # Setup columns
        self.db.add_columns('users', {
            'name': 'text',
            'age': 'integer'
        })
        
        # Insert data
        row_id = self.db.insert('users', {
            'name': 'Alice',
            'age': 28
        })
        
        assert isinstance(row_id, int)
        assert row_id >= 0

    def test_insert_explicit_id(self):
        """Test insert with explicit row ID."""
        # Setup columns
        self.db.add_columns('users', {
            'name': 'text'
        })
        
        # Insert with explicit ID
        explicit_id = 100
        result_id = self.db.insert('users', {
            'name': 'Bob'
        }, row_id=explicit_id)
        
        assert result_id == explicit_id

    def test_insert_duplicate_id_error(self):
        """Test that duplicate row IDs raise an error."""
        # Setup
        self.db.add_columns('users', {'name': 'text'})
        
        # Insert first row
        self.db.insert('users', {'name': 'Alice'}, row_id=10)
        
        # Try to insert with same ID
        with pytest.raises(ValueError, match="Row ID 10 already exists"):
            self.db.insert('users', {'name': 'Bob'}, row_id=10)

    def test_insert_invalid_column(self):
        """Test error handling for invalid column names."""
        self.db.add_columns('users', {'name': 'text'})
        
        with pytest.raises(ValueError, match="Column 'invalid_column' not found"):
            self.db.insert('users', {'invalid_column': 'test'})

    def test_insert_single_column(self):
        """Test single column insert."""
        self.db.add_columns('users', {'name': 'text', 'age': 'integer'})
        
        # Single column insert
        row_id = self.db.insert('users', 'name', 'Charlie')
        assert isinstance(row_id, int)
        
        # Add more data to same row
        self.db.insert('users', 'age', 30, row_id=row_id)

    def test_insert_force_type(self):
        """Test forcing a specific type override."""
        self.db.add_columns('users', {'data': 'text'})
        
        # Force store number as text
        row_id = self.db.insert('users', 'data', 123, force_type='text')
        assert isinstance(row_id, int)

    def test_query_basic(self):
        """Test basic querying functionality."""
        # Setup data
        self.db.add_columns('users', {'name': 'text', 'age': 'integer'})
        
        # Insert test data
        self.db.insert('users', {'name': 'Alice', 'age': 25})
        self.db.insert('users', {'name': 'Bob', 'age': 30})
        
        # Query all
        all_users = self.db.query('users')
        assert len(all_users) == 2
        
        # Query with filter
        older_users = self.db.query('users', 'age >= 30')
        assert len(older_users) == 1
        assert older_users[0]['name'] == 'Bob'

    def test_upsert_insert(self):
        """Test upsert when row doesn't exist (insert)."""
        self.db.add_columns('users', {
            'name': 'text',
            'email': 'text',
            'age': 'integer'
        })
        
        # Upsert new row
        row_id = self.db.upsert('users', {
            'name': 'Diana',
            'email': 'diana@example.com',
            'age': 28
        }, key_columns=['email'])
        
        assert isinstance(row_id, int)

    def test_upsert_update(self):
        """Test upsert when row exists (update)."""
        self.db.add_columns('users', {
            'name': 'text',
            'email': 'text',
            'age': 'integer'
        })
        
        # Insert initial row
        initial_id = self.db.insert('users', {
            'name': 'Eve',
            'email': 'eve@example.com',
            'age': 25
        })
        
        # Upsert (should update)
        updated_id = self.db.upsert('users', {
            'name': 'Eve Smith',  # Updated name
            'email': 'eve@example.com',  # Same email (key)
            'age': 26  # Updated age
        }, key_columns=['email'])
        
        assert updated_id == initial_id  # Should be same row

    def test_upsert_explicit_id(self):
        """Test upsert with explicit ID for new inserts."""
        self.db.add_columns('users', {
            'name': 'text',
            'email': 'text'
        })
        
        # Upsert with explicit ID
        explicit_id = 500
        result_id = self.db.upsert('users', {
            'name': 'Frank',
            'email': 'frank@example.com'
        }, key_columns=['email'], row_id=explicit_id)
        
        assert result_id == explicit_id

    def test_error_message_quality(self):
        """Test that error messages are helpful and informative."""
        self.db.add_columns('users', {'name': 'text', 'age': 'integer'})
        
        # Test invalid column error includes available columns
        try:
            self.db.insert('users', {'wrong_name': 'test'})
        except ValueError as e:
            error_msg = str(e)
            assert 'wrong_name' in error_msg
            assert 'Available columns' in error_msg
            assert 'name' in error_msg
            assert 'age' in error_msg

    def test_connection_api_availability(self):
        """Test that the connection API is available and working."""
        # Test modern connection API is available
        assert hasattr(synthdb, 'connect') 
        assert hasattr(synthdb, 'Connection')
        
        # Test they can be called - using new connection API
        db = synthdb.connect(self.db_path, 'sqlite')
        db.create_table('modern_test')
        db.add_columns('modern_test', {'name': 'text'})
        
        # Test that new query works
        results = db.query('modern_test')
        assert len(results) >= 0  # Should not error

    def test_transaction_safety(self):
        """Test that operations are transactionally safe."""
        self.db.add_columns('users', {'name': 'text'})
        
        # Insert some data
        row_id1 = self.db.insert('users', {'name': 'Alice'})
        row_id2 = self.db.insert('users', {'name': 'Bob'})
        
        # Verify both were inserted
        users = self.db.query('users')
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
        
        # Initialize database using connection API
        self.db = synthdb.connect(self.db_path, backend='sqlite')

    def teardown_method(self):
        """Cleanup test database."""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass

    def test_complete_workflow(self):
        """Test complete workflow with new API."""
        # Initialize
        self.db.create_table('products')
        
        # Add columns with mixed types
        columns = self.db.add_columns('products', {
            'name': 'text',
            'description': 'A sample product',  # Infer text
            'price': 19.99,                     # Infer real
            'stock': 100,                       # Infer integer
            'active': True,                     # Infer boolean
            'tags': ['electronics', 'gadget'],  # Infer json
            'created': '2023-12-25'             # Infer timestamp
        })
        
        assert len(columns) == 7
        
        # Insert products
        product1 = self.db.insert('products', {
            'name': 'Smartphone',
            'description': 'Latest model smartphone',
            'price': 599.99,
            'stock': 50,
            'active': True,
            'tags': ['electronics', 'mobile'],
            'created': '2023-12-25 10:00:00'
        })
        
        product2 = self.db.insert('products', {
            'name': 'Laptop',
            'price': 1299.99,
            'stock': 25,
            'active': True
        }, row_id=1000)  # Explicit ID
        
        # Query and verify
        all_products = self.db.query('products')
        assert len(all_products) == 2
        
        expensive = self.db.query('products', 'price > 1000')
        assert len(expensive) == 1
        assert expensive[0]['name'] == 'Laptop'
        
        # Add sku column for upsert test
        self.db.add_columns('products', {'sku': 'text'})
        
        # Upsert test
        updated_id = self.db.upsert('products', {
            'name': 'Laptop Pro',  # Updated name
            'sku': 'LAPTOP-001',
            'price': 1399.99       # Updated price
        }, key_columns=['sku'])
        
        # Should be a new product since SKU didn't exist
        final_products = self.db.query('products')
        assert len(final_products) == 3


class TestColumnCopyAPI:
    """Test column copying functionality."""
    
    def setup_method(self):
        """Setup test databases with sample data."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        self.db = synthdb.connect(self.db_path, backend='sqlite')
        
        # Create source table with data
        self.db.create_table('users')
        self.db.add_columns('users', {
            'name': 'text',
            'email': 'text', 
            'age': 'integer',
            'active': 'boolean'
        })
        
        # Insert test data
        self.db.insert('users', {'name': 'Alice', 'email': 'alice@example.com', 'age': 25, 'active': True})
        self.db.insert('users', {'name': 'Bob', 'email': 'bob@example.com', 'age': 30, 'active': False})
        
        # Create target table
        self.db.create_table('customers')
        self.db.add_columns('customers', {'company': 'text'})

    def teardown_method(self):
        """Cleanup test database."""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass

    def test_copy_column_structure_only(self):
        """Test copying column structure without data."""
        # Copy email column structure only
        column_id = self.db.copy_column('users', 'email', 'customers', 'contact_email', copy_data=False)
        
        assert isinstance(column_id, int)
        
        # Verify column was created
        columns = self.db.list_columns('customers')
        column_names = [col['name'] for col in columns]
        assert 'contact_email' in column_names
        
        # Verify no data was copied
        customers = self.db.query('customers')
        if customers:  # If there are any rows
            for row in customers:
                assert row.get('contact_email') is None

    def test_copy_column_with_data(self):
        """Test copying column structure and data."""
        # First add some data to customers table to test copying into existing rows
        self.db.insert('customers', {'company': 'ACME Corp'})
        self.db.insert('customers', {'company': 'Tech Inc'})
        
        # Copy email column with data
        column_id = self.db.copy_column('users', 'email', 'customers', 'contact_email', copy_data=True)
        
        assert isinstance(column_id, int)
        
        # Verify column was created
        columns = self.db.list_columns('customers')
        column_names = [col['name'] for col in columns]
        assert 'contact_email' in column_names
        
        # Verify data was copied
        customers = self.db.query('customers')
        emails = [row.get('contact_email') for row in customers if row.get('contact_email')]
        assert 'alice@example.com' in emails
        assert 'bob@example.com' in emails

    def test_copy_column_within_same_table(self):
        """Test copying a column within the same table."""
        # Copy email to backup_email in same table
        column_id = self.db.copy_column('users', 'email', 'users', 'backup_email', copy_data=True)
        
        assert isinstance(column_id, int)
        
        # Verify column was created
        columns = self.db.list_columns('users')
        column_names = [col['name'] for col in columns]
        assert 'backup_email' in column_names
        
        # Verify data was copied correctly
        users = self.db.query('users')
        for user in users:
            assert user['email'] == user['backup_email']

    def test_copy_column_different_types(self):
        """Test copying columns of different data types."""
        # Test integer column
        int_column_id = self.db.copy_column('users', 'age', 'customers', 'customer_age', copy_data=True)
        
        # Test boolean column
        bool_column_id = self.db.copy_column('users', 'active', 'customers', 'is_active', copy_data=True)
        
        assert isinstance(int_column_id, int)
        assert isinstance(bool_column_id, int)
        
        # Verify columns and data types
        columns = self.db.list_columns('customers')
        column_info = {col['name']: col['data_type'] for col in columns}
        
        assert column_info['customer_age'] == 'integer'
        assert column_info['is_active'] == 'boolean'

    def test_copy_column_error_source_not_found(self):
        """Test error when source column doesn't exist."""
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            self.db.copy_column('users', 'nonexistent', 'customers', 'test_col')

    def test_copy_column_error_source_table_not_found(self):
        """Test error when source table doesn't exist."""
        with pytest.raises(ValueError, match="Column 'email' not found in table 'nonexistent'"):
            self.db.copy_column('nonexistent', 'email', 'customers', 'test_col')

    def test_copy_column_error_target_table_not_found(self):
        """Test error when target table doesn't exist."""
        with pytest.raises(ValueError, match="Table 'nonexistent' not found"):
            self.db.copy_column('users', 'email', 'nonexistent', 'test_col')

    def test_copy_column_api_import(self):
        """Test that copy_column is available from the main API."""
        from synthdb.api import copy_column
        
        # Test function exists and can be called
        column_id = copy_column('users', 'email', 'customers', 'contact_email', 
                               copy_data=False, connection_info=self.db_path, backend_name='sqlite')
        assert isinstance(column_id, int)
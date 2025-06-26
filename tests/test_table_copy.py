"""Tests for table copy functionality."""

import pytest
import tempfile
import os

from synthdb import connect
from synthdb.core import copy_table


class TestTableCopy:
    """Test table copy functionality."""
    
    @pytest.fixture
    def db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        db = connect(db_path, 'sqlite')
        yield db
        
        # Cleanup
        os.unlink(db_path)
    
    def test_copy_table_structure_only(self, db):
        """Test copying table structure without data."""
        # Create source table with columns
        db.create_table('users')
        db.add_columns('users', {
            'name': 'text',
            'age': 'integer',
            'email': 'text',
            'created_at': 'timestamp'
        })
        
        # Copy structure only
        new_table_id = db.copy_table('users', 'users_template')
        
        # Verify new table exists
        tables = db.list_tables()
        table_names = [t['name'] for t in tables]
        assert 'users_template' in table_names
        
        # Verify columns were copied
        source_cols = db.list_columns('users')
        target_cols = db.list_columns('users_template')
        
        assert len(source_cols) == len(target_cols)
        
        # Check column names and types match
        source_info = {col['name']: col['data_type'] for col in source_cols}
        target_info = {col['name']: col['data_type'] for col in target_cols}
        
        assert source_info == target_info
        
        # Verify no data was copied
        assert len(db.query('users_template')) == 0
    
    def test_copy_table_with_data(self, db):
        """Test copying table structure and data."""
        # Create source table with data
        db.create_table('products')
        db.add_columns('products', {
            'name': 'text',
            'price': 'real',
            'stock': 'integer'
        })
        
        # Insert test data
        db.insert('products', {'name': 'Widget', 'price': 9.99, 'stock': 100})
        db.insert('products', {'name': 'Gadget', 'price': 19.99, 'stock': 50})
        db.insert('products', {'name': 'Doohickey', 'price': 5.99, 'stock': 200})
        
        # Copy with data
        new_table_id = db.copy_table('products', 'products_backup', copy_data=True)
        
        # Verify data was copied
        source_data = db.query('products')
        target_data = db.query('products_backup')
        
        assert len(target_data) == len(source_data) == 3
        
        # Verify data values match (but IDs are different)
        source_values = sorted([(row['name'], row['price'], row['stock']) for row in source_data])
        target_values = sorted([(row['name'], row['price'], row['stock']) for row in target_data])
        
        assert source_values == target_values
        
        # Verify row IDs are different (new UUIDs generated)
        source_ids = {row['row_id'] for row in source_data}
        target_ids = {row['row_id'] for row in target_data}
        
        assert len(source_ids.intersection(target_ids)) == 0
    
    def test_copy_empty_table(self, db):
        """Test copying a table with no columns."""
        # Create empty table
        db.create_table('empty_table')
        
        # Copy it
        new_table_id = db.copy_table('empty_table', 'empty_copy')
        
        # Verify both tables exist and are empty
        tables = db.list_tables()
        table_names = [t['name'] for t in tables]
        
        assert 'empty_table' in table_names
        assert 'empty_copy' in table_names
        
        assert len(db.list_columns('empty_table')) == 0
        assert len(db.list_columns('empty_copy')) == 0
    
    def test_copy_table_source_not_exists(self, db):
        """Test copying from non-existent table."""
        with pytest.raises(ValueError, match="Source table 'nonexistent' not found"):
            db.copy_table('nonexistent', 'target')
    
    def test_copy_table_target_exists(self, db):
        """Test copying to existing table name."""
        # Create both tables
        db.create_table('table1')
        db.create_table('table2')
        
        # Try to copy to existing table
        with pytest.raises(ValueError, match="Target table 'table2' already exists"):
            db.copy_table('table1', 'table2')
    
    def test_copy_table_with_deleted_rows(self, db):
        """Test that deleted rows are not copied."""
        # Create table with data
        db.create_table('orders')
        db.add_columns('orders', {
            'product': 'text',
            'quantity': 'integer'
        })
        
        # Insert data
        row1 = db.insert('orders', {'product': 'Item1', 'quantity': 10})
        row2 = db.insert('orders', {'product': 'Item2', 'quantity': 20})
        row3 = db.insert('orders', {'product': 'Item3', 'quantity': 30})
        
        # Delete one row
        db.delete_row('orders', row2)
        
        # Copy with data
        db.copy_table('orders', 'orders_copy', copy_data=True)
        
        # Verify only non-deleted rows were copied
        copied_data = db.query('orders_copy')
        assert len(copied_data) == 2
        
        products = [row['product'] for row in copied_data]
        assert 'Item1' in products
        assert 'Item3' in products
        assert 'Item2' not in products
    
    def test_copy_table_preserves_all_types(self, db):
        """Test that all data types are preserved correctly."""
        # Create table with all types
        db.create_table('all_types')
        db.add_columns('all_types', {
            'text_col': 'text',
            'int_col': 'integer',
            'real_col': 'real',
            'timestamp_col': 'timestamp'
        })
        
        # Insert test data
        db.insert('all_types', {
            'text_col': 'Hello World',
            'int_col': 42,
            'real_col': 3.14159,
            'timestamp_col': '2023-12-25 12:00:00.000'
        })
        
        # Copy with data
        db.copy_table('all_types', 'all_types_copy', copy_data=True)
        
        # Verify data types and values
        copied_data = db.query('all_types_copy')[0]
        
        assert copied_data['text_col'] == 'Hello World'
        assert copied_data['int_col'] == 42
        assert copied_data['real_col'] == 3.14159
        assert copied_data['timestamp_col'] == '2023-12-25 12:00:00.000'
    
    def test_copy_table_transaction_rollback(self, db):
        """Test that copy is atomic - all or nothing."""
        # Create source table
        db.create_table('source')
        db.add_columns('source', {'col1': 'text'})
        
        # Mock a failure during copy by trying to copy to a protected name
        with pytest.raises(ValueError):
            db.copy_table('source', 'table_definitions')  # Protected name
        
        # Verify no partial table was created
        tables = db.list_tables()
        table_names = [t['name'] for t in tables]
        assert 'table_definitions' not in table_names
    
    def test_copy_table_with_history(self, db):
        """Test that value history is preserved when copying."""
        # Create table and add data with updates
        db.create_table('versioned')
        db.add_columns('versioned', {'status': 'text'})
        
        # Insert and update to create history
        row_id = db.insert('versioned', {'status': 'draft'})
        db.upsert('versioned', {'status': 'published'}, row_id)
        db.upsert('versioned', {'status': 'archived'}, row_id)
        
        # Copy with data
        db.copy_table('versioned', 'versioned_copy', copy_data=True)
        
        # Get current value in copy
        copied_data = db.query('versioned_copy')[0]
        assert copied_data['status'] == 'archived'  # Latest value
        
        # Verify history was copied by checking value tables directly
        from synthdb.transactions import transaction_context
        from synthdb.backends import get_backend
        backend = get_backend('sqlite')
        
        with transaction_context(db.connection_info, 'sqlite') as (backend, connection):
            # Get table IDs
            cur = backend.execute(connection, 
                "SELECT id FROM table_definitions WHERE name = 'versioned_copy'")
            target_table_id = backend.fetchone(cur)['id']
            
            cur = backend.execute(connection,
                "SELECT id FROM column_definitions WHERE table_id = ? AND name = 'status'",
                (target_table_id,))
            col_id = backend.fetchone(cur)['id']
            
            # Check all versions exist
            cur = backend.execute(connection,
                "SELECT COUNT(*) as count FROM text_values WHERE table_id = ? AND column_id = ?",
                (target_table_id, col_id))
            version_count = backend.fetchone(cur)['count']
            
            assert version_count == 3  # All 3 versions copied
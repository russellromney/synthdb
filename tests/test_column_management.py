"""Tests for column management functionality."""

import pytest
import tempfile
import os

from synthdb import connect
from synthdb.api import rename_column, delete_column
from synthdb.utils import list_columns


class TestColumnManagement:
    """Test column rename and delete functionality."""
    
    @pytest.fixture
    def db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        db = connect(db_path, 'sqlite')
        yield db
        
        # Cleanup
        os.unlink(db_path)
    
    def test_rename_column(self, db):
        """Test renaming a column."""
        # Create table with columns
        db.create_table('users')
        db.add_columns('users', {
            'username': 'text',
            'email': 'text',
            'age': 'integer'
        })
        
        # Insert test data
        db.insert('users', {'username': 'john', 'email': 'john@example.com', 'age': 30})
        db.insert('users', {'username': 'jane', 'email': 'jane@example.com', 'age': 25})
        
        # Rename column
        db.rename_column('users', 'username', 'display_name')
        
        # Verify column was renamed
        columns = db.list_columns('users')
        column_names = [col['name'] for col in columns]
        
        assert 'username' not in column_names
        assert 'display_name' in column_names
        
        # Verify data is still accessible with new name
        users = db.query('users')
        assert len(users) == 2
        assert users[0]['display_name'] in ['john', 'jane']
        assert users[1]['display_name'] in ['john', 'jane']
    
    def test_rename_column_nonexistent_table(self, db):
        """Test renaming column in non-existent table."""
        with pytest.raises(ValueError, match="Table 'nonexistent' not found"):
            db.rename_column('nonexistent', 'old', 'new')
    
    def test_rename_column_nonexistent_column(self, db):
        """Test renaming non-existent column."""
        db.create_table('users')
        db.add_columns('users', {'name': 'text'})
        
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            db.rename_column('users', 'nonexistent', 'new_name')
    
    def test_rename_column_to_existing_name(self, db):
        """Test renaming column to already existing name."""
        db.create_table('users')
        db.add_columns('users', {
            'name': 'text',
            'email': 'text'
        })
        
        with pytest.raises(ValueError, match="Column 'email' already exists"):
            db.rename_column('users', 'name', 'email')
    
    def test_rename_column_protected_name(self, db):
        """Test renaming column to protected name."""
        db.create_table('users')
        db.add_columns('users', {'name': 'text'})
        
        with pytest.raises(ValueError, match="protected"):
            db.rename_column('users', 'name', 'row_id')
    
    def test_delete_column(self, db):
        """Test soft deleting a column."""
        # Create table with columns
        db.create_table('products')
        db.add_columns('products', {
            'name': 'text',
            'price': 'real',
            'deprecated_field': 'text'
        })
        
        # Insert test data
        db.insert('products', {
            'name': 'Widget',
            'price': 9.99,
            'deprecated_field': 'old data'
        })
        
        # Delete column
        db.delete_column('products', 'deprecated_field')
        
        # Verify column is no longer visible
        columns = db.list_columns('products')
        column_names = [col['name'] for col in columns]
        
        assert 'deprecated_field' not in column_names
        assert 'name' in column_names
        assert 'price' in column_names
        
        # Verify queries don't return deleted column
        products = db.query('products')
        assert len(products) == 1
        assert 'deprecated_field' not in products[0]
        assert products[0]['name'] == 'Widget'
        assert products[0]['price'] == 9.99
    
    def test_delete_column_preserves_data(self, db):
        """Test that deleting column preserves data for recovery."""
        # Create table and add data
        db.create_table('logs')
        db.add_columns('logs', {'message': 'text', 'level': 'text'})
        
        row_id = db.insert('logs', {'message': 'Test log', 'level': 'INFO'})
        
        # Delete column
        db.delete_column('logs', 'level')
        
        # Data should still exist in the database, just not visible
        # This is tested indirectly - if hard delete was used, 
        # the table structure would be different
        logs = db.query('logs')
        assert len(logs) == 1
        assert 'level' not in logs[0]
    
    def test_delete_nonexistent_column(self, db):
        """Test deleting non-existent column."""
        db.create_table('users')
        
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            db.delete_column('users', 'nonexistent')
    
    def test_rename_then_delete(self, db):
        """Test renaming a column then deleting it."""
        # Create table
        db.create_table('test')
        db.add_columns('test', {
            'old_name': 'text',
            'other': 'integer'
        })
        
        # Insert data
        db.insert('test', {'old_name': 'value1', 'other': 42})
        
        # Rename column
        db.rename_column('test', 'old_name', 'new_name')
        
        # Verify rename worked
        data = db.query('test')
        assert 'new_name' in data[0]
        assert data[0]['new_name'] == 'value1'
        
        # Delete the renamed column
        db.delete_column('test', 'new_name')
        
        # Verify deletion
        columns = db.list_columns('test')
        column_names = [col['name'] for col in columns]
        assert 'new_name' not in column_names
        assert 'other' in column_names
    
    def test_column_operations_with_history(self, db):
        """Test column operations preserve value history."""
        # Create table
        db.create_table('versioned')
        db.add_columns('versioned', {'status': 'text'})
        
        # Create history by updating values
        row_id = db.insert('versioned', {'status': 'draft'})
        db.upsert('versioned', {'status': 'published'}, row_id)
        db.upsert('versioned', {'status': 'archived'}, row_id)
        
        # Rename column
        db.rename_column('versioned', 'status', 'document_status')
        
        # Verify current value is accessible with new name
        data = db.query('versioned')
        assert data[0]['document_status'] == 'archived'
        
        # Delete column
        db.delete_column('versioned', 'document_status')
        
        # Verify table still exists but column is gone
        columns = db.list_columns('versioned')
        assert len(columns) == 0  # No columns left
        
        # When all columns are deleted, query returns no rows
        # because there's no data to display
        data = db.query('versioned')
        assert len(data) == 0
    
    def test_hard_delete_column(self, db):
        """Test hard deleting a column permanently removes data."""
        # Create table with columns
        db.create_table('products')
        db.add_columns('products', {
            'name': 'text',
            'price': 'real',
            'temp_data': 'text'
        })
        
        # Insert test data
        row_ids = []
        for i in range(3):
            row_id = db.insert('products', {
                'name': f'Product {i}',
                'price': 10.0 + i,
                'temp_data': f'temp_{i}'
            })
            row_ids.append(row_id)
        
        # Hard delete column
        db.delete_column('products', 'temp_data', hard_delete=True)
        
        # Verify column is not visible
        columns = db.list_columns('products')
        column_names = [col['name'] for col in columns]
        assert 'temp_data' not in column_names
        
        # Verify data is completely removed (not just hidden)
        # Query should work fine without the deleted column
        products = db.query('products')
        assert len(products) == 3
        for product in products:
            assert 'temp_data' not in product
            assert 'name' in product
            assert 'price' in product
    
    def test_hard_delete_soft_deleted_column(self, db):
        """Test hard deleting a previously soft-deleted column."""
        # Create table
        db.create_table('users')
        db.add_columns('users', {
            'name': 'text',
            'old_field': 'text'
        })
        
        # Insert data
        db.insert('users', {'name': 'Alice', 'old_field': 'old_value'})
        
        # First soft delete
        db.delete_column('users', 'old_field', hard_delete=False)
        
        # Verify soft deleted (not visible in normal list)
        visible_columns = db.list_columns('users')
        assert not any(col['name'] == 'old_field' for col in visible_columns)
        
        # But visible when including deleted
        all_columns = list_columns('users', include_deleted=True, db_path=db.connection_info)
        assert any(col['name'] == 'old_field' and col['deleted_at'] is not None for col in all_columns)
        
        # Now hard delete the soft-deleted column
        db.delete_column('users', 'old_field', hard_delete=True)
        
        # Verify completely gone even with include_deleted
        all_columns = list_columns('users', include_deleted=True, db_path=db.connection_info)
        assert not any(col['name'] == 'old_field' for col in all_columns)
    
    def test_list_columns_include_deleted(self, db):
        """Test listing columns with include_deleted parameter."""
        # Create table
        db.create_table('test')
        db.add_columns('test', {
            'active1': 'text',
            'deleted1': 'text',
            'active2': 'integer',
            'deleted2': 'real'
        })
        
        # Soft delete some columns
        db.delete_column('test', 'deleted1')
        db.delete_column('test', 'deleted2')
        
        # List without deleted
        visible_columns = db.list_columns('test')
        visible_names = [col['name'] for col in visible_columns]
        assert 'active1' in visible_names
        assert 'active2' in visible_names
        assert 'deleted1' not in visible_names
        assert 'deleted2' not in visible_names
        
        # List with deleted
        all_columns = db.list_columns('test', include_deleted=True)
        all_names = [col['name'] for col in all_columns]
        assert 'active1' in all_names
        assert 'active2' in all_names
        assert 'deleted1' in all_names
        assert 'deleted2' in all_names
        
        # Check deleted columns have deleted_at timestamp
        for col in all_columns:
            if col['name'] in ['deleted1', 'deleted2']:
                assert col['deleted_at'] is not None
            else:
                assert col['deleted_at'] is None
    
    def test_hard_delete_with_multiple_types(self, db):
        """Test hard delete removes data from all type tables."""
        # Create table with different column types
        db.create_table('mixed')
        db.add_columns('mixed', {
            'text_col': 'text',
            'int_col': 'integer',
            'real_col': 'real',
            'ts_col': 'timestamp'
        })
        
        # Insert data
        db.insert('mixed', {
            'text_col': 'hello',
            'int_col': 42,
            'real_col': 3.14,
            'ts_col': '2023-12-25'
        })
        
        # Hard delete each column type
        db.delete_column('mixed', 'text_col', hard_delete=True)
        db.delete_column('mixed', 'int_col', hard_delete=True)
        db.delete_column('mixed', 'real_col', hard_delete=True)
        db.delete_column('mixed', 'ts_col', hard_delete=True)
        
        # Verify all columns are gone
        columns = db.list_columns('mixed')
        assert len(columns) == 0
        
        # Even with include_deleted
        all_columns = list_columns('mixed', include_deleted=True, db_path=db.connection_info)
        assert len(all_columns) == 0
    
    def test_hard_delete_nonexistent_column(self, db):
        """Test hard deleting non-existent column."""
        db.create_table('test')
        
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            db.delete_column('test', 'nonexistent', hard_delete=True)
    
    def test_soft_vs_hard_delete_comparison(self, db):
        """Compare soft delete vs hard delete behavior."""
        # Create two identical tables
        for table in ['soft_test', 'hard_test']:
            db.create_table(table)
            db.add_columns(table, {
                'keep': 'text',
                'remove': 'text'
            })
            db.insert(table, {'keep': 'data1', 'remove': 'data2'})
        
        # Soft delete in first table
        db.delete_column('soft_test', 'remove', hard_delete=False)
        
        # Hard delete in second table
        db.delete_column('hard_test', 'remove', hard_delete=True)
        
        # Both should not show the column in normal listing
        soft_columns = [col['name'] for col in db.list_columns('soft_test')]
        hard_columns = [col['name'] for col in db.list_columns('hard_test')]
        assert soft_columns == hard_columns == ['keep']
        
        # But soft deleted column should appear with include_deleted
        soft_all = list_columns('soft_test', include_deleted=True, db_path=db.connection_info)
        hard_all = list_columns('hard_test', include_deleted=True, db_path=db.connection_info)
        
        assert len(soft_all) == 2  # Both columns
        assert len(hard_all) == 1  # Only 'keep' column
        
        # Soft deleted column should have deleted_at timestamp
        removed_col = next(col for col in soft_all if col['name'] == 'remove')
        assert removed_col['deleted_at'] is not None
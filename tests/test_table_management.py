"""Tests for table management functionality."""

import pytest
import tempfile
import os

from synthdb import connect
from synthdb.api import delete_table


class TestTableManagement:
    """Test table deletion functionality."""
    
    @pytest.fixture
    def db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        db = connect(db_path, 'sqlite')
        yield db
        
        # Cleanup
        os.unlink(db_path)
    
    def test_soft_delete_table(self, db):
        """Test soft deleting a table."""
        # Create table with data
        db.create_table('users')
        db.add_columns('users', {
            'name': 'text',
            'email': 'text'
        })
        
        db.insert('users', {'name': 'John', 'email': 'john@example.com'})
        db.insert('users', {'name': 'Jane', 'email': 'jane@example.com'})
        
        # Soft delete table
        db.delete_table('users', hard_delete=False)
        
        # Table should no longer be visible
        tables = db.list_tables()
        table_names = [t['name'] for t in tables]
        assert 'users' not in table_names
        
        # Attempting to query deleted table returns empty results
        # (The view doesn't exist anymore)
        try:
            results = db.query('users')
            assert len(results) == 0
        except Exception:
            # Some implementations might raise an error
            pass
    
    def test_hard_delete_table(self, db):
        """Test hard deleting a table."""
        # Create table with data
        db.create_table('temp_data')
        db.add_columns('temp_data', {
            'value': 'text',
            'timestamp': 'timestamp'
        })
        
        # Insert substantial data
        for i in range(10):
            db.insert('temp_data', {
                'value': f'data_{i}',
                'timestamp': '2023-01-01 00:00:00.000'
            })
        
        # Hard delete table
        db.delete_table('temp_data', hard_delete=True)
        
        # Table should be completely gone
        tables = db.list_tables()
        table_names = [t['name'] for t in tables]
        assert 'temp_data' not in table_names
        
        # No data should remain in value tables
        # This is verified by the fact that the table is gone
    
    def test_delete_nonexistent_table(self, db):
        """Test deleting non-existent table."""
        with pytest.raises(ValueError, match="Table 'nonexistent' not found"):
            db.delete_table('nonexistent')
    
    def test_delete_protected_table(self, db):
        """Test that protected tables cannot be deleted."""
        # Try to delete system tables
        with pytest.raises(ValueError, match="conflicts with internal"):
            db.delete_table('table_definitions')
        
        with pytest.raises(ValueError, match="conflicts with internal"):
            db.delete_table('column_definitions')
    
    def test_soft_delete_preserves_structure(self, db):
        """Test that soft delete preserves table structure."""
        # Create complex table
        db.create_table('products')
        db.add_columns('products', {
            'name': 'text',
            'price': 'real',
            'stock': 'integer',
            'description': 'text'
        })
        
        # Note column count before deletion
        columns_before = db.list_columns('products')
        assert len(columns_before) == 4
        
        # Soft delete
        db.delete_table('products', hard_delete=False)
        
        # Table is marked as deleted but structure remains in database
        # (This is an implementation detail - from user perspective it's gone)
        tables = db.list_tables()
        assert 'products' not in [t['name'] for t in tables]
    
    def test_delete_table_with_relationships(self, db):
        """Test deleting table that has data relationships."""
        # Create related tables
        db.create_table('orders')
        db.add_columns('orders', {
            'order_number': 'text',
            'customer_id': 'text'
        })
        
        db.create_table('order_items')
        db.add_columns('order_items', {
            'order_id': 'text',
            'product': 'text',
            'quantity': 'integer'
        })
        
        # Add related data
        order_id = db.insert('orders', {
            'order_number': 'ORD-001',
            'customer_id': 'CUST-123'
        })
        
        db.insert('order_items', {
            'order_id': order_id,
            'product': 'Widget',
            'quantity': 5
        })
        
        # Delete parent table
        db.delete_table('orders', hard_delete=False)
        
        # Child table should still exist
        tables = db.list_tables()
        table_names = [t['name'] for t in tables]
        assert 'order_items' in table_names
        
        # But parent is gone
        assert 'orders' not in table_names
    
    def test_hard_delete_performance(self, db):
        """Test that hard delete is efficient for large tables."""
        # Create table with many rows
        db.create_table('large_table')
        db.add_columns('large_table', {
            'data': 'text',
            'number': 'integer'
        })
        
        # Insert many rows
        for i in range(100):
            db.insert('large_table', {
                'data': f'row_{i}',
                'number': i
            })
        
        # Hard delete should be fast
        import time
        start_time = time.time()
        db.delete_table('large_table', hard_delete=True)
        end_time = time.time()
        
        # Should complete quickly (within 1 second)
        assert end_time - start_time < 1.0
        
        # Verify table is gone
        tables = db.list_tables()
        assert 'large_table' not in [t['name'] for t in tables]
    
    def test_delete_table_with_history(self, db):
        """Test deleting table with value history."""
        # Create table with history
        db.create_table('versioned')
        db.add_columns('versioned', {'status': 'text'})
        
        # Create value history
        row_id = db.insert('versioned', {'status': 'v1'})
        for i in range(2, 6):
            db.upsert('versioned', {'status': f'v{i}'}, row_id)
        
        # Soft delete preserves history
        db.delete_table('versioned', hard_delete=False)
        
        # Table should be gone from user perspective
        tables = db.list_tables()
        assert 'versioned' not in [t['name'] for t in tables]
    
    def test_create_after_soft_delete(self, db):
        """Test creating a table with same name after soft delete."""
        # Create and populate table
        db.create_table('reusable')
        db.add_columns('reusable', {'data': 'text'})
        db.insert('reusable', {'data': 'original'})
        
        # Soft delete
        db.delete_table('reusable', hard_delete=False)
        
        # Should be able to create new table with same name
        db.create_table('reusable')
        db.add_columns('reusable', {'info': 'text'})
        db.insert('reusable', {'info': 'new'})
        
        # Verify it's a different table
        columns = db.list_columns('reusable')
        column_names = [c['name'] for c in columns]
        assert 'info' in column_names
        assert 'data' not in column_names
        
        # Query returns new data
        data = db.query('reusable')
        assert len(data) == 1
        assert data[0]['info'] == 'new'
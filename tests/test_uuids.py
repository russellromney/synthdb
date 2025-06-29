"""
Tests for UUID row ID generation in SynthDB.

Tests that the simplified row ID generation using UUIDs
works correctly and efficiently.
"""

import pytest
import tempfile
import os
import synthdb


class TestRowIdGeneration:
    """Test row ID generation."""
    
    def setup_method(self):
        """Setup test database."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        # Create connection
        self.db = synthdb.connect(self.db_path, backend='sqlite', auto_init=True)
    
    def teardown_method(self):
        """Cleanup test database."""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass
    
    def test_unique_row_ids(self):
        """Test that auto-generated row IDs are unique UUIDs."""
        self.db.create_table('users')
        self.db.add_columns('users', {'name': 'text', 'age': 'integer'})
        
        # Insert multiple rows and verify unique UUIDs
        row_ids = []
        for i in range(5):
            row_id = self.db.insert('users', {
                'name': f'User {i}',
                'age': 20 + i
            })
            row_ids.append(row_id)
        
        # Verify all IDs are unique UUIDs
        assert len(set(row_ids)) == 5, "All row IDs should be unique"
        for row_id in row_ids:
            assert isinstance(row_id, str), f"Expected string UUID, got {type(row_id)}"
            assert len(row_id) == 36, f"Expected UUID length 36, got {len(row_id)}"
            assert row_id.count('-') == 4, f"Expected UUID format with 4 dashes, got {row_id}"
    
    def test_uuid_uniqueness_across_tables(self):
        """Test that row IDs are globally unique UUIDs across tables."""
        # Create two tables
        self.db.create_table('users')
        self.db.add_columns('users', {'name': 'text'})
        
        self.db.create_table('products')
        self.db.add_columns('products', {'title': 'text'})
        
        # Insert into first table
        user_id1 = self.db.insert('users', {'name': 'Alice'})
        user_id2 = self.db.insert('users', {'name': 'Bob'})
        
        # Insert into second table
        product_id1 = self.db.insert('products', {'title': 'Widget'})
        product_id2 = self.db.insert('products', {'title': 'Gadget'})
        
        # Verify all IDs are unique UUIDs
        all_ids = [user_id1, user_id2, product_id1, product_id2]
        assert len(set(all_ids)) == 4, "All row IDs should be unique"
        
        # Verify each is a valid UUID
        for row_id in all_ids:
            assert isinstance(row_id, str), f"Expected string UUID, got {type(row_id)}"
            assert len(row_id) == 36, f"Expected UUID length 36, got {len(row_id)}"
            assert row_id.count('-') == 4, f"Expected UUID format with 4 dashes, got {row_id}"
    
    def test_explicit_id_with_uuid_generation(self):
        """Test that explicit row IDs work alongside UUID generation."""
        self.db.create_table('data')
        self.db.add_columns('data', {'value': 'text'})
        
        # Insert with auto-generated UUID
        auto_id1 = self.db.insert('data', {'value': 'auto1'})
        
        # Insert with explicit custom ID
        explicit_id = "custom-1000"
        result_id = self.db.insert('data', {'value': 'explicit'}, id=explicit_id)
        
        # Insert with auto-generated UUID again
        auto_id2 = self.db.insert('data', {'value': 'auto2'})
        
        # Verify explicit ID is preserved
        assert result_id == explicit_id
        
        # Verify auto IDs are UUIDs and unique
        assert isinstance(auto_id1, str) and len(auto_id1) == 36
        assert isinstance(auto_id2, str) and len(auto_id2) == 36
        assert auto_id1 != auto_id2, "Auto-generated UUIDs should be unique"
        assert auto_id1 != explicit_id and auto_id2 != explicit_id
    
    def test_uuid_generation_after_explicit_ids(self):
        """Test UUID generation works correctly after explicit IDs."""
        self.db.create_table('items')
        self.db.add_columns('items', {'name': 'text'})
        
        # Insert several items with explicit IDs
        self.db.insert('items', {'name': 'item1'}, id="explicit-100")
        self.db.insert('items', {'name': 'item2'}, id="explicit-200")
        
        # Insert with auto-generated UUIDs
        auto_id1 = self.db.insert('items', {'name': 'auto1'})
        auto_id2 = self.db.insert('items', {'name': 'auto2'})
        
        # Auto IDs should be unique UUIDs, not affected by explicit IDs
        assert isinstance(auto_id1, str) and len(auto_id1) == 36
        assert isinstance(auto_id2, str) and len(auto_id2) == 36
        assert auto_id1 != auto_id2, "Auto-generated UUIDs should be unique"
        assert auto_id1 not in ["explicit-100", "explicit-200"]
        assert auto_id2 not in ["explicit-100", "explicit-200"]
    
    def test_uuid_generation_efficiency(self):
        """Test that UUID generation is efficient (no database round-trips)."""
        self.db.create_table('test')
        self.db.add_columns('test', {'data': 'text'})
        
        # Generate multiple UUIDs and verify they're unique
        import time
        start_time = time.time()
        
        uuids = []
        for i in range(100):
            row_id = self.db.insert('test', {'data': f'test{i}'})
            uuids.append(row_id)
        
        end_time = time.time()
        
        # Should be fast since no sequence table round-trips
        assert end_time - start_time < 5.0, "UUID generation should be fast"
        
        # All UUIDs should be unique
        assert len(set(uuids)) == 100, "All UUIDs should be unique"
        
        # All should be valid UUID format
        for uuid_str in uuids:
            assert isinstance(uuid_str, str) and len(uuid_str) == 36
    
    def test_concurrent_uuid_simulation(self):
        """Test UUID uniqueness in simulated concurrent scenario."""
        self.db.create_table('concurrent_test')
        self.db.add_columns('concurrent_test', {'thread_id': 'integer', 'data': 'text'})
        
        # Simulate multiple "threads" inserting data
        all_ids = []
        for thread_id in range(3):
            for item in range(5):
                row_id = self.db.insert('concurrent_test', {
                    'thread_id': thread_id,
                    'data': f'thread_{thread_id}_item_{item}'
                })
                all_ids.append(row_id)
        
        # Verify all IDs are unique UUIDs
        assert len(set(all_ids)) == 15, "All row IDs should be unique"
        for row_id in all_ids:
            assert isinstance(row_id, str) and len(row_id) == 36, f"Invalid UUID: {row_id}"
    
    def test_uuid_with_upsert(self):
        """Test that upserts work correctly with UUID row IDs."""
        self.db.create_table('upsert_test')
        self.db.add_columns('upsert_test', {'name': 'text', 'value': 'integer'})
        
        # Insert initial data with auto UUIDs
        id1 = self.db.insert('upsert_test', {'name': 'Alice', 'value': 10})
        id2 = self.db.insert('upsert_test', {'name': 'Bob', 'value': 20})
        
        # Upsert using existing row_id (should update)
        updated_id = self.db.upsert('upsert_test', {'name': 'Alice Updated', 'value': 15}, id=id1)
        
        # Insert new data with auto UUID
        id3 = self.db.insert('upsert_test', {'name': 'Charlie', 'value': 30})
        
        # Verify IDs are correct
        assert updated_id == id1, "Upsert should return same row ID"
        assert isinstance(id3, str) and len(id3) == 36, "New ID should be valid UUID"
        assert id3 != id1 and id3 != id2, "New UUID should be unique"
        
        # Verify data integrity
        data = self.db.query('upsert_test')
        assert len(data) == 3, "Should have 3 rows total"
        
        # Find Alice's record and verify it was updated
        alice_record = next(row for row in data if row['id'] == id1)
        assert alice_record['name'] == 'Alice Updated'
        assert alice_record['value'] == 15


class TestUUIDsAPI:
    """Test UUIDs through different API entry points."""
    
    def setup_method(self):
        """Setup test database."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        # Initialize database
        synthdb.database.make_db(self.db_path, 'sqlite')
    
    def teardown_method(self):
        """Cleanup test database."""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass
    
    def test_core_api_uuids(self):
        """Test UUIDs via core API functions."""
        from synthdb.core import create_table
        from synthdb.api import insert
        
        # Create table
        table_id = create_table('core_test', self.db_path, 'sqlite')
        assert isinstance(table_id, int)
        
        # Add columns and insert data
        db = synthdb.connect(self.db_path, 'sqlite')
        db.add_columns('core_test', {'name': 'text'})
        
        # Test auto UUID generation
        row_id1 = insert('core_test', {'name': 'Test1'}, connection_info=self.db_path, backend_name='sqlite')
        row_id2 = insert('core_test', {'name': 'Test2'}, connection_info=self.db_path, backend_name='sqlite')
        
        assert isinstance(row_id1, str) and len(row_id1) == 36, f"Expected UUID, got {row_id1}"
        assert isinstance(row_id2, str) and len(row_id2) == 36, f"Expected UUID, got {row_id2}"
        assert row_id1 != row_id2, "UUIDs should be unique"
    
    def test_connection_api_uuids(self):
        """Test UUIDs via Connection API."""
        db = synthdb.connect(self.db_path, 'sqlite')
        
        db.create_table('connection_test')
        db.add_columns('connection_test', {'data': 'text'})
        
        # Insert multiple rows and verify unique UUIDs
        ids = []
        for i in range(4):
            row_id = db.insert('connection_test', {'data': f'data_{i}'})
            ids.append(row_id)
        
        # Verify all are unique UUIDs
        assert len(set(ids)) == 4, "All UUIDs should be unique"
        for row_id in ids:
            assert isinstance(row_id, str) and len(row_id) == 36, f"Expected UUID, got {row_id}"
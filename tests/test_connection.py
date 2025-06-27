"""Tests for the SynthDB Connection class."""

import pytest
import tempfile
import os
import synthdb


class TestSynthDBConnection:
    """Test the SynthDB connection class."""
    
    def setup_method(self):
        """Set up test database."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        # Create connection
        self.db = synthdb.connect(self.db_path, backend='sqlite', auto_init=True)
    
    def teardown_method(self):
        """Clean up test database."""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass
    
    def test_connection_creation(self):
        """Test creating a connection."""
        db = synthdb.connect(self.db_path, backend='sqlite')
        assert isinstance(db, synthdb.Connection)
        assert db.connection_info == self.db_path
        assert db.backend_name == 'sqlite'
    
    def test_connect_function(self):
        """Test the connect convenience function."""
        db = synthdb.connect(self.db_path, 'sqlite')
        assert isinstance(db, synthdb.Connection)
    
    def test_create_table(self):
        """Test creating a table."""
        table_id = self.db.create_table('users')
        assert isinstance(table_id, int)
        assert table_id >= 0
        
        # Verify table exists
        tables = self.db.list_tables()
        table_names = [t['name'] for t in tables]
        assert 'users' in table_names
    
    def test_add_columns(self):
        """Test adding columns with type inference."""
        self.db.create_table('products')
        
        column_ids = self.db.add_columns('products', {
            'name': 'text',                    # Explicit type
            'price': 19.99,                   # Infer real
            'stock': 100,                     # Infer integer
            'created': '2023-12-25'          # Infer timestamp
        })
        
        assert len(column_ids) == 4
        assert all(isinstance(col_id, int) for col_id in column_ids.values())
        
        # Verify columns exist
        columns = self.db.list_columns('products')
        column_names = [c['name'] for c in columns]
        for expected_col in ['name', 'price', 'stock', 'created']:
            assert expected_col in column_names
    
    def test_insert_auto_id(self):
        """Test inserting data with auto-generated ID."""
        self.db.create_table('users')
        self.db.add_columns('users', {
            'name': 'text',
            'age': 25,
            'email': 'user@example.com'
        })
        
        # Insert with auto-generated ID
        user_id = self.db.insert('users', {
            'name': 'John Doe',
            'age': 30,
            'email': 'john@example.com'
        })
        
        assert isinstance(user_id, str)
        assert len(user_id) == 36  # UUID4 length
        assert user_id.count('-') == 4  # UUID4 format
        
        # Verify data was inserted
        users = self.db.query('users')
        assert len(users) == 1
        assert users[0]['name'] == 'John Doe'
        assert users[0]['age'] == 30
        assert users[0]['email'] == 'john@example.com'
        assert users[0]['row_id'] == user_id
    
    def test_insert_explicit_id(self):
        """Test inserting data with explicit ID."""
        self.db.create_table('users')
        self.db.add_columns('users', {'name': 'text'})
        
        # Insert with explicit ID
        explicit_id = "custom-uuid-100"
        result_id = self.db.insert('users', {'name': 'Jane Doe'}, row_id=explicit_id)
        assert result_id == explicit_id
        
        # Verify data was inserted
        users = self.db.query('users')
        assert len(users) == 1
        assert users[0]['row_id'] == explicit_id
        assert users[0]['name'] == 'Jane Doe'
    
    def test_insert_single_column(self):
        """Test inserting single column data."""
        self.db.create_table('users')
        self.db.add_columns('users', {'name': 'text', 'age': 25})
        
        # Insert single column
        user_id = self.db.insert('users', 'name', 'Alice')
        
        # Verify data was inserted
        users = self.db.query('users', f'row_id = "{user_id}"')
        assert len(users) == 1
        assert users[0]['name'] == 'Alice'
        assert users[0]['age'] is None  # Other columns should be null
    
    def test_query(self):
        """Test querying data."""
        self.db.create_table('products')
        self.db.add_columns('products', {
            'name': 'text',
            'price': 19.99,
            'active': True
        })
        
        # Insert test data
        self.db.insert('products', {'name': 'Product A', 'price': 10.0, 'active': True})
        self.db.insert('products', {'name': 'Product B', 'price': 20.0, 'active': False})
        self.db.insert('products', {'name': 'Product C', 'price': 30.0, 'active': True})
        
        # Refresh views to ensure data is visible
        self.db.refresh_views()
        
        # Query all products
        all_products = self.db.query('products')
        assert len(all_products) == 3
        
        # Query with WHERE clause
        expensive = self.db.query('products', 'price > 15')
        assert len(expensive) == 2
        
        active = self.db.query('products', 'active = 1')
        assert len(active) == 2
    
    def test_upsert(self):
        """Test upsert functionality."""
        self.db.create_table('users')
        self.db.add_columns('users', {
            'name': 'text',
            'email': 'user@example.com',
            'age': 25
        })
        
        # Insert new user with specific ID
        target_id = "100"
        user_id = self.db.upsert('users', {
            'name': 'John Doe',
            'email': 'john@example.com',
            'age': 30
        }, row_id=target_id)
        
        assert user_id == target_id
        users = self.db.query('users')
        assert len(users) == 1
        assert users[0]['name'] == 'John Doe'
        assert users[0]['age'] == 30
        
        # Update existing user (same row_id)
        updated_id = self.db.upsert('users', {
            'name': 'John Smith',  # Updated name
            'email': 'john.smith@example.com',  # Updated email
            'age': 31  # Updated age
        }, row_id=target_id)
        
        # Should be same ID
        assert updated_id == user_id
        
        # Verify update
        users = self.db.query('users')
        assert len(users) == 1  # Still only one user
        assert users[0]['name'] == 'John Smith'
        assert users[0]['age'] == 31
    
    def test_list_tables(self):
        """Test listing tables."""
        # Initially no tables
        tables = self.db.list_tables()
        user_tables = [t for t in tables if not t['name'].startswith('sqlite_')]
        assert len(user_tables) == 0
        
        # Create some tables
        self.db.create_table('users')
        self.db.create_table('products')
        
        tables = self.db.list_tables()
        table_names = [t['name'] for t in tables]
        assert 'users' in table_names
        assert 'products' in table_names
    
    def test_list_columns(self):
        """Test listing columns."""
        self.db.create_table('users')
        
        # Initially no columns
        columns = self.db.list_columns('users')
        assert len(columns) == 0
        
        # Add columns
        self.db.add_columns('users', {
            'name': 'text',
            'age': 25,
            'score': 95.5
        })
        
        columns = self.db.list_columns('users')
        assert len(columns) == 3
        
        column_names = [c['name'] for c in columns]
        assert 'name' in column_names
        assert 'age' in column_names
        assert 'score' in column_names
        
        # Check data types
        name_col = next(c for c in columns if c['name'] == 'name')
        age_col = next(c for c in columns if c['name'] == 'age')
        score_col = next(c for c in columns if c['name'] == 'score')
        
        assert name_col['data_type'] == 'text'
        assert age_col['data_type'] == 'integer'
        assert score_col['data_type'] == 'real'
    
    def test_error_handling(self):
        """Test error handling."""
        # Try to insert into non-existent table
        with pytest.raises(ValueError, match="Table 'nonexistent' not found"):
            self.db.insert('nonexistent', {'name': 'test'})
        
        # Try to insert into non-existent column
        self.db.create_table('users')
        self.db.add_columns('users', {'name': 'text'})
        
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            self.db.insert('users', {'nonexistent': 'test'})
        
        # Insert with existing ID should update the value (not raise error)
        user_id = self.db.insert('users', {'name': 'John'})
        # This should update the existing row, not raise an error
        self.db.insert('users', {'name': 'Jane'}, row_id=user_id)
        
        # Verify the update happened
        users = self.db.query('users', f'row_id = "{user_id}"')
        assert len(users) == 1
        assert users[0]['name'] == 'Jane'  # Should be updated to Jane
    
    def test_repr(self):
        """Test string representation."""
        db_repr = repr(self.db)
        assert 'Connection' in db_repr
        assert 'sqlite' in db_repr.lower()
"""
Tests for protected name validation in SynthDB.

Tests that reserved column names like 'row_id' and core internal table names
are properly protected and cannot be used for user-defined tables/columns.
"""

import pytest
import tempfile
import os
import synthdb


class TestProtectedNames:
    """Test protected table and column name validation."""
    
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
    
    def test_protected_column_name_id(self):
        """Test that 'id' cannot be used as a column name."""
        self.db.create_table('users')
        
        # Test via add_column method
        with pytest.raises(ValueError, match="Column name 'id' is protected"):
            self.db.add_column('users', 'id', 'text')
    
    def test_protected_column_name_case_insensitive(self):
        """Test that protected column names are case insensitive."""
        self.db.create_table('users')
        
        # Test different cases
        with pytest.raises(ValueError, match="Column name 'ID' is protected"):
            self.db.add_column('users', 'ID', 'text')
        
        with pytest.raises(ValueError, match="Column name 'Id' is protected"):
            self.db.add_column('users', 'Id', 'text')
    
    def test_protected_column_name_add_columns(self):
        """Test that 'id' cannot be used via add_columns method."""
        self.db.create_table('products')
        
        # Test via add_columns method
        with pytest.raises(ValueError, match="Column name 'id' is protected"):
            self.db.add_columns('products', {
                'name': 'text',
                'id': 'integer'  # This should fail
            })
    
    def test_protected_table_name_table_definitions(self):
        """Test that core internal table names cannot be used."""
        # Test core metadata table
        with pytest.raises(ValueError, match="Table name 'table_definitions' conflicts with internal SynthDB tables"):
            self.db.create_table('table_definitions')
    
    def test_protected_table_name_column_definitions(self):
        """Test that column_definitions table name is protected."""
        with pytest.raises(ValueError, match="Table name 'column_definitions' conflicts with internal SynthDB tables"):
            self.db.create_table('column_definitions')
    
    def test_protected_table_name_value_tables(self):
        """Test that type-specific value table names are protected."""
        protected_tables = [
            'text_values',
            'integer_values', 
            'real_values',
            'timestamp_values'
        ]
        
        for table_name in protected_tables:
            with pytest.raises(ValueError, match=f"Table name '{table_name}' conflicts with internal SynthDB tables"):
                self.db.create_table(table_name)
    
    def test_protected_table_name_row_metadata(self):
        """Test that row_metadata table name is protected."""
        with pytest.raises(ValueError, match="Table name 'row_metadata' conflicts with internal SynthDB tables"):
            self.db.create_table('row_metadata')
    
    def test_protected_table_names_case_insensitive(self):
        """Test that protected table names are case insensitive."""
        # Test different cases for a core table
        with pytest.raises(ValueError, match="Table name 'TABLE_DEFINITIONS' conflicts with internal SynthDB tables"):
            self.db.create_table('TABLE_DEFINITIONS')
        
        with pytest.raises(ValueError, match="Table name 'Table_Definitions' conflicts with internal SynthDB tables"):
            self.db.create_table('Table_Definitions')
    
    def test_valid_table_names_allowed(self):
        """Test that valid, non-protected table names are allowed."""
        # These should all work fine
        valid_names = [
            'users',
            'products', 
            'orders',
            'my_table',
            'user_data',
            'product_catalog',
            'text_data',  # Similar but not exactly 'text_values'
            'table_info'  # Similar but not exactly 'table_definitions'
        ]
        
        for table_name in valid_names:
            table_id = self.db.create_table(table_name)
            assert isinstance(table_id, int)
    
    def test_valid_column_names_allowed(self):
        """Test that valid, non-protected column names are allowed."""
        self.db.create_table('test_table')
        
        # These should all work fine
        valid_names = [
            'record_id',   # Similar but not 'id'
            'user_id',     # Contains 'id' but not reserved 'id'
            'row_data',    # Contains 'row' but not 'id'  
            'name',
            'email',
            'created_at',
            'updated_at'
        ]
        
        column_ids = {}
        for col_name in valid_names:
            column_id = self.db.add_column('test_table', col_name, 'text')
            column_ids[col_name] = column_id
            assert isinstance(column_id, int)
        
        # Verify all columns were created
        columns = self.db.list_columns('test_table')
        column_names = [col['name'] for col in columns]
        for valid_name in valid_names:
            assert valid_name in column_names
    
    def test_error_message_helpful(self):
        """Test that error messages are helpful and informative."""
        self.db.create_table('users')
        
        # Test column error message
        try:
            self.db.add_column('users', 'id', 'text')
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_msg = str(e)
            assert 'id' in error_msg
            assert 'protected' in error_msg
            assert 'Protected column names: id' in error_msg
        
        # Test table error message
        try:
            self.db.create_table('table_definitions')
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_msg = str(e)
            assert 'table_definitions' in error_msg
            assert 'conflicts with internal SynthDB tables' in error_msg


class TestProtectedNamesAPI:
    """Test protected names validation through different API entry points."""
    
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
    
    def test_core_api_column_protection(self):
        """Test column protection via core API functions."""
        from synthdb.core import create_table, add_column
        
        # Create table should work
        table_id = create_table('users', self.db_path, 'sqlite')
        assert isinstance(table_id, int)
        
        # Adding protected column should fail
        with pytest.raises(ValueError, match="Column name 'id' is protected"):
            add_column('users', 'id', 'text', self.db_path, 'sqlite')
    
    def test_core_api_table_protection(self):
        """Test table protection via core API functions."""
        from synthdb.core import create_table
        
        # Protected table should fail
        with pytest.raises(ValueError, match="Table name 'row_metadata' conflicts with internal SynthDB tables"):
            create_table('row_metadata', self.db_path, 'sqlite')
    
    def test_api_add_columns_protection(self):
        """Test column protection via api.add_columns function."""
        from synthdb.api import add_columns
        from synthdb.core import create_table
        
        # Create table first
        create_table('products', self.db_path, 'sqlite')
        
        # Protected column in bulk add should fail
        with pytest.raises(ValueError, match="Column name 'id' is protected"):
            add_columns('products', {
                'name': 'text',
                'price': 'real',
                'id': 'integer'  # This should fail
            }, self.db_path, 'sqlite')
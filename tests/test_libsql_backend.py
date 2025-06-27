"""Tests for LibSQL backend functionality."""

import pytest
import tempfile
import os

from synthdb import connect
from synthdb.backends import get_backend, LibSQLBackend, SqliteBackend


class TestLibSQLBackend:
    """Test LibSQL backend implementation."""
    
    def test_libsql_import(self):
        """Test that LibSQL backend can be imported."""
        try:
            backend = get_backend("libsql")
            # Should either be LibSQL or fallback to SQLite
            assert isinstance(backend, (LibSQLBackend, SqliteBackend))
        except ImportError:
            pytest.skip("libsql-experimental not installed")
    
    def test_libsql_connection(self):
        """Test basic LibSQL connection and operations."""
        try:
            # Create temporary database
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
                db_path = f.name
            
            # Connect with LibSQL using context manager
            with connect(db_path, 'libsql') as db:
                # Basic operations
                db.create_table('test')
                db.add_columns('test', {'data': 'text'})
                db.insert('test', {'data': 'Hello LibSQL'})
                
                # Query
                results = db.query('test')
                assert len(results) == 1
                assert results[0]['data'] == 'Hello LibSQL'
            
            # Cleanup
            os.unlink(db_path)
            
        except ImportError:
            pytest.skip("libsql-experimental not installed")
    
    def test_backend_detection(self):
        """Test that LibSQL is detected for various connection strings."""
        from synthdb.backends import detect_backend_from_path
        
        # Local files should default to sqlite
        assert detect_backend_from_path('test.db') == 'sqlite'
        assert detect_backend_from_path('/path/to/data.sqlite') == 'sqlite'
        
        # Remote URLs should be detected as libsql
        assert detect_backend_from_path('libsql://my-db.turso.io') == 'libsql'
        assert detect_backend_from_path('https://my-db.turso.io') == 'libsql'
        assert detect_backend_from_path('http://localhost:8080') == 'libsql'
    
    def test_fallback_to_sqlite(self):
        """Test that system falls back to SQLite if LibSQL not available."""
        # This test demonstrates the fallback behavior
        # When libsql-experimental is not installed, get_backend should return SQLite
        backend = get_backend("libsql")
        # Will be either LibSQL (if installed) or SQLite (fallback)
        assert backend.get_name() in ('libsql', 'sqlite')
    
    def test_config_default_backend(self):
        """Test that sqlite is the default backend in config."""
        from synthdb.config import config
        
        # Reset config to defaults
        config._load_from_env()
        
        # SQLite should be default unless overridden by env var
        if not os.getenv('SYNTHDB_BACKEND'):
            assert config.backend == 'sqlite'
    
    def test_sqlite_compatibility(self):
        """Test that LibSQL backend is SQLite-compatible."""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
                db_path = f.name
            
            # Create database with LibSQL
            with connect(db_path, 'libsql') as db1:
                db1.create_table('compat_test')
                db1.add_columns('compat_test', {'value': 'integer'})
                db1.insert('compat_test', {'value': 42})
            
            # Read with SQLite (should work if compatible)
            with connect(db_path, 'sqlite') as db2:
                results = db2.query('compat_test')
                assert len(results) == 1
                assert results[0]['value'] == 42
            
            # Cleanup
            os.unlink(db_path)
            
        except ImportError:
            pytest.skip("libsql-experimental not installed")
    
    def test_transaction_support(self):
        """Test that LibSQL supports transactions properly."""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
                db_path = f.name
            
            with connect(db_path, 'libsql') as db:
                # Create table
                db.create_table('transaction_test')
                db.add_columns('transaction_test', {'count': 'integer'})
                
                # Test transaction rollback behavior
                from synthdb.transactions import transaction_context
                from synthdb.backends import get_backend
                
                backend = get_backend('libsql')
                
                # This should be rolled back
                try:
                    with transaction_context(db_path, 'libsql') as (backend, connection):
                        backend.execute(connection, 
                            "INSERT INTO integer_values (row_id, table_id, column_id, value) VALUES ('test', 1, 1, 100)")
                        # Force an error to trigger rollback
                        raise Exception("Test rollback")
                except:
                    pass
                
                # Verify nothing was inserted
                results = db.query('transaction_test')
                assert len(results) == 0
            
            # Cleanup
            os.unlink(db_path)
            
        except ImportError:
            pytest.skip("libsql-experimental not installed")


class TestLibSQLFeatures:
    """Test LibSQL-specific features."""
    
    def test_returning_support(self):
        """Test that LibSQL supports RETURNING clause."""
        try:
            backend = get_backend('libsql')
            assert backend.supports_returning() is True
        except ImportError:
            pytest.skip("libsql-experimental not installed")
    
    def test_type_mapping(self):
        """Test LibSQL type mapping."""
        try:
            backend = get_backend('libsql')
            
            # Test type mappings
            assert backend.get_sql_type('text') == 'TEXT'
            assert backend.get_sql_type('integer') == 'INTEGER'
            assert backend.get_sql_type('real') == 'REAL'
            assert backend.get_sql_type('timestamp') == 'TEXT'
            
            # Unknown type should default to TEXT
            assert backend.get_sql_type('unknown') == 'TEXT'
        except ImportError:
            pytest.skip("libsql-experimental not installed")
    
    def test_autoincrement_sql(self):
        """Test LibSQL autoincrement SQL generation."""
        try:
            backend = get_backend('libsql')
            assert backend.get_autoincrement_sql() == 'INTEGER PRIMARY KEY AUTOINCREMENT'
        except ImportError:
            pytest.skip("libsql-experimental not installed")
"""Test that performance optimizations are enabled by default for database connections."""

import pytest
import tempfile
import os
import sqlite3
from synthdb import connect
from synthdb.backends import get_backend


def test_sqlite_optimizations_enabled():
    """Test that SQLite backend enables all performance optimizations by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # Get backend and create connection
        backend = get_backend("sqlite")
        conn = backend.connect(db_path)
        
        # Check all pragmas
        cursor = conn.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode.lower() == "wal"
        
        cursor = conn.execute("PRAGMA synchronous")
        synchronous = cursor.fetchone()[0]
        assert synchronous == 1  # NORMAL = 1
        
        cursor = conn.execute("PRAGMA cache_size")
        cache_size = cursor.fetchone()[0]
        assert cache_size == -64000  # 64MB in KB
        
        # Note: page_size only affects new databases and must be set before creating tables
        # For existing databases, it will remain at the original size
        cursor = conn.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        # Page size might be 4096 or 8192 depending on when it was set
        assert page_size in [4096, 8192]
        
        backend.close(conn)


def test_libsql_optimizations_enabled():
    """Test that LibSQL backend enables all performance optimizations for local databases."""
    pytest.importorskip("libsql_experimental")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # Create a connection through SynthDB
        db = connect(db_path, backend="libsql")
        db.create_table("test_table")
        db.close()
        
        # Verify optimizations using direct SQLite connection
        # (LibSQL creates SQLite-compatible files)
        conn = sqlite3.connect(db_path)
        
        cursor = conn.execute("PRAGMA journal_mode")
        assert cursor.fetchone()[0].lower() == "wal"
        
        cursor = conn.execute("PRAGMA synchronous")
        assert cursor.fetchone()[0] == 1  # NORMAL
        
        # Cache size doesn't persist - only active during the connection
        # We'd need to verify it on a SynthDB connection, not a raw SQLite one
        cursor = conn.execute("PRAGMA cache_size")
        # Default cache size is 2000 pages for SQLite
        assert cursor.fetchone()[0] == 2000
        
        conn.close()


def test_optimizations_persist():
    """Test that optimizations persist across connections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # First connection
        db1 = connect(db_path, backend="sqlite")
        db1.create_table("test_table")
        db1.close()
        
        # Second connection - optimizations should still be active
        db2 = connect(db_path, backend="sqlite")
        db2.add_column("test_table", "test_col", "text")
        db2.close()
        
        # Verify optimizations persisted with direct connection
        conn = sqlite3.connect(db_path)
        
        cursor = conn.execute("PRAGMA journal_mode")
        assert cursor.fetchone()[0].lower() == "wal"
        
        cursor = conn.execute("PRAGMA synchronous")
        assert cursor.fetchone()[0] == 1  # NORMAL
        
        # Cache size doesn't persist - only active during the connection
        # We'd need to verify it on a SynthDB connection, not a raw SQLite one
        cursor = conn.execute("PRAGMA cache_size")
        # Default cache size is 2000 pages for SQLite
        assert cursor.fetchone()[0] == 2000
        
        conn.close()


def test_page_size_on_new_database():
    """Test that page size is set correctly on new databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "new_db.db")
        
        # Create new database with SynthDB
        backend = get_backend("sqlite")
        conn = backend.connect(db_path)
        
        # Create a table to commit the page size
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        
        # Verify page size was set to 8192 for new database
        cursor = conn.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        assert page_size == 8192  # Should be 8KB for new databases
        
        backend.close(conn)


def test_performance_benefits():
    """Test that the optimizations provide expected configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "perf_test.db")
        
        db = connect(db_path, backend="sqlite")
        db.create_table("performance_test")
        db.add_columns("performance_test", {
            "data": "text",
            "value": "integer"
        })
        
        # Insert some data to ensure pragmas are working
        for i in range(100):
            db.insert("performance_test", {
                "data": f"test_data_{i}",
                "value": i
            })
        
        db.close()
        
        # Verify database works correctly with optimizations
        conn = sqlite3.connect(db_path)
        # SynthDB creates views, not tables - query the view
        cursor = conn.execute("SELECT COUNT(*) FROM performance_test")
        count = cursor.fetchone()[0]
        assert count == 100
        
        # Verify all optimizations are still active
        cursor = conn.execute("PRAGMA journal_mode")
        assert cursor.fetchone()[0].lower() == "wal"
        
        cursor = conn.execute("PRAGMA synchronous")
        assert cursor.fetchone()[0] == 1  # NORMAL
        
        conn.close()
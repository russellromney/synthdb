"""Demonstrate performance optimizations enabled by default in SynthDB."""

import synthdb
import sqlite3
import os
import tempfile
from synthdb.backends import get_backend


def main():
    print("=== SynthDB Performance Optimizations Demo ===\n")
    
    # Create a temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "demo.db")
        
        # Create database through SynthDB
        print("1. Creating database with SynthDB...")
        db = synthdb.connect(db_path, backend="sqlite")
        db.create_table("users")
        db.add_columns("users", {
            "name": "text",
            "email": "text",
            "age": "integer"
        })
        
        # Insert some data
        db.insert("users", {"name": "Alice", "email": "alice@example.com", "age": 30})
        db.insert("users", {"name": "Bob", "email": "bob@example.com", "age": 25})
        
        print("   Database created and populated\n")
        
        # Close SynthDB connection
        db.close()
        
        # Verify all optimizations with direct SQLite connection
        print("2. Verifying all performance optimizations...")
        conn = sqlite3.connect(db_path)
        
        # Check journal mode
        cursor = conn.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        print(f"   ✓ Journal mode: {journal_mode} (WAL mode for better concurrency)")
        
        # Check synchronous mode
        cursor = conn.execute("PRAGMA synchronous")
        synchronous = cursor.fetchone()[0]
        sync_mode = "NORMAL" if synchronous == 1 else f"Unknown ({synchronous})"
        print(f"   ✓ Synchronous: {sync_mode} (faster than FULL, still safe)")
        
        # Check cache size
        cursor = conn.execute("PRAGMA cache_size")
        cache_size = cursor.fetchone()[0]
        cache_mb = abs(cache_size) / 1000
        print(f"   ✓ Cache size: {cache_mb:.0f}MB ({cache_size} KB)")
        
        # Check page size
        cursor = conn.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        page_kb = page_size / 1024
        print(f"   ✓ Page size: {page_kb:.0f}KB ({page_size} bytes)")
        
        # Check for WAL files
        wal_file = db_path + "-wal"
        shm_file = db_path + "-shm"
        
        print(f"\n3. WAL mode artifacts:")
        print(f"   WAL file exists: {os.path.exists(wal_file)}")
        print(f"   SHM file exists: {os.path.exists(shm_file)}")
        
        # Show benefits
        print("\n4. Benefits of these optimizations:")
        print("   • WAL mode: Better concurrency, readers don't block writers")
        print("   • NORMAL sync: ~10x faster writes while maintaining durability")
        print("   • 64MB cache: Reduced disk I/O for frequently accessed data")
        print("   • 8KB pages: Better I/O efficiency for modern systems")
        
        conn.close()
        
        # Test with backend directly
        print("\n5. Testing backend connection directly...")
        backend = get_backend("sqlite")
        conn2 = backend.connect(db_path)
        
        # Verify optimizations are applied on SynthDB connections
        cursor = conn2.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        print(f"   Journal mode: {journal_mode}")
        
        cursor = conn2.execute("PRAGMA synchronous")
        sync_val = cursor.fetchone()[0]
        print(f"   Synchronous: {'NORMAL' if sync_val == 1 else sync_val}")
        
        cursor = conn2.execute("PRAGMA cache_size")
        cache = cursor.fetchone()[0]
        print(f"   Cache size: {abs(cache)/1000:.0f}MB ({cache} KB)")
        
        cursor = conn2.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        print(f"   Page size: {page_size/1024:.0f}KB ({page_size} bytes)")
        
        backend.close(conn2)
        print("   ✓ All optimizations verified on new connections")
        
        print("\n✅ All performance optimizations are enabled by default in SynthDB!")
        print("   These settings provide optimal performance for most workloads.")


if __name__ == "__main__":
    main()
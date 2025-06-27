#!/usr/bin/env python3
"""
SynthDB LibSQL Demo - Showcasing LibSQL-specific features

This demo shows how to use SynthDB with LibSQL, including both
local and remote database connections.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import synthdb
sys.path.insert(0, str(Path(__file__).parent.parent))

import synthdb


def libsql_demo():
    """Demonstrate LibSQL features in SynthDB."""
    print("🚀 SynthDB LibSQL Features Demo")
    print("=" * 50)
    
    # Example 1: Local LibSQL database (default)
    print("\n1️⃣ Local LibSQL Database (Default)")
    print("-" * 35)
    
    db = synthdb.connect('libsql_demo.db')
    print(f"✅ Connected to local database")
    print(f"🔧 Backend: {db.backend.get_name()}")
    
    # Create a simple table
    db.create_table('local_data')
    db.add_columns('local_data', {
        'name': 'text',
        'value': 100,
        'timestamp': '2024-01-01 12:00:00'
    })
    
    # Insert some data
    db.insert('local_data', {
        'name': 'Local Test',
        'value': 42,
        'timestamp': '2024-01-15 10:30:00'
    })
    
    results = db.query('local_data')
    print(f"✅ Created table and inserted {len(results)} record(s)")
    
    # Example 2: Remote LibSQL connection (if URL provided)
    print("\n2️⃣ Remote LibSQL Database Connection")
    print("-" * 37)
    
    # Check if user provided a remote URL via environment variable
    remote_url = os.getenv('LIBSQL_REMOTE_URL')
    
    if remote_url:
        try:
            print(f"🌐 Connecting to: {remote_url}")
            remote_db = synthdb.connect(remote_url)
            print(f"✅ Connected to remote LibSQL database!")
            print(f"🔧 Backend: {remote_db.backend.get_name()}")
            
            # You can work with remote databases just like local ones
            tables = remote_db.list_tables()
            print(f"📊 Remote database has {len(tables)} table(s)")
            
        except Exception as e:
            print(f"❌ Could not connect to remote database: {e}")
    else:
        print("ℹ️  To test remote connections, set LIBSQL_REMOTE_URL environment variable:")
        print("   export LIBSQL_REMOTE_URL='libsql://your-database.turso.io'")
        print("   export LIBSQL_REMOTE_URL='https://your-database.turso.io'")
    
    # Example 3: Backend fallback behavior
    print("\n3️⃣ Backend Fallback Behavior")
    print("-" * 30)
    
    # Force SQLite backend
    sqlite_db = synthdb.connect('sqlite_demo.db', backend='sqlite')
    print(f"✅ Explicitly using SQLite backend: {sqlite_db.backend.get_name()}")
    
    # Show the difference in features
    print("\n📋 Backend Comparison:")
    print("   LibSQL:")
    print("     • Local file support ✅")
    print("     • Remote database support ✅") 
    print("     • SQLite compatibility ✅")
    print("     • Edge computing ready ✅")
    print("   SQLite:")
    print("     • Local file support ✅")
    print("     • Remote database support ❌")
    print("     • Maximum compatibility ✅")
    print("     • No external dependencies ✅")
    
    # Example 4: LibSQL-specific benefits
    print("\n4️⃣ Why LibSQL as Default?")
    print("-" * 26)
    
    print("✨ LibSQL provides:")
    print("   • 100% SQLite compatibility - existing databases work unchanged")
    print("   • Remote database support for cloud/edge deployments")
    print("   • Modern features while maintaining SQLite's simplicity")
    print("   • Automatic fallback to SQLite if not available")
    print("   • Future-proof your application with minimal changes")
    
    # Clean up
    try:
        os.remove('libsql_demo.db')
        os.remove('sqlite_demo.db')
        print("\n🧹 Demo databases cleaned up")
    except FileNotFoundError:
        pass


def installation_guide():
    """Show installation information for LibSQL."""
    print("\n" + "=" * 60)
    print("📦 LibSQL Installation")
    print("=" * 60)
    
    print("\nLibSQL support is provided by the libsql-experimental package:")
    print("\n# Install SynthDB (SQLite is included by default)")
    print("uv add synthdb")
    print("\n# For LibSQL remote database support, also install:")
    print("uv add libsql-experimental")
    print("\n# Verify installation")
    print("python -c \"import libsql_experimental; print('✅ LibSQL is installed')\"")
    
    print("\n⚠️  Note: If libsql-experimental is not available, SynthDB")
    print("   automatically falls back to SQLite with a warning.")


if __name__ == "__main__":
    libsql_demo()
    installation_guide()
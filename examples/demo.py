#!/usr/bin/env python3
"""
SynthDB Demo - Modern Connection-Based API

This demo showcases SynthDB's API that provides
a clean, intuitive interface for working with schema-on-write databases.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import synthdb
sys.path.insert(0, str(Path(__file__).parent.parent))

import synthdb


def main_demo():
    """Demonstrate SynthDB's modern connection-based API."""
    print("🚀 SynthDB Modern API Demo")
    print("=" * 50)
    
    # Connect to database - the modern way
    print("\n📦 Connecting to Database...")
    db = synthdb.connect('demo.db')  # Uses SQLite by default
    print(f"✅ Connected: {db}")
    print(f"🔧 Backend: {db.backend_name or 'auto-detected'}")
    
    print("\n1️⃣ Create Table and Add Columns")
    print("-" * 35)
    
    # Create table
    db.create_table('users')
    print("✅ Created 'users' table")
    
    # Add columns with bulk operation and type inference
    column_ids = db.add_columns('users', {
        'name': 'text',                           # Explicit type
        'email': 'user@example.com',              # Infers 'text'
        'age': 25,                                # Infers 'integer'
        'salary': 75000.50,                       # Infers 'real'
        'last_login': '2023-12-25 10:30:00',     # Infers 'timestamp'
        'bio': 'Software engineer and cat lover', # Explicit text
        'active': True                            # Infers 'integer' (boolean)
    })
    
    print(f"✅ Added {len(column_ids)} columns:")
    for col_name, col_id in column_ids.items():
        print(f"   • {col_name} (ID: {col_id})")
    
    print("\n2️⃣ Insert Data (Multiple Methods)")
    print("-" * 38)
    
    # Auto-generated ID with complete row data
    alice_id = db.insert('users', {
        'name': 'Alice Johnson',
        'email': 'alice@example.com',
        'age': 28,
        'salary': 85000.0,
        'last_login': '2023-12-25 09:15:30',
        'bio': 'Senior software engineer specializing in database systems'
    })
    print(f"✅ Inserted Alice with auto-generated ID: {alice_id}")
    
    # Explicit ID
    bob_id = db.insert('users', {
        'name': 'Bob Smith',
        'email': 'bob@example.com', 
        'age': 35,
        'salary': 92000.0,
        'bio': 'DevOps engineer and automation enthusiast'
    }, row_id="100")
    print(f"✅ Inserted Bob with explicit ID: {bob_id}")
    
    # Partial data insert
    carol_id = db.insert('users', {
        'name': 'Carol Brown',
        'email': 'carol@example.com',
        'age': 32,
        'active': True,
        'salary': 68000.0
    }, row_id="200")
    print(f"✅ Inserted Carol with explicit ID: {carol_id}")
    
    print("\n3️⃣ Query Data (Simple & Powerful)")
    print("-" * 36)
    
    # Query all users
    all_users = db.query('users')
    print(f"✅ Total users: {len(all_users)}")
    
    # Query with conditions
    active_users = db.query('users', 'active = \"true\"')
    print(f"✅ Active users: {len(active_users)}")
    
    senior_users = db.query('users', 'age >= 30')
    print(f"✅ Senior users (30+): {len(senior_users)}")
    
    high_earners = db.query('users', 'salary > 80000')
    print(f"✅ High earners (>$80k): {len(high_earners)}")
    
    print("\n📊 User Details:")
    for user in all_users:
        name = user.get('name', 'N/A')
        age = user.get('age', 'N/A')
        email = user.get('email', 'N/A')
        salary = user.get('salary', 'N/A')
        print(f"   Row {user['row_id']}: {name} ({age}) - {email} - ${salary}")
    
    print("\n4️⃣ Upsert Operations")
    print("-" * 22)
    
    # Insert new user via upsert
    david_id = "500"  # Specific ID for David
    result_id = db.upsert('users', {
        'name': 'David Wilson',
        'email': 'david@example.com',
        'age': 29,
        'salary': 78000.0,
        'active': True
    }, row_id=david_id)
    print(f"✅ Upserted new user David: {result_id}")
    
    # Update existing user via upsert (same row_id)
    david_updated_id = db.upsert('users', {
        'name': 'David Wilson-Smith',  # Updated name
        'email': 'david.wilson@example.com',  # Updated email
        'age': 30,                      # Updated age  
        'salary': 82000.0               # Updated salary
    }, row_id=david_id)
    print(f"✅ Updated David's info, same ID: {david_updated_id}")
    
    print("\n5️⃣ Database Inspection")
    print("-" * 25)
    
    # List tables
    tables = db.list_tables()
    print(f"✅ Tables in database: {len(tables)}")
    for table in tables:
        print(f"   • {table['name']} (ID: {table['id']}, Created: {table['created_at']})")
    
    # List columns
    columns = db.list_columns('users')
    print(f"\n✅ Columns in 'users': {len(columns)}")
    for column in columns:
        print(f"   • {column['name']:15} | {column['data_type']:10} | ID: {column['id']}")
    
    print("\n6️⃣ Error Handling")
    print("-" * 19)
    
    try:
        # Try to insert with duplicate explicit ID
        db.insert('users', {'name': 'Test User'}, row_id=alice_id)
    except ValueError as e:
        print(f"✅ Caught duplicate ID error: {e}")
    
    try:
        # Try to insert invalid column
        db.insert('users', {'invalid_column': 'test'})
    except ValueError as e:
        print(f"✅ Caught invalid column error: {e}")
    
    try:
        # Try to use protected column name
        db.add_column('users', 'row_id', 'text')
    except ValueError as e:
        print(f"✅ Caught protected column name error: {e}")
    
    try:
        # Try to use protected table name
        db.create_table('text_values')
    except ValueError as e:
        print(f"✅ Caught protected table name error: {e}")
    
    print("\n7️⃣ Final Results")
    print("-" * 18)
    
    final_users = db.query('users')
    print(f"\n📈 Final user count: {len(final_users)}")
    
    print("\n📋 Complete User Database:")
    print("-" * 80)
    for user in final_users:
        name = user.get('name') or 'N/A'
        email = user.get('email') or 'N/A'
        age = user.get('age')
        salary = user.get('salary')
        active = '✅' if user.get('active') == 'true' else '❌'
        age_str = str(age) if age is not None else 'N/A'
        salary_str = str(salary) if salary is not None else 'N/A'
        row_id_short = user['row_id'][:8] + "..." if len(user['row_id']) > 8 else user['row_id']
        print(f"   {row_id_short:12} | {name:20} | {email:20} | {age_str:3} | ${salary_str:8} | {active}")
    
    print("\n8️⃣ Column Management Operations")
    print("-" * 33)
    
    # Create a test table for column operations
    db.create_table('products')
    print("✅ Created 'products' table")
    
    # Add columns including ones we'll delete
    db.add_columns('products', {
        'name': 'text',
        'price': 'real',
        'deprecated_field': 'text',
        'temp_data': 'text'
    })
    print("✅ Added columns to products")
    
    # Insert some test data
    db.insert('products', {
        'name': 'Widget',
        'price': 19.99,
        'deprecated_field': 'old_value',
        'temp_data': 'temporary'
    })
    
    # Example 1: Soft delete (preserves data)
    db.delete_column('products', 'deprecated_field')
    print("✅ Soft deleted 'deprecated_field' column (data preserved)")
    
    # Example 2: Hard delete (permanently removes data)
    db.delete_column('products', 'temp_data', hard_delete=True)
    print("✅ Hard deleted 'temp_data' column (data permanently removed)")
    
    # Example 3: List columns with and without deleted
    visible_cols = db.list_columns('products')
    all_cols = db.list_columns('products', include_deleted=True)
    
    print("\n📊 Column Listing Results:")
    print(f"   • Visible columns: {[c['name'] for c in visible_cols]}")
    print(f"   • All columns (including deleted): {[c['name'] for c in all_cols]}")
    print(f"   • Soft deleted columns: {[c['name'] for c in all_cols if c['deleted_at']]}")
    
    # Example 4: Column copying
    db.create_table('customers')
    email_col_id = db.copy_column("users", "email", "customers", "contact_email", copy_data=False)
    print(f"\n✅ Copied email column structure to customers (ID: {email_col_id})")
    
    print("\n✨ Demo completed successfully!")


def connection_examples():
    """Show different ways to connect to databases."""
    print("\n" + "=" * 60)
    print("🔗 Connection Examples")
    print("=" * 60)
    
    print("\n💾 Local Database Files:")
    print("   • LibSQL (default): synthdb.connect('app.db')")
    print("   • SQLite (explicit): synthdb.connect('app.db', backend='sqlite')")
    
    print("\n🌐 Remote Database Connections:")
    print("   • Turso: synthdb.connect('libsql://your-database.turso.io')")
    print("   • HTTP: synthdb.connect('https://your-database.turso.io')")
    
    print("\n🔧 Backend Selection:")
    print("   • Auto-detection: synthdb.connect('app.db')  # Uses LibSQL")
    print("   • Remote URL: synthdb.connect('libsql://...')  # Always LibSQL")
    print("   • Explicit backend: synthdb.connect('app.db', backend='sqlite')")
    print("   • Fallback: If LibSQL unavailable, automatically uses SQLite")


def api_benefits():
    """Highlight the benefits of the connection-based API."""
    print("\n" + "=" * 60)
    print("🎯 Connection API Benefits")
    print("=" * 60)
    
    print("\n✅ Clean & Intuitive:")
    print("   • Object-oriented design familiar to developers")
    print("   • Connection established once, reused everywhere")
    print("   • No repetitive connection parameter passing")
    
    print("\n🚀 Developer Experience:")
    print("   • Auto-completion in IDEs works perfectly")
    print("   • Method chaining and fluent interface")
    print("   • Clear error messages with helpful context")
    
    print("\n🔧 Powerful Features:")
    print("   • Automatic type inference from sample data")
    print("   • Bulk column operations")
    print("   • Built-in upsert functionality")
    print("   • Auto-generated or explicit row IDs")
    print("   • Column copying (structure-only or with data)")
    print("   • Soft delete (preserves data) or hard delete (permanent)")
    print("   • List deleted columns for recovery")
    
    print("\n🛡️ Robust & Reliable:")
    print("   • Enhanced error handling and validation")
    print("   • Transaction safety")
    print("   • Connection pooling and management")
    print("   • Modern, clean API design")


def cleanup():
    """Clean up demo files."""
    try:
        os.remove('demo.db')
        print("\n🧹 Demo database cleaned up")
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    try:
        main_demo()
        connection_examples()
        api_benefits()
    finally:
        cleanup()
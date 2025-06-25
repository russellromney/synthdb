#!/usr/bin/env python3
"""
Demo script showing SynthDB functionality.

This script demonstrates the toy examples from the original implementation,
now using the organized package structure.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import synthdb
sys.path.insert(0, str(Path(__file__).parent.parent))

from synthdb import (
    make_db, create_table, add_column, insert_typed_value, 
    create_table_views, query_view, export_table_structure,
    list_tables, list_columns
)


def create_demo_data():
    """Create demo data similar to the original make_values function"""
    print("=== Creating Demo Data ===\n")
    
    # Create users table
    print("Creating 'users' table...")
    users_table_id = create_table('users')
    
    # Add columns to users table
    print("Adding columns to 'users' table...")
    first_name_col = add_column('users', 'first_name', 'text')
    last_name_col = add_column('users', 'last_name', 'text')
    age_col = add_column('users', 'age', 'integer')
    active_col = add_column('users', 'active', 'boolean')
    
    # Create pets table
    print("Creating 'pets' table...")
    pets_table_id = create_table('pets')
    
    # Add columns to pets table
    print("Adding columns to 'pets' table...")
    name_col = add_column('pets', 'name', 'text')
    species_col = add_column('pets', 'species', 'text')
    weight_col = add_column('pets', 'weight', 'real')
    vaccinated_col = add_column('pets', 'vaccinated', 'boolean')
    
    # Insert users data
    print("Inserting users data...")
    insert_typed_value(0, users_table_id, first_name_col, 'John', 'text')
    insert_typed_value(0, users_table_id, last_name_col, 'Smith', 'text') 
    insert_typed_value(0, users_table_id, age_col, 30, 'integer')
    insert_typed_value(0, users_table_id, active_col, True, 'boolean')
    
    insert_typed_value(1, users_table_id, first_name_col, 'Jane', 'text')
    insert_typed_value(1, users_table_id, last_name_col, 'Jones', 'text')
    insert_typed_value(1, users_table_id, age_col, 25, 'integer')
    insert_typed_value(1, users_table_id, active_col, False, 'boolean')
    
    # Insert pets data
    print("Inserting pets data...")
    insert_typed_value(0, pets_table_id, name_col, 'Doggo', 'text')
    insert_typed_value(0, pets_table_id, species_col, 'dog', 'text')
    insert_typed_value(0, pets_table_id, weight_col, 25.5, 'real')
    insert_typed_value(0, pets_table_id, vaccinated_col, True, 'boolean')
    
    insert_typed_value(1, pets_table_id, name_col, 'Catsy', 'text')
    insert_typed_value(1, pets_table_id, species_col, 'cat', 'text')
    insert_typed_value(1, pets_table_id, weight_col, 4.2, 'real')
    insert_typed_value(1, pets_table_id, vaccinated_col, False, 'boolean')
    
    print("Demo data created successfully!\n")


def demonstrate_queries():
    """Demonstrate various query capabilities"""
    print("=== Demonstrating Queries ===\n")
    
    # List all tables
    print("All tables:")
    tables = list_tables()
    for table in tables:
        print(f"  - {table['name']} (ID: {table['id']}, Created: {table['created_at']})")
    print()
    
    # Show table structures
    for table in tables:
        table_name = table['name']
        print(f"Columns in '{table_name}' table:")
        columns = list_columns(table_name)
        for col in columns:
            print(f"  - {col['name']} ({col['data_type']})")
        print()
    
    # Query users table
    print("All users:")
    users = query_view('users')
    for user in users:
        print(f"  - {user['first_name']} {user['last_name']}, age {user['age']}, active: {user['active']}")
    print()
    
    # Query with WHERE clause
    print("Active users only:")
    active_users = query_view('users', "active = 'true'")
    for user in active_users:
        print(f"  - {user['first_name']} {user['last_name']}")
    print()
    
    # Query pets table
    print("All pets:")
    pets = query_view('pets')
    for pet in pets:
        print(f"  - {pet['name']} the {pet['species']}, weight: {pet['weight']} lbs, vaccinated: {pet['vaccinated']}")
    print()
    
    # Query with WHERE clause
    print("Vaccinated pets only:")
    vaccinated_pets = query_view('pets', "vaccinated = 'true'")
    for pet in vaccinated_pets:
        print(f"  - {pet['name']} the {pet['species']}")
    print()


def demonstrate_export():
    """Demonstrate table structure export"""
    print("=== Demonstrating Table Export ===\n")
    
    tables = list_tables()
    for table in tables:
        table_name = table['name']
        print(f"CREATE TABLE structure for '{table_name}':")
        create_sql = export_table_structure(table_name)
        print(create_sql)
        print()


def demonstrate_schema_evolution():
    """Demonstrate adding columns to existing tables"""
    print("=== Demonstrating Schema Evolution ===\n")
    
    # Add a new column to users table
    print("Adding 'email' column to users table...")
    email_col = add_column('users', 'email', 'text')
    
    # Insert email data for existing users
    print("Adding email data for existing users...")
    # Find users table ID
    tables = list_tables()
    users_table_id = next(t['id'] for t in tables if t['name'] == 'users')
    
    insert_typed_value(0, users_table_id, email_col, 'john.smith@example.com', 'text')
    insert_typed_value(1, users_table_id, email_col, 'jane.jones@example.com', 'text')
    
    # Query updated table
    print("Users table with new email column:")
    users = query_view('users')
    for user in users:
        print(f"  - {user['first_name']} {user['last_name']} <{user['email']}>")
    print()


def main():
    """Main demo function"""
    print("SynthDB Demo")
    print("=" * 50)
    
    # Clean up any existing database
    if os.path.exists('db.db'):
        os.unlink('db.db')
    
    # Initialize database
    print("Initializing database...")
    make_db()
    print("Database initialized!\n")
    
    # Run demonstrations
    create_demo_data()
    demonstrate_queries()
    demonstrate_export()
    demonstrate_schema_evolution()
    
    print("Demo completed successfully!")
    print("\nThe database file 'db.db' contains all the demo data.")
    print("You can explore it further using the SynthDB package or CLI.")


if __name__ == "__main__":
    main()
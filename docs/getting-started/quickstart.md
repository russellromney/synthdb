# Quick Start Guide

Get up and running with SynthDB in just a few minutes! This guide will walk you through the essential operations.

## Your First Database

Let's create a simple user management system:

```python
import synthdb

# Create a connection (database file will be created automatically)
db = synthdb.connect('my_app.limbo')  # Uses Limbo by default

# Create a table
db.create_table('users')

# Add columns with automatic type inference
db.add_columns('users', {
    'name': 'Alice',           # Infers 'text' type
    'email': 'alice@test.com', # Infers 'text' type
    'age': 25,                 # Infers 'integer' type
    'salary': 75000.50         # Infers 'real' type
})

print("✅ Table created with columns!")
```

## Insert Data

SynthDB automatically assigns unique row IDs:

```python
# Insert with auto-generated ID
user_id = db.insert('users', {
    'name': 'Bob Smith',
    'email': 'bob@example.com',
    'age': 30,
    'active': True,
    'metadata': {'role': 'user', 'department': 'engineering'}
})

print(f"✅ Inserted user with ID: {user_id}")

# Insert with explicit ID (useful for migrations)
db.insert('users', {
    'name': 'Carol Brown',
    'email': 'carol@example.com',
    'age': 28,
    'active': False
}, row_id="1000")

print("✅ Inserted user with explicit ID: 1000")
```

## Query Data

Query your data with familiar SQL-like syntax:

```python
# Get all users
all_users = db.query('users')
print(f"Total users: {len(all_users)}")

# Filter with WHERE clause
active_users = db.query('users', 'active = "true"')
print(f"Active users: {len(active_users)}")

# Filter by age
young_users = db.query('users', 'age < 30')
print(f"Users under 30: {len(young_users)}")

# Display results
for user in active_users:
    print(f"  {user['name']} ({user['age']}) - {user['email']}")
```

## Update Data

Use upsert to insert or update based on row_id:

```python
# Get the user's row_id first (from a previous insert or query)
users = db.query('users', 'name = "Bob Smith"')
user_id = users[0]['row_id'] if users else 100  # Use existing ID or specific new ID

# Update existing user or insert with specified ID
updated_id = db.upsert('users', {
    'name': 'Bob Smith',
    'email': 'bob.smith@newcompany.com',  # Updated email
    'age': 31,                           # Updated age
    'active': True,
    'metadata': {'role': 'senior_engineer'}  # Updated role
}, row_id=user_id)

print(f"✅ Upserted user with ID: {updated_id}")
```

## Evolve Your Schema

Add new columns without migrations:

```python
# Add new columns to existing table
db.add_columns('users', {
    'created_at': '2024-01-01',  # Infers 'timestamp' type
    'department': 'Engineering'  # Infers 'text' type
})

# Insert data with new columns
db.insert('users', {
    'name': 'David Wilson',
    'email': 'david@example.com',
    'age': 35,
    'active': True,
    'created_at': '2024-06-26',
    'salary': 95000.0,
    'skills': ['python', 'rust', 'database']
})

print("✅ Schema evolved! New columns added.")
```

## Copy Columns

Easily duplicate column structures between tables:

```python
# Create a customers table
db.create_table('customers')
db.add_columns('customers', {'company': 'text'})

# Copy just the column structure (fast)
db.copy_column('users', 'email', 'customers', 'contact_email', copy_data=False)

# Copy column structure AND data (complete copy)
db.copy_column('users', 'age', 'customers', 'contact_age', copy_data=True)

# Copy within the same table (backup/duplicate)
db.copy_column('users', 'email', 'users', 'backup_email', copy_data=True)

print("✅ Column copying complete!")

# Verify the results
customers = db.query('customers')
print(f"Customers table now has {len(db.list_columns('customers'))} columns")
```

## Inspect Your Database

Explore your database structure:

```python
# List all tables
tables = db.list_tables()
for table in tables:
    print(f"Table: {table['name']} (ID: {table['id']})")

# List columns in a table
columns = db.list_columns('users')
for col in columns:
    print(f"  Column: {col['name']} ({col['data_type']})")

# Get final count
final_users = db.query('users')
print(f"\n📊 Final user count: {len(final_users)}")
```

## CLI Quick Start

SynthDB also provides a powerful CLI for database operations:

```bash
# Initialize a database
sdb database init my_cli_app.limbo  # Uses Limbo by default

# Create a table
sdb table create products

# Add columns
sdb table add column products name text
sdb table add column products price real
sdb table add column products quantity integer

# Insert data
sdb add products '{"name": "Widget", "price": 19.99, "quantity": 100}'
sdb add products '{"name": "Gadget", "price": 29.99, "quantity": 50}'

# Query data
sdb query products
sdb query products --where "price > 20"

# List tables and columns
sdb table list
sdb table list products
```

## Backend Selection

Choose the right backend for your needs:

```python
# Use Limbo for best performance (default)
db = synthdb.connect('fast_app.limbo')  # Uses Limbo automatically

# Use SQLite for maximum stability  
db = synthdb.connect('stable_app.db', backend='sqlite')

# Auto-detection by file extension
db = synthdb.connect('app.limbo')  # Uses Limbo (recommended)
db = synthdb.connect('app.db')     # Uses SQLite
```

## Error Handling

SynthDB provides helpful error messages:

```python
try:
    # Try to insert duplicate ID
    db.insert('users', {'name': 'Test'}, row_id="1000")
except ValueError as e:
    print(f"Expected error: {e}")

try:
    # Try to access non-existent column
    db.query('users', 'nonexistent_column = "value"')
except Exception as e:
    print(f"Expected error: {e}")

try:
    # Try to use protected column name
    db.add_column('users', 'row_id', 'text')
except ValueError as e:
    print(f"Expected error: {e}")

try:
    # Try to use protected table name
    db.create_table('text_values')
except ValueError as e:
    print(f"Expected error: {e}")
```

## Complete Example

Here's everything together in a complete script:

```python
import synthdb

def main():
    # Connect to database
    db = synthdb.connect('quickstart.limbo')  # Uses Limbo by default
    
    # Create and populate table
    db.create_table('products')
    db.add_columns('products', {
        'name': 'text',
        'description': 'A sample product',
        'price': 19.99,
        'in_stock': True,
        'tags': ['electronics', 'gadgets']
    })
    
    # Insert some products
    products = [
        {'name': 'Smartphone', 'price': 599.99, 'in_stock': True, 'tags': ['electronics', 'mobile']},
        {'name': 'Laptop', 'price': 1299.99, 'in_stock': True, 'tags': ['electronics', 'computer']},
        {'name': 'Headphones', 'price': 199.99, 'in_stock': False, 'tags': ['electronics', 'audio']},
    ]
    
    for product in products:
        product_id = db.insert('products', product)
        print(f"Added {product['name']} with ID {product_id}")
    
    # Query and display results
    expensive_products = db.query('products', 'price > 500')
    print(f"\nExpensive products ({len(expensive_products)}):")
    for product in expensive_products:
        status = "✅ In Stock" if product['in_stock'] == 'true' else "❌ Out of Stock"
        print(f"  {product['name']}: ${product['price']} - {status}")

if __name__ == "__main__":
    main()
```

## Next Steps

Now that you've seen the basics, explore more advanced features:

- **[Connection API Guide](../user-guide/connection-api.md)** - Deep dive into the Python API
- **[CLI Usage](../user-guide/cli.md)** - Master the command-line interface
- **[Working with Tables](../user-guide/tables.md)** - Advanced table operations
- **[Data Operations](../user-guide/data-operations.md)** - Complex queries and data manipulation
- **[Examples](../examples/basic.md)** - Real-world usage patterns

## Clean Up

If you want to remove the test databases created in this guide:

```bash
rm quickstart.limbo my_app.limbo my_cli_app.limbo
```
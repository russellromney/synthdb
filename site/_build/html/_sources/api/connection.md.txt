# Connection API Reference

The `Connection` class is the primary interface for interacting with SynthDB databases. It provides a clean, object-oriented API for all database operations.

## Quick Reference

```python
import synthdb

# Create connection
db = synthdb.connect('app.limbo')  # Uses Limbo by default

# Table operations
db.create_table('users')
db.add_columns('users', {'name': 'text', 'age': 25})

# Data operations
user_id = db.insert('users', {'name': 'Alice', 'age': 30})
users = db.query('users', 'age > 25')

# Inspection
tables = db.list_tables()
columns = db.list_columns('users')
```

## Connection Class

::: synthdb.Connection
    options:
      show_source: true
      show_root_heading: true
      show_root_toc_entry: true
      heading_level: 3

## Factory Function

::: synthdb.connect
    options:
      show_source: true
      show_root_heading: true
      show_root_toc_entry: true
      heading_level: 3

## Connection Methods

### Table Management

#### create_table()

::: synthdb.Connection.create_table
    options:
      show_source: true

#### add_column()

::: synthdb.Connection.add_column
    options:
      show_source: true

#### add_columns()

::: synthdb.Connection.add_columns
    options:
      show_source: true

### Data Operations

#### insert()

::: synthdb.Connection.insert
    options:
      show_source: true

#### query()

::: synthdb.Connection.query
    options:
      show_source: true

#### upsert()

::: synthdb.Connection.upsert
    options:
      show_source: true

### Database Inspection

#### list_tables()

::: synthdb.Connection.list_tables
    options:
      show_source: true

#### list_columns()

::: synthdb.Connection.list_columns
    options:
      show_source: true

#### refresh_views()

::: synthdb.Connection.refresh_views
    options:
      show_source: true

## Examples

### Basic Usage

```python
import synthdb

# Create connection
db = synthdb.connect('example.limbo')  # Uses Limbo by default

# Create table and add columns
db.create_table('products')
db.add_columns('products', {
    'name': 'text',
    'price': 19.99,  # Infers real type
    'active': True   # Infers boolean type
})

# Insert data
product_id = db.insert('products', {
    'name': 'Widget',
    'price': 29.99,
    'active': True
})

# Query data
products = db.query('products', 'active = "true"')
```

### Advanced Patterns

```python
# Batch operations
products = [
    {'name': 'Widget A', 'price': 19.99},
    {'name': 'Widget B', 'price': 29.99},
    {'name': 'Widget C', 'price': 39.99},
]

for product in products:
    db.insert('products', product)

# Upsert with key columns
db.upsert('products', {
    'name': 'Widget A',
    'price': 24.99,  # Updated price
    'active': True
}, key_columns=['name'])

# Complex queries
expensive = db.query('products', 'price > 25 AND active = "true"')
```

### Error Handling

```python
try:
    # Insert with explicit ID
    db.insert('products', {'name': 'Test'}, row_id=1000)
    
    # Try duplicate ID
    db.insert('products', {'name': 'Test2'}, row_id=1000)
    
except ValueError as e:
    print(f"Duplicate ID error: {e}")

try:
    # Query non-existent column
    db.query('products', 'nonexistent = "value"')
    
except Exception as e:
    print(f"Query error: {e}")
```

## Connection Configuration

### Backend Selection

```python
# Explicit backend selection
db_limbo = synthdb.connect('app.limbo')                    # Uses Limbo (default)
db_sqlite = synthdb.connect('app.db', backend='sqlite')     # Uses SQLite explicitly

# Auto-detection by file extension
db_auto_limbo = synthdb.connect('app.limbo')   # Uses Limbo (recommended)
db_auto_sqlite = synthdb.connect('app.db')     # Uses SQLite
```

### Connection Options

```python
# Auto-initialization (default: True)
db = synthdb.connect('app.limbo', auto_init=True)

# Manual initialization
db = synthdb.connect('app.limbo', auto_init=False)
# ... perform setup operations ...
db.init_db()  # Call when ready
```

## Performance Considerations

### Batch Operations

For multiple inserts, consider batching:

```python
# Instead of individual inserts
for item in large_dataset:
    db.insert('table', item)

# Consider using upsert for updates
for item in large_dataset:
    db.upsert('table', item, key_columns=['id'])
```

### Query Optimization

```python
# Use specific WHERE clauses
users = db.query('users', 'active = "true" AND age > 25')

# Limit results when possible
recent_users = db.query('users', 'created_at > "2024-01-01"')
```

### Connection Reuse

```python
# Reuse connections for multiple operations
db = synthdb.connect('app.limbo')

# Multiple operations on same connection
db.create_table('users')
db.add_columns('users', {...})
db.insert('users', {...})
results = db.query('users')

# No need to reconnect for each operation
```

## See Also

- [CLI Reference](cli.md) - Command-line interface
- [Core Functions](core.md) - Lower-level functions
- [Examples](../examples/basic.md) - Real-world usage patterns
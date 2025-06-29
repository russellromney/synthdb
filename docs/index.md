# SynthDB Documentation

A flexible database system with schema-on-write capabilities. SynthDB makes it easy to work with evolving data structures while maintaining familiar SQL-like interfaces.

## What is SynthDB?

SynthDB is a modern database system that adapts to your data as it evolves. Unlike traditional databases that require predefined schemas, SynthDB allows you to add columns and modify data structures on the fly while maintaining data integrity and providing familiar query interfaces.

## Key Features

- **Flexible Schema**: Store data with dynamic schemas that evolve as your application grows
- **Automatic Views**: Automatically generated SQL views that present data as traditional tables
- **Schema Evolution**: Add columns to existing tables without migration scripts
- **Type Safety**: Type-specific storage tables for optimal performance and data integrity
- **History Tracking**: Built-in audit trail with creation and update timestamps
- **Safe SQL Execution**: Execute custom SELECT queries with built-in safety validation
- **CLI Interface**: Rich command-line interface for database operations
- **Python API**: Clean, well-documented Python API for programmatic access
- **SQLite Backend**: Built on SQLite - the world's most widely deployed database engine
- **Remote Support**: Optional LibSQL backend for remote database connectivity

## Quick Example

```python
import synthdb

# Create a connection (SQLite by default)
db = synthdb.connect('app.db')

# Or connect to remote database (requires libsql-experimental)
# db = synthdb.connect('libsql://your-database.turso.io')

# Create table and add columns
db.create_table('users')
db.add_columns('users', {
    'name': 'text',
    'email': 'user@example.com',  # Infers text type
    'age': 25,                    # Infers integer type
    'score': 95.5                 # Infers real type
})

# Insert data with auto-generated ID
user_id = db.insert('users', {
    'name': 'Alice',
    'email': 'alice@example.com',
    'age': 30,
    'active': True
})

# Query data
users = db.query('users', 'age > 25')

# Execute custom SQL queries
results = db.execute_sql("""
    SELECT name, age, AVG(score) OVER () as avg_score
    FROM users
    WHERE active = 1
""")
```

## Getting Started

1. **[Installation](getting-started/installation.md)** - Install SynthDB and its dependencies
2. **[Quick Start](getting-started/quickstart.md)** - Get up and running in minutes
3. **[SQL Queries](getting-started/sql-queries.md)** - Execute safe SQL queries on your data

## Documentation Sections

### 🔧 [API Reference](api/connection.md)
Complete reference for all SynthDB classes, functions, and CLI commands.

### 🛠️ [Development](development/feature-proposals.md)
Information for contributors and developers working on SynthDB itself.

## Community and Support

- **GitHub**: [russellromney/synthdb](https://github.com/russellromney/synthdb)
- **Issues**: [Report bugs and request features](https://github.com/russellromney/synthdb/issues)
- **PyPI**: [Install from PyPI](https://pypi.org/project/synthdb/)

## License

SynthDB is released under the MIT License. See the [LICENSE](https://github.com/russellromney/synthdb/blob/main/LICENSE) file for details.
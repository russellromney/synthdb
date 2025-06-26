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
- **CLI Interface**: Rich command-line interface for database operations
- **Python API**: Clean, well-documented Python API for programmatic access
- **Multiple Backends**: Supports Limbo and SQLite backends

## Quick Example

```python
import synthdb

# Create a connection
db = synthdb.connect('app.db')

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
```

## Getting Started

1. **[Installation](getting-started/installation.md)** - Install SynthDB and its dependencies
2. **[Quick Start](getting-started/quickstart.md)** - Get up and running in minutes
3. **[Basic Concepts](getting-started/concepts.md)** - Understand SynthDB's core concepts
4. **[Connection API](user-guide/connection-api.md)** - Learn the modern Python API

## Documentation Sections

### 📚 [User Guide](user-guide/connection-api.md)
Learn how to use SynthDB effectively with step-by-step guides and examples.

### 🔧 [API Reference](api/connection.md)
Complete reference for all SynthDB classes, functions, and CLI commands.

### 🚀 [Examples](examples/basic.md)
Real-world examples and patterns for common use cases.

### ⚙️ [Advanced Topics](advanced/backends.md)
Deep dive into SynthDB's architecture, performance tuning, and troubleshooting.

### 🛠️ [Development](development/contributing.md)
Information for contributors and developers working on SynthDB itself.

## Community and Support

- **GitHub**: [russellromney/synthdb](https://github.com/russellromney/synthdb)
- **Issues**: [Report bugs and request features](https://github.com/russellromney/synthdb/issues)
- **PyPI**: [Install from PyPI](https://pypi.org/project/synthdb/)

## License

SynthDB is released under the MIT License. See the [LICENSE](https://github.com/russellromney/synthdb/blob/main/LICENSE) file for details.
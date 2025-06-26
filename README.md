# SynthDB

A flexible database system with schema-on-write capabilities. SynthDB makes it easy to work with evolving data structures while maintaining familiar SQL-like interfaces.

## Features

- **Flexible Schema**: Store data with dynamic schemas that evolve as your application grows
- **Automatic Views**: Automatically generated SQL views that present data as traditional tables
- **Schema Evolution**: Add columns to existing tables without migration scripts
- **Type Safety**: Type-specific storage tables for optimal performance and data integrity
- **History Tracking**: Built-in audit trail with creation and update timestamps
- **CLI Interface**: Rich command-line interface for database operations
- **Python API**: Clean, well-documented Python API for programmatic access
- **Multiple Backends**: Supports Limbo and SQLite backends
- **Production Ready**: SQLite for stable production deployments
- **Configurable**: Choose your backend based on performance and stability needs

## Installation

### 🚀 **Quick Install with uv (Recommended)**

```bash
# Install uv (fastest Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install SynthDB
uv add synthdb
```

### **Traditional Installation**

```bash
pip install synthdb
```

**Backend Options:**
- **Limbo** (default): Fast, modern SQLite-compatible database written in Rust
- **SQLite**: Traditional SQLite for maximum stability and compatibility

### **Development Setup**

```bash
git clone https://github.com/russellromney/synthdb
cd synthdb

# With uv (recommended - 10-100x faster!)
uv sync                 # Install dependencies
make dev               # Setup development environment
make test              # Run tests
make lint              # Run linting

# With pip (traditional)
pip install -e ".[dev]"
```

## Quick Start

### CLI Usage

```bash
# Initialize a new database (uses Limbo by default)
synthdb database init
# or use the shorter alias:
sdb database init

# Use different backends
sdb database init                    # Uses Limbo by default
sdb database init --backend sqlite   # Use SQLite explicitly

# Environment variable (optional)
export SYNTHDB_BACKEND=limbo  # Already the default
sdb database init

# Create a table
sdb table create products

# Add columns
sdb table add column products name text
sdb table add column products price real
sdb table add column products active boolean

# Insert data
sdb insert products 0 name "Widget" text
sdb insert products 0 price "19.99" real
sdb insert products 0 active "true" boolean

# Query data
sdb query products
sdb query products --where "price > 15"

# List tables and columns
sdb table list
sdb table list products

# Show detailed information
sdb database info
sdb table show products

# Export table structure
sdb table export products
```

### Python API

#### 🔗 **Connection API (Recommended - Clean & Modern)**

```python
import synthdb

# Create a connection - handles everything automatically
db = synthdb.connect('app.limbo')  # Uses Limbo by default

# Create table and add columns in one go
db.create_table('products')
db.add_columns('products', {
    'name': 'text',                  # Explicit type
    'description': 'A great product', # Infers text
    'price': 19.99,                  # Infers real
    'stock': 100,                    # Infers integer
    'active': True,                  # Infers boolean
    'metadata': {'category': 'tech'}, # Infers json
    'created': '2023-12-25'          # Infers timestamp
})

# Insert data with auto-generated IDs
product_id = db.insert('products', {
    'name': 'Awesome Widget',
    'description': 'The best widget you\'ll ever use',
    'price': 29.99,
    'stock': 50,
    'active': True,
    'metadata': {'category': 'widgets', 'featured': True}
})

# Insert with explicit ID
db.insert('products', {'name': 'Special Item'}, row_id=1000)

# Single column inserts
db.insert('products', 'name', 'Quick Add')

# Query data - super simple!
all_products = db.query('products')
expensive = db.query('products', 'price > 25')

# Upsert (insert or update)
db.upsert('products', {
    'name': 'Updated Widget',
    'sku': 'WIDGET-001',
    'price': 24.99
}, key_columns=['sku'])

# Database inspection
tables = db.list_tables()
columns = db.list_columns('products')
```

#### 🔧 **Alternative Connection Methods**

```python
# Different backends
db = synthdb.connect('app.limbo')                    # Uses Limbo (default)
db = synthdb.connect('app.db', backend='sqlite')     # Uses SQLite explicitly

# Auto-detection by file extension
db = synthdb.connect('app.limbo')  # Uses Limbo (recommended)
db = synthdb.connect('app.db')     # Uses SQLite
```


## Backend Selection

SynthDB supports two database backends optimized for different use cases:

### Limbo (Default)
- **Pros**: Fastest performance, modern Rust implementation, SQLite-compatible
- **Cons**: Alpha software, may have compatibility issues
- **Best for**: Development, single-user applications, performance testing
- **Concurrency**: Single writer, multiple readers

### SQLite (Stable)
- **Pros**: Battle-tested, maximum compatibility, stable, embedded
- **Cons**: Limited concurrent writes
- **Best for**: Production apps, desktop apps, small web apps, embedded systems
- **Concurrency**: Single writer, multiple readers

### Configuration

```python
# Set backend globally (optional - Limbo is default)
synthdb.set_default_backend("limbo")  # Already the default

# Environment variable (optional)
SYNTHDB_BACKEND=limbo  # Already the default

# File extension hints
# .limbo files use Limbo
# .sqlite/.sqlite3/.db files use SQLite
```

### Performance Comparison

| Backend | Single User | Multi User | Complex Queries | JSON Performance |
|---------|-------------|------------|-----------------|------------------|
| Limbo | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| SQLite | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

## Architecture

SynthDB uses a flexible data model with the following components:

### Core Tables

- **table_definitions**: Metadata about user-defined tables
- **column_definitions**: Metadata about columns in each table
- **{type}_values**: Type-specific value storage (text_values, integer_values, etc.)
- **{type}_value_history**: Audit trail for all value changes

### View Generation

SynthDB automatically creates SQL views for each table that:
- Present data in familiar columnar format
- Include row_id, created_at, and updated_at timestamps
- Handle type conversions (e.g., boolean 1/0 to "true"/"false")
- Update automatically when schema changes

### Supported Data Types

- **text**: String values
- **integer**: Whole numbers
- **real**: Floating-point numbers
- **boolean**: True/false values (stored as integers, displayed as strings)
- **json**: JSON objects and arrays
- **timestamp**: Date/time values

## Examples

See the `examples/` directory for comprehensive usage examples:

```bash
# Modern connection API demo (recommended)
python examples/demo.py
```

**Modern Demo** demonstrates:
- Clean connection-based interface (`synthdb.connect()`)
- Automatic database initialization
- Bulk column creation with type inference
- Auto-generated and explicit row IDs
- Simple querying and upsert operations
- Database inspection and error handling
- Different connection methods
- API benefits and best practices

## Documentation

SynthDB includes comprehensive documentation built with Sphinx and MkDocs Material:

- **📚 [Full Documentation](https://synthdb.readthedocs.io/)** - Complete guides, tutorials, and API reference
- **🚀 [Quick Start Guide](docs/getting-started/quickstart.md)** - Get up and running in minutes
- **🔧 [API Reference](docs/api/connection.md)** - Detailed API documentation
- **💡 [Examples](docs/examples/basic.md)** - Real-world usage patterns
- **🛠️ [Development Guide](docs/development/contributing.md)** - Contributing to SynthDB

### Building Documentation Locally

```bash
# Install documentation dependencies
uv sync --extra docs

# Serve documentation with live reload
make docs-serve
# or
python scripts/build_docs.py serve

# Build static documentation
make docs-build
```

## Development

### Running Tests

```bash
pytest tests/
```

### Project Structure

```
synthdb/
├── synthdb/           # Main package
│   ├── __init__.py   # Public API
│   ├── core.py       # Core database operations
│   ├── database.py   # Database setup
│   ├── views.py      # View management
│   ├── utils.py      # Utility functions
│   ├── types.py      # Type mapping
│   ├── cli.py        # CLI interface
│   └── __main__.py   # python -m synthdb support
├── tests/            # Test suite
├── examples/         # Usage examples
└── pyproject.toml    # Package configuration
```

## API Reference

### 🔗 **Connection API (Recommended)**

#### Connection
- `synthdb.connect(connection_info, backend=None)` - Create database connection

#### Core Methods
- `db.create_table(name)` - Create new table
- `db.add_columns(table, columns_dict)` - Add multiple columns with type inference
- `db.insert(table, data, value=None, row_id=None, force_type=None)` - Insert with auto-generated or explicit IDs

#### Query Methods
- `db.query(table, where_clause=None)` - Query table data
- `db.upsert(table, data, key_columns, row_id=None)` - Insert or update based on key columns

#### Inspection Methods
- `db.list_tables()` - List all tables with metadata
- `db.list_columns(table)` - List columns in table with types and IDs

#### Utility Methods
- `db.refresh_views()` - Regenerate all views


## CLI Commands

> **Note:** You can use `sdb` as a shorter alias for `synthdb` in all commands.

### 🚀 **Quick Commands (Shortcuts)**
- `sdb db init` - Initialize database (shortcut for `database init`)
- `sdb t create <name>` - Create table (shortcut for `table create`)
- `sdb l [table]` - List tables/columns (shortcut for `table list`)
- `sdb q <table>` - Query data (shortcut for `query`)
- `sdb i <table> '<json>'` - Insert data (shortcut for `add`)

### Database Operations
- `sdb database init [--path <path>] [--backend <backend>] [connection options]` - Initialize database
- `sdb db init` - Shortcut for database init
- `sdb database info [--path <path>] [--backend <backend>] [connection options]` - Show database information


### Table Operations
- `sdb table create <name> [--backend <backend>]` - Create table
- `sdb t create <name>` - Shortcut for table create
- `sdb table list [<table>] [--backend <backend>]` - List tables or columns in specific table
- `sdb l [table]` - Shortcut for table list
- `sdb table show <name> [--backend <backend>]` - Show detailed table information
- `sdb table export <name> [--backend <backend>]` - Export table structure
- `sdb table add column <table> <column> <type> [--backend <backend>]` - Add column

### Data Operations
- `sdb add <table> '<json_data>' [--id <row_id>] [--backend <backend>]` - Add data using modern API (auto-generated IDs, type inference)
- `sdb i <table> '<json_data>'` - Shortcut for add
- `sdb query <table> [--where <clause>] [--backend <backend>]` - Query table data
- `sdb q <table>` - Shortcut for query
- `sdb insert <table> <row_id> <column> <value> <type> [--backend <backend>]` - Insert value into specific row/column

> 💡 **Tip**: Use shortcuts for faster development: `sdb db init`, `sdb t create users`, `sdb i users '{"name":"John"}'`, `sdb q users`

> 🔗 **Best Practice**: For complex operations, use the Connection class in Python: `db = synthdb.connect('app.db'); db.insert('users', {...})`

All commands support:
- `--path <path>` to specify database file (defaults to `db.db`)
- `--backend <backend>` to specify backend (`limbo`, `sqlite`)

**Connection Examples:**
```bash
# Local file with Limbo (recommended)
sdb query products --path myapp.limbo

# Local file with SQLite
sdb query products --path myapp.db --backend sqlite

# Environment variable (optional)
export SYNTHDB_BACKEND="limbo"  # Already the default
sdb query products
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Use Cases

SynthDB is ideal for:

- **Rapid prototyping** - Quickly evolve schemas without migrations
- **Analytics platforms** - Flexible data ingestion with strong typing
- **Content management** - Handle varying content structures
- **Data integration** - Normalize disparate data sources
- **Audit systems** - Built-in change tracking and history
- **Microservices** - Each service can define its own schema dynamically

## Performance Considerations

- Views are generated dynamically but cached by SQLite
- Type-specific tables optimize storage and indexing
- History tables provide audit capability with minimal overhead
- Consider partitioning strategies for very large datasets

## Limitations

### Common
- View complexity increases with table width
- Not suitable for high-frequency transactional workloads
- Schema changes require view regeneration

### Backend-Specific
- **SQLite/Limbo**: Limited concurrent write performance
- **Limbo**: Alpha software, potential compatibility issues
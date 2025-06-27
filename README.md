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
- **SQLite Backend**: Built on SQLite, the world's most widely deployed database engine

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
uv add synthdb
```

**Backend:**
- **SQLite**: Default backend - Battle-tested, stable, and available everywhere
- **LibSQL**: Optional backend for remote database support (Turso, etc.)

```bash
# SQLite is included with Python, no additional installation needed
# For LibSQL remote database support:
uv add libsql-experimental
```

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
uv add -e ".[dev]"
```

## Quick Start

### CLI Usage

```bash
# Initialize a new database
synthdb db init
# or use the shorter alias:
sdb db init

# Create a table
sdb table create products

# Add columns
sdb table add column products name text
sdb table add column products price real
sdb table add column products quantity integer

# Insert data
sdb insert products 0 name "Widget" text
sdb insert products 0 price "19.99" real
sdb insert products 0 quantity "100" integer

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

# Create a connection - uses SQLite by default
db = synthdb.connect('app.db')

# Or connect to a remote LibSQL database (Turso, etc.)
db = synthdb.connect('libsql://your-database.turso.io')

# Create table and add columns in one go
db.create_table('products')
db.add_columns('products', {
    'name': 'text',                  # Explicit type
    'description': 'A great product', # Infers text
    'price': 19.99,                  # Infers real
    'stock': 100,                    # Infers integer
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
db.insert('products', {'name': 'Special Item'}, row_id="1000")

# Single column inserts
db.insert('products', 'name', 'Quick Add')

# Query data - super simple!
all_products = db.query('products')
expensive = db.query('products', 'price > 25')

# Upsert (insert or update by row_id)
db.upsert('products', {
    'name': 'Updated Widget',
    'sku': 'WIDGET-001',
    'price': 24.99
}, row_id=product_id)

# Database inspection
tables = db.list_tables()
columns = db.list_columns('products')
```

#### 🔧 **Connection Methods**

```python
# Create database connection (SQLite by default)
db = synthdb.connect('app.db')

# Explicitly use LibSQL backend for remote databases
db = synthdb.connect('libsql://your-database.turso.io')
db = synthdb.connect('https://your-database.turso.io')

# Explicitly specify backend
db = synthdb.connect('app.db', backend='sqlite')  # Default
db = synthdb.connect('app.db', backend='libsql')   # For LibSQL features
```


## Backend

SynthDB uses SQLite as the default backend, with optional LibSQL support for remote databases:

### SQLite (Default)
- **Pros**: Battle-tested, maximum compatibility, stable, embedded, zero-configuration
- **Built-in**: Included with Python - no additional installation required
- **Best for**: Desktop apps, embedded systems, local development
- **File extensions**: .db, .sqlite, .sqlite3

### LibSQL (Optional)
- **What it is**: SQLite-compatible database with additional features
- **Pros**: All SQLite benefits plus remote database support, edge computing ready
- **Remote Support**: Connect to Turso and other LibSQL-compatible services
- **Compatibility**: 100% SQLite compatible - existing SQLite databases work as-is
- **Best for**: Modern applications requiring remote databases, edge computing, distributed systems
- **Installation**: Requires `libsql-experimental` package:
  ```bash
  uv add libsql-experimental
  ```

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
- Handle type conversions (e.g., integer to text)
- Update automatically when schema changes

### Supported Data Types

- **text**: String values
- **integer**: Whole numbers
- **real**: Floating-point numbers
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
- `db.upsert(table, data, row_id)` - Insert or update based on row_id

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
- `sdb i <table> '<data>'` - Insert data (shortcut for `add`)

### Database Operations
- `sdb database init [--path <path>] [connection options]` - Initialize database
- `sdb db init` - Shortcut for database init
- `sdb database info [--path <path>] [connection options]` - Show database information


### Table Operations
- `sdb table create <name>` - Create table
- `sdb t create <name>` - Shortcut for table create
- `sdb table list [<table>]` - List tables or columns in specific table
- `sdb l [table]` - Shortcut for table list
- `sdb table show <name>` - Show detailed table information
- `sdb table export <name>` - Export table structure
- `sdb table add column <table> <column> <type>` - Add column

### Data Operations
- `sdb add <table> '<data>' [--id <row_id>]` - Add data using modern API (auto-generated IDs, type inference)
- `sdb i <table> '<data>'` - Shortcut for add
- `sdb query <table> [--where <clause>]` - Query table data
- `sdb q <table>` - Shortcut for query
- `sdb insert <table> <row_id> <column> <value> <type>` - Insert value into specific row/column

> 💡 **Tip**: Use shortcuts for faster development: `sdb db init`, `sdb t create users`, `sdb i users '{"name":"John"}'`, `sdb q users`

> 🔗 **Best Practice**: For complex operations, use the Connection class in Python: `db = synthdb.connect('app.db'); db.insert('users', {...})`

All commands support:
- `--path <path>` to specify database file (defaults to `db.db`)

**Connection Examples:**
```bash
# Local database file (uses SQLite by default)
sdb query products --path myapp.db

# Remote LibSQL database
sdb query products --path "libsql://your-database.turso.io"

# Explicitly specify backend
sdb query products --path myapp.db --backend sqlite  # Default
sdb query products --path myapp.db --backend libsql  # For LibSQL features
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

## Naming Restrictions

SynthDB enforces naming restrictions to protect internal functionality:

### Protected Column Names
- **`row_id`** - Reserved for SynthDB's internal row identifier
- Column names are case-insensitive, so `ROW_ID`, `Row_Id`, etc. are also protected

### Protected Table Names
SynthDB prevents creating tables with names that conflict with internal tables:

**Core Tables:**
- `table_definitions`, `column_definitions`

**Value Storage Tables:**
- `text_values`, `integer_values`, `real_values`, `timestamp_values`

**Row Metadata Table:**
- `row_metadata`

Table names are also case-insensitive for protection purposes.

### Error Messages
When attempting to use protected names, SynthDB provides clear error messages:
```python
# Column name error
db.add_column('users', 'row_id', 'text')
# ValueError: Column name 'row_id' is protected and cannot be used. Protected column names: row_id

# Table name error  
db.create_table('text_values')
# ValueError: Table name 'text_values' conflicts with internal SynthDB tables and cannot be used. Please choose a different name.
```

## Limitations

### Common
- View complexity increases with table width
- Not suitable for extreme-frequency transactional workloads
- Schema changes require view regeneration
- Not suitable for extremely large workloads (>100GB)
- Computationally more intense than just using a normal table setup

### Backend Specific

#### LibSQL
- Requires `libsql-experimental` package installation
- Remote databases require internet connectivity

#### SQLite
- Limited concurrent write performance (single writer, multiple readers)
- Database size limited by filesystem constraints
- No remote database support
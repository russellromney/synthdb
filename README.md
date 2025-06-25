# SynthDB

A flexible database system with schema-on-write capabilities and automatic view generation. SynthDB makes it easy to work with evolving data structures while maintaining familiar SQL-like interfaces.

## Features

- **Flexible Schema**: Store data with dynamic schemas that evolve as your application grows
- **Automatic Views**: Automatically generated SQL views that present data as traditional tables
- **Schema Evolution**: Add columns to existing tables without migration scripts
- **Type Safety**: Type-specific storage tables for optimal performance and data integrity
- **History Tracking**: Built-in audit trail with creation and update timestamps
- **CLI Interface**: Rich command-line interface for database operations
- **Python API**: Clean, well-documented Python API for programmatic access
- **Multiple Backends**: Supports Limbo, SQLite, PostgreSQL, and MySQL backends
- **Production Ready**: PostgreSQL and MySQL for high-concurrency production deployments
- **Configurable**: Choose your backend based on performance, stability, and scalability needs

## Installation

```bash
pip install synthdb
```

**Backend Options:**
- **Limbo** (default): Fast, modern SQLite-compatible database written in Rust
- **SQLite**: Traditional SQLite for maximum stability  
- **PostgreSQL**: Production-grade with JSONB, concurrent access, replication
- **MySQL**: Enterprise database with JSON support and high performance

**Installation Options:**
```bash
# Default installation (includes Limbo)
pip install synthdb

# With PostgreSQL support
pip install "synthdb[postgresql]"

# With MySQL support  
pip install "synthdb[mysql]"

# With all backends
pip install "synthdb[all]"
```

For development:

```bash
git clone https://github.com/russellromney/synthdb
cd synthdb
pip install -e .
```

## Quick Start

### CLI Usage

```bash
# Initialize a new database (uses Limbo by default)
synthdb database init
# or use the shorter alias:
sdb database init

# Use different backends
sdb database init --backend sqlite
sdb database init --backend postgresql
sdb database init --backend mysql

# PostgreSQL with connection details
sdb database init --backend postgresql --host localhost --port 5432 \
  --database myapp --user myuser --password mypass

# MySQL with connection string
sdb database init mysql://user:pass@localhost:3306/myapp

# Environment variable
export SYNTHDB_BACKEND=postgresql
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

```python
import synthdb

# Initialize database (uses Limbo by default)
synthdb.make_db()

# Or explicitly choose backend
synthdb.make_db(backend_name="sqlite")

# PostgreSQL with connection parameters
synthdb.make_db({
    'host': 'localhost',
    'database': 'myapp',
    'user': 'myuser',
    'password': 'mypass'
}, backend_name="postgresql")

# MySQL with connection string
synthdb.make_db("mysql://user:pass@localhost:3306/myapp")

# Set default backend globally
synthdb.set_default_backend("postgresql")

# Create table and columns
table_id = synthdb.create_table("products")
name_col = synthdb.add_column("products", "name", "text")
price_col = synthdb.add_column("products", "price", "real")

# Insert data
synthdb.insert_typed_value(0, table_id, name_col, "Widget", "text")
synthdb.insert_typed_value(0, table_id, price_col, 19.99, "real")

# Query data
results = synthdb.query_view("products")
filtered = synthdb.query_view("products", "price > 15")

# Export structure
sql = synthdb.export_table_structure("products")
```

## Backend Selection

SynthDB supports four database backends optimized for different use cases:

### Limbo (Default)
- **Pros**: Fastest performance, modern Rust implementation, SQLite-compatible
- **Cons**: Alpha software, may have compatibility issues
- **Best for**: Development, single-user applications, performance testing
- **Concurrency**: Single writer, multiple readers

### SQLite (Stable)
- **Pros**: Battle-tested, maximum compatibility, stable, embedded
- **Cons**: Limited concurrent writes
- **Best for**: Desktop apps, small web apps, embedded systems
- **Concurrency**: Single writer, multiple readers

### PostgreSQL (Production)
- **Pros**: JSONB support, excellent concurrency, ACID compliance, replication
- **Cons**: Requires server setup, more complex deployment
- **Best for**: Production web apps, analytics, multi-user systems
- **Concurrency**: Excellent (MVCC)
- **Query Optimizations**: JSONB indexes, materialized views, partial indexes

### MySQL (Enterprise)
- **Pros**: JSON support, horizontal scaling, enterprise features
- **Cons**: Requires server setup, licensing considerations
- **Best for**: Enterprise applications, high-scale web services
- **Concurrency**: Very good (row-level locking)
- **Query Optimizations**: JSON columns, InnoDB indexes, partitioning

### Configuration

```python
# Set backend globally
synthdb.set_default_backend("postgresql")

# Environment variable
SYNTHDB_BACKEND=postgresql

# Connection strings
postgresql://user:pass@host:port/database
mysql://user:pass@host:port/database

# File extension hints
# .limbo files use Limbo
# .sqlite/.sqlite3/.db files use SQLite
```

### Performance Comparison

| Backend | Single User | Multi User | Complex Queries | JSON Performance |
|---------|-------------|------------|-----------------|------------------|
| Limbo | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| SQLite | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| PostgreSQL | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| MySQL | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

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
python examples/demo.py
```

This demonstrates:
- Database initialization
- Table and column creation
- Data insertion and querying
- Schema evolution
- Export functionality

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

### Core Functions

- `make_db(db_path)` - Initialize database
- `create_table(name, db_path)` - Create new table
- `add_column(table, column, data_type, db_path)` - Add column
- `insert_typed_value(row_id, table_id, column_id, value, data_type, db_path)` - Insert value

### Query Functions

- `query_view(table, where_clause, db_path)` - Query table view
- `list_tables(db_path)` - List all tables
- `list_columns(table, db_path)` - List columns in table

### Utility Functions

- `export_table_structure(table, db_path)` - Export CREATE TABLE SQL
- `create_table_views(db_path)` - Regenerate all views

## CLI Commands

> **Note:** You can use `sdb` as a shorter alias for `synthdb` in all commands.

### Database Operations
- `sdb database init [--path <path>] [--backend <backend>] [connection options]` - Initialize database
- `sdb database info [--path <path>] [--backend <backend>] [connection options]` - Show database information

**Connection Options (for PostgreSQL/MySQL):**
- `--host <host>` - Database host (default: localhost)
- `--port <port>` - Database port (default: 5432/3306)
- `--database <name>` - Database name (default: synthdb)
- `--user <user>` - Database user (default: postgres/root)
- `--password <pass>` - Database password

### Table Operations
- `sdb table create <name> [--backend <backend>]` - Create table
- `sdb table list [<table>] [--backend <backend>]` - List tables or columns in specific table
- `sdb table show <name> [--backend <backend>]` - Show detailed table information
- `sdb table export <name> [--backend <backend>]` - Export table structure
- `sdb table add column <table> <column> <type> [--backend <backend>]` - Add column

### Data Operations
- `sdb insert <table> <row_id> <column> <value> <type> [--backend <backend>]` - Insert value
- `sdb query <table> [--where <clause>] [--backend <backend>]` - Query table data

All commands support:
- `--path <path>` to specify database file/connection string (defaults to `db.db`)
- `--backend <backend>` to specify backend (`limbo`, `sqlite`, `postgresql`, `mysql`)
- Network connection options for PostgreSQL and MySQL

**Connection Examples:**
```bash
# Local file
sdb query products --path myapp.db

# PostgreSQL connection string
sdb query products --path "postgresql://user:pass@localhost/myapp"

# MySQL with individual options
sdb query products --backend mysql --host localhost --database myapp --user root

# Environment variable
export SYNTHDB_CONNECTION="postgresql://user:pass@localhost/myapp"
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
- **PostgreSQL/MySQL**: Require server setup and configuration
- **Network backends**: Network latency affects performance
# SynthDB

A synthetic database system using the Entity-Attribute-Value (EAV) model. SynthDB provides schema-on-write capabilities with automatic view generation, making it easy to work with flexible, evolving data structures while maintaining familiar SQL-like interfaces.

## Features

- **EAV Architecture**: Store data in a flexible, type-specific Entity-Attribute-Value model
- **Automatic Views**: Automatically generated SQL views that present EAV data as traditional tables
- **Schema Evolution**: Add columns to existing tables without migration scripts
- **Type Safety**: Type-specific storage tables for optimal performance and data integrity
- **History Tracking**: Built-in audit trail with creation and update timestamps
- **CLI Interface**: Rich command-line interface for database operations
- **Python API**: Clean, well-documented Python API for programmatic access

## Installation

```bash
pip install synthdb
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
# Initialize a new database
synthdb database init
# or use the shorter alias:
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

# Initialize database
synthdb.make_db()

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

## Architecture

SynthDB uses an EAV (Entity-Attribute-Value) model with the following components:

### Core Tables

- **table_definitions**: Metadata about user-defined tables
- **column_definitions**: Metadata about columns in each table
- **{type}_values**: Type-specific value storage (text_values, integer_values, etc.)
- **{type}_value_history**: Audit trail for all value changes

### View Generation

SynthDB automatically creates SQL views for each table that:
- Present EAV data in familiar columnar format
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
│   ├── core.py       # Core EAV operations
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
- `sdb database init [--path <path>]` - Initialize database
- `sdb database info [--path <path>]` - Show database information

### Table Operations
- `sdb table create <name>` - Create table
- `sdb table list [<table>]` - List tables or columns in specific table
- `sdb table show <name>` - Show detailed table information
- `sdb table export <name>` - Export table structure
- `sdb table add column <table> <column> <type>` - Add column

### Data Operations
- `sdb insert <table> <row_id> <column> <value> <type>` - Insert value
- `sdb query <table> [--where <clause>]` - Query table data

All commands support `--path <path>` to specify database file (defaults to `db.db`).

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
- **Content management** - Handle varying entity structures
- **Data integration** - Normalize disparate data sources
- **Audit systems** - Built-in change tracking and history

## Performance Considerations

- Views are generated dynamically but cached by SQLite
- Type-specific tables optimize storage and indexing
- History tables provide audit capability with minimal overhead
- Consider partitioning strategies for very large datasets

## Limitations

- SQLite backend limits concurrent write performance
- View complexity increases with table width
- Not suitable for high-frequency transactional workloads
- Schema changes require view regeneration
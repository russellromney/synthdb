# SynthDB

A flexible database system with schema-on-write capabilities. SynthDB makes it easy to work with evolving data structures while maintaining familiar SQL-like interfaces.

## Features

- **Flexible Schema**: Store data with dynamic schemas that evolve as your application grows
- **Schema Evolution**: Add columns to existing tables without migration scripts
- **Type Safety**: Type-specific storage tables for optimal performance and data integrity
- **History Tracking**: Built-in audit trail with creation and update timestamps
- **CLI Interface**: Rich command-line interface for database operations
- **Python API**: Clean, well-documented Python API for programmatic access
- **REST API Server**: FastAPI-based server for remote database access
- **Type-Safe Models**: Pydantic-based models with relationship support
- **SQLite Backend**: Built on SQLite, the world's most widely deployed database engine
- **Local Project Management**: Built-in `.synthdb` directory for project-local databases
- **Branch Support**: Create and switch between database branches for development workflows
- **Safe SQL Execution**: Execute custom SELECT queries with built-in safety validation
- **SQL Keyword Protection**: Prevents table/column names that conflict with SQL keywords
- **Clean ID Interface**: Simple 'id' field for all row identifiers

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

**Optional Dependencies:**

```bash
# For API server functionality
uv add "synthdb[api]"

# For LibSQL remote database support
uv add libsql-experimental
```

**Backend:**
- **SQLite**: Default backend - Battle-tested, stable, and available everywhere
- **LibSQL**: Optional backend for remote database support (Turso, etc.)

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

### Project & Branch Management (New!)

SynthDB now includes built-in project and branch management, similar to Git but for your database:

```bash
# Initialize a SynthDB project in current directory
sdb project init

# Check project status
sdb project status

# Branch commands
sdb branch                    # List all branches
sdb branch list               # List all branches (explicit)
sdb branch current            # Show current branch
sdb branch create feature-x   # Create new branch
sdb branch switch main        # Switch to a branch
sdb branch delete old-branch  # Delete a branch

# Advanced branch operations
sdb branch create hotfix --from production  # Create from specific branch
sdb branch create test --no-switch         # Create without switching
sdb branch delete temp --force              # Delete without confirmation

# Merge structure changes between branches
sdb branch merge feature-x              # Merge feature-x into current branch
sdb branch merge feature-x --into main  # Merge feature-x into main
sdb branch merge feature-x --dry-run    # Preview changes without merging
```

#### How Branches Work

- Each branch has its own isolated database file in `.synthdb/databases/`
- Creating a branch copies the current database to the new branch
- Switching branches automatically points `synthdb.connect()` to the right database
- Changes in one branch don't affect other branches
- Perfect for testing features, migrations, or experiments

#### Structure Merging

SynthDB supports merging table structures between branches:

- **What gets merged**: New tables and new columns only
- **What doesn't merge**: Data, column type changes, column deletions
- **Type safety**: If a column exists in both branches with different types, it's reported but not merged
- **Dry run support**: Preview changes before applying them

Example workflow:
```bash
# Create feature branch and add new structure
sdb branch create feature-analytics
sdb branch switch feature-analytics
# ... add new analytics tables and columns ...

# Merge structure back to main
sdb branch switch main
sdb branch merge feature-analytics --dry-run  # Preview first
sdb branch merge feature-analytics             # Apply changes
```

### CLI Usage

```bash
# Initialize a standalone database (without project)
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

# In a project with .synthdb directory, connect automatically uses the active branch
db = synthdb.connect()  # Uses current branch's database

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
db.insert('products', {'name': 'Special Item'}, id="1000")

# Single column inserts
db.insert('products', 'name', 'Quick Add')

# Query data - super simple!
all_products = db.query('products')
expensive = db.query('products', 'price > 25')

# Results include unique ID for each row
for product in all_products:
    print(f"{product['name']}: ${product['price']} (ID: {product['id']})")

# Upsert (insert or update by ID)
db.upsert('products', {
    'name': 'Updated Widget',
    'sku': 'WIDGET-001',
    'price': 24.99
}, id=product_id)

# Execute custom SQL queries safely
results = db.execute_sql("""
    SELECT category, COUNT(*) as count, AVG(price) as avg_price
    FROM products
    GROUP BY category
""")

# Parameterized queries (SQL injection safe)
expensive_products = db.execute_sql(
    "SELECT * FROM products WHERE price > ? AND active = ?",
    [100.0, True]
)

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

# Connect to remote API server
from synthdb.api_client import connect_remote
api = connect_remote('http://localhost:8000', 'myapp.db')
```

### 🌐 **API Server & Remote Access**

SynthDB includes a FastAPI-based server for remote database access:

```bash
# Start API server
sdb api serve --host 0.0.0.0 --port 8000

# Test API connection
sdb api test http://localhost:8000
```

```python
from synthdb.api_client import connect_remote

# Connect to remote API server
with connect_remote('http://localhost:8000', 'myapp.db') as api:
    # Use exactly like local connection
    api.create_table('users')
    api.add_columns('users', {'name': 'text', 'email': 'text'})
    
    user_id = api.insert('users', {
        'name': 'Remote User',
        'email': 'remote@example.com'
    })
    
    users = api.query('users')
    print(f"Found {len(users)} users")
    
    # Execute saved queries remotely
    results = api.queries.execute_query('user_stats')
```

### 🏗️ **Type-Safe Models**

Generate Pydantic models from your database schema for type safety and validation:

```python
from synthdb.models import extend_connection_with_models, Relationship, add_relationship

# Extend connection with model functionality
db = synthdb.connect('app.db')
extend_connection_with_models(db)

# Generate models from existing tables
models = db.generate_models()
User = models['Users']  # Generates from 'users' table
Post = models['Posts']  # Generates from 'posts' table

# Use type-safe models
user = User(
    name="Alice Johnson",
    email="alice@example.com",
    age=28
)

# Save to database with validation
user_id = user.save()
print(f"Created user with ID: {user_id}")

# Query with models
all_users = User.find_all()
active_users = User.find_all("is_active = 1")
specific_user = User.find_by_id(user_id)

# Model validation (Pydantic)
try:
    invalid_user = User(name="Bob", age="not-a-number")
except ValidationError as e:
    print(f"Validation error: {e}")

# Define relationships between models
user_posts_rel = Relationship(
    related_model=Post,
    foreign_key='user_id',
    related_key='id',
    relationship_type='one_to_many'
)
add_relationship(User, 'posts', user_posts_rel)

# Use relationships
user = User.find_by_id(user_id)
posts = user.posts  # Automatically loads related posts
print(f"User has {len(posts)} posts")

# Generate model code files
sdb models generate --output models.py
```

#### Model CLI Commands

```bash
# Generate models for all tables
sdb models generate --output generated_models.py

# Test model generation
sdb models test
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
- Include id, created_at, and updated_at timestamps
- Handle type conversions (e.g., integer to text)
- Update automatically when schema changes


### Supported Data Types

- **text**: String values
- **integer**: Whole numbers
- **real**: Floating-point numbers
- **timestamp**: Date/time values

## Branch Management in Python

Working with branches programmatically:

```python
import synthdb
from synthdb.local_config import get_local_config, init_local_project

# Initialize a project (only needed once)
init_local_project()

# Get the local config manager
config = get_local_config()

# Check current branch
print(f"Current branch: {config.get_active_branch()}")

# Create a new branch
config.create_branch("feature-new-schema")

# Switch to the new branch
config.set_active_branch("feature-new-schema")

# Now synthdb.connect() automatically uses the feature branch
db = synthdb.connect()
db.create_table("experimental_features")
db.add_columns("experimental_features", {"name": "text", "enabled": "integer"})

# Switch back to main
config.set_active_branch("main")
db_main = synthdb.connect()  # This connects to main branch

# List all branches
branches = config.list_branches()
for name, info in branches.items():
    print(f"Branch: {name} - Database: {info['database']}")
```

### Real-World Branch Workflow

```python
# Development workflow example
config = get_local_config()

# 1. Create feature branch for new functionality
config.create_branch("feature-user-profiles", from_branch="main")
config.set_active_branch("feature-user-profiles")

# 2. Develop and test new schema
db = synthdb.connect()
db.create_table("user_profiles")
db.add_columns("user_profiles", {
    "user_id": "text",
    "bio": "text", 
    "avatar_url": "text",
    "preferences": "text"  # JSON stored as text
})

# 3. Test with sample data
db.insert("user_profiles", {
    "user_id": "user123",
    "bio": "Software developer passionate about databases",
    "avatar_url": "https://example.com/avatar.jpg",
    "preferences": '{"theme": "dark", "notifications": true}'
})

# 4. Create a staging branch for integration testing
config.create_branch("staging", from_branch="main")
config.set_active_branch("staging")

# 5. Merge structure changes back to main
config.set_active_branch("main")
results = config.merge_structure("feature-user-profiles", dry_run=True)
print(f"Would add tables: {results['new_tables']}")
print(f"Would add columns: {results['new_columns']}")

# 6. Apply the merge
if input("Apply changes? (y/n): ").lower() == 'y':
    results = config.merge_structure("feature-user-profiles")
    print("Structure merged successfully!")
```

## Examples

See the `examples/` directory for comprehensive usage examples:

```bash
# Modern connection API demo (recommended)
python examples/demo.py

# API server and type-safe models demo
python examples/api_and_models_demo.py

# Local project and branch management demo
python examples/local_project_demo.py

# Comprehensive branch workflow demo
python examples/branch_demo.py

# Branch structure merging demo
python examples/merge_demo.py
```

**Modern Demo** (`demo.py`) demonstrates:
- Clean connection-based interface (`synthdb.connect()`)
- Automatic database initialization
- Bulk column creation with type inference
- Auto-generated and explicit row IDs
- Simple querying and upsert operations
- Database inspection and error handling
- Different connection methods
- API benefits and best practices

**API & Models Demo** (`api_and_models_demo.py`) demonstrates:
- Starting and using the FastAPI server
- Type-safe Pydantic models with validation
- Model relationships and associations
- Remote API client usage
- Code generation for models
- Integration with saved queries

**SQL Execution Demo** (`sql_execution_demo.py`) demonstrates:
- Safe execution of custom SELECT queries
- Parameterized queries to prevent SQL injection
- Complex analytical queries with aggregations
- JOIN operations across tables
- Safety validations and restrictions
- Working with timestamps and SQL functions

**Local Project Demo** (`local_project_demo.py`) demonstrates:
- Initializing a `.synthdb` project directory
- Working with the local configuration
- Creating and switching between branches
- Branch isolation (changes don't affect other branches)
- Automatic database path resolution

**Branch Demo** (`branch_demo.py`) demonstrates:
- Complete branch management workflow
- Creating feature and hotfix branches
- Working with multiple branches simultaneously
- Branch-specific data modifications
- Comparing data across branches

**Merge Demo** (`merge_demo.py`) demonstrates:
- Creating branches with different schema changes
- Merging new tables and columns between branches
- Handling type conflicts safely
- Dry-run previews before merging
- Non-destructive merge operations

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
- `sdb sql <query> [--params <json>] [--format <format>]` - Execute safe SQL queries (SELECT only)

> 💡 **Tip**: Use shortcuts for faster development: `sdb db init`, `sdb t create users`, `sdb i users '{"name":"John"}'`, `sdb q users`

> 🔗 **Best Practice**: For complex operations, use the Connection class in Python: `db = synthdb.connect('app.db'); db.insert('users', {...})`

### API Commands
- `sdb api serve [--host <host>] [--port <port>] [--reload]` - Start API server
- `sdb api test <url>` - Test API server connection

### Model Commands
- `sdb models generate [--output <file>]` - Generate model code
- `sdb models test` - Test model generation

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

**SQL Query Examples:**
```bash
# Simple SELECT query
sdb sql "SELECT * FROM users WHERE age > 25"

# Query with parameters (safe from SQL injection)
sdb sql "SELECT * FROM users WHERE age > ? AND active = ?" --params "[25, true]"

# Aggregation queries
sdb sql "SELECT department, COUNT(*) as count, AVG(salary) as avg FROM users GROUP BY department"

# Output formats
sdb sql "SELECT * FROM products" --format json
sdb sql "SELECT * FROM products" --format csv --output products.csv

# Join queries
sdb sql "SELECT u.name, COUNT(o.id) as orders FROM users u LEFT JOIN orders o ON u.row_id = o.user_id GROUP BY u.row_id"
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
- **AI Agents** - Allow agents to safey make and test changes to database structure with zero downtime
- **Content management** - Handle varying content structures
- **Data integration** - Normalize disparate data sources
- **Audit systems** - Built-in change tracking and history
- **Microservices** - Each service can define its own schema dynamically

## Performance Considerations

- Views are generated dynamically but cached by SQLite
- Type-specific tables optimize storage and indexing
- History tables provide audit capability with minimal overhead
- Consider partitioning strategies for very large datasets

### Error Messages
When attempting to use protected names, SynthDB provides clear error messages:
```python
# Column name error
db.add_column('users', 'row_id', 'text')
# ValueError: Column name 'row_id' is protected and cannot be used. Protected column names: row_id
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
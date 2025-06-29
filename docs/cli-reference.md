# CLI Reference

SynthDB provides a comprehensive command-line interface for managing databases, tables, data, and more. The CLI uses a noun-first structure (e.g., `sdb table create` instead of `sdb create-table`) for better organization.

## Installation

The CLI is automatically available after installing SynthDB:

```bash
pip install synthdb
```

The CLI is available as both `synthdb` and `sdb` (shorter alias).

## Global Options

All commands support these global options:

- `--help`: Show help message and exit

## Command Structure

SynthDB CLI follows a hierarchical command structure:

```
sdb [NOUN] [VERB] [ARGUMENTS] [OPTIONS]
```

For example:
- `sdb table create users` - Create a table named "users"
- `sdb db init` - Initialize a new database
- `sdb query exec user_stats` - Execute a saved query

## Database Commands

### db init

Initialize a new SynthDB database.

```bash
sdb db init [OPTIONS]
```

**Options:**
- `--path, -p TEXT`: Database file path or connection string (default: "db.db")
- `--force, -f`: Overwrite existing database
- `--backend, -b TEXT`: Database backend - sqlite or libsql (default: "sqlite")

**Example:**
```bash
sdb db init --path myapp.db --backend libsql
```

### db info

Show database information including tables and statistics.

```bash
sdb db info [OPTIONS]
```

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend

**Example:**
```bash
sdb db info --path production.db
```

## Table Commands

### table create

Create a new table.

```bash
sdb table create NAME [OPTIONS]
```

**Arguments:**
- `NAME`: Table name

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend

**Example:**
```bash
sdb table create users
```

### table list

List all tables or columns in a specific table.

```bash
sdb table list [TABLE_NAME] [OPTIONS]
```

**Arguments:**
- `TABLE_NAME`: Optional - show columns for specific table

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--include-deleted, -d`: Include soft-deleted columns

**Examples:**
```bash
# List all tables
sdb table list

# List columns in users table
sdb table list users

# Include deleted columns
sdb table list users --include-deleted
```

### table show

Show detailed information about a specific table.

```bash
sdb table show NAME [OPTIONS]
```

**Arguments:**
- `NAME`: Table name

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend

**Example:**
```bash
sdb table show users
```

### table export

Export table structure as CREATE TABLE SQL.

```bash
sdb table export NAME [OPTIONS]
```

**Arguments:**
- `NAME`: Table name

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend

**Example:**
```bash
sdb table export users > users_schema.sql
```

### table copy

Copy a table's structure and optionally its data.

```bash
sdb table copy SOURCE TARGET [OPTIONS]
```

**Arguments:**
- `SOURCE`: Source table name
- `TARGET`: Target table name

**Options:**
- `--with-data`: Copy data along with structure
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend

**Examples:**
```bash
# Copy structure only
sdb table copy users users_backup

# Copy structure and data
sdb table copy users users_backup --with-data
```

### table add column

Add a column to an existing table.

```bash
sdb table add column TABLE NAME TYPE [OPTIONS]
```

**Arguments:**
- `TABLE`: Table name
- `NAME`: Column name
- `TYPE`: Data type (text, integer, real, timestamp)

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend

**Example:**
```bash
sdb table add column users email text
```

### table rename-column

Rename a column in a table.

```bash
sdb table rename-column TABLE OLD_NAME NEW_NAME [OPTIONS]
```

**Arguments:**
- `TABLE`: Table name
- `OLD_NAME`: Current column name
- `NEW_NAME`: New column name

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend

**Example:**
```bash
sdb table rename-column users username user_name
```

### table delete-column

Delete a column from a table.

```bash
sdb table delete-column TABLE COLUMN [OPTIONS]
```

**Arguments:**
- `TABLE`: Table name
- `COLUMN`: Column name to delete

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--hard`: Permanently delete all column data (cannot be recovered)
- `--yes, -y`: Skip confirmation prompt

**Examples:**
```bash
# Soft delete (data preserved)
sdb table delete-column users temp_field

# Hard delete (permanent)
sdb table delete-column users old_data --hard --yes
```

### table delete

Delete a table and all its data.

```bash
sdb table delete NAME [OPTIONS]
```

**Arguments:**
- `NAME`: Table name to delete

**Options:**
- `--hard`: Permanently delete all data (cannot be recovered)
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--yes, -y`: Skip confirmation prompt

**Examples:**
```bash
# Soft delete
sdb table delete temp_table

# Hard delete
sdb table delete old_table --hard --yes
```

## Data Commands

### insert

Insert a value into a specific table/row/column.

```bash
sdb insert TABLE ID COLUMN VALUE [TYPE] [OPTIONS]
```

**Arguments:**
- `TABLE`: Table name
- `ID`: Row ID
- `COLUMN`: Column name
- `VALUE`: Value to insert
- `TYPE`: Optional data type (text, integer, real, timestamp)

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--auto, -a`: Automatically infer data type
- `--backend, -b TEXT`: Database backend

**Examples:**
```bash
# Insert with explicit type
sdb insert users user123 name "John Doe" text

# Insert with type inference
sdb insert users user123 age 25 --auto

# Insert timestamp
sdb insert events evt001 created_at "2024-01-01 12:00:00" timestamp
```

### add

Add data using the modern API with auto-generated IDs and type inference.

```bash
sdb add TABLE DATA [OPTIONS]
```

**Arguments:**
- `TABLE`: Table name
- `DATA`: JSON data to insert

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--id`: Explicit row ID (auto-generated if not provided)

**Examples:**
```bash
# Auto-generated ID
sdb add users '{"name": "Jane Smith", "email": "jane@example.com", "age": 30}'

# Explicit ID
sdb add products '{"name": "Widget", "price": 19.99}' --id prod001
```

### query

Query data from a table.

```bash
sdb query TABLE [OPTIONS]
```

**Arguments:**
- `TABLE`: Table name to query

**Options:**
- `--where, -w TEXT`: WHERE clause
- `--format, -f TEXT`: Output format (table, json)
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend

**Examples:**
```bash
# Query all data
sdb query users

# Query with filter
sdb query users --where "age > 25"

# Output as JSON
sdb query products --format json --where "price < 50"
```

### sql

Execute a safe SQL query (SELECT only).

```bash
sdb sql QUERY [OPTIONS]
```

**Arguments:**
- `QUERY`: SQL query to execute

**Options:**
- `--params, -p TEXT`: Query parameters as JSON array
- `--format, -f TEXT`: Output format (table, json, csv)
- `--output, -o TEXT`: Output file path
- `--path TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend

**Examples:**
```bash
# Simple query
sdb sql "SELECT * FROM users WHERE age > 25"

# Query with parameters
sdb sql "SELECT * FROM users WHERE age > ?" --params "[25]"

# Export to CSV
sdb sql "SELECT name, email FROM users" --format csv --output users.csv

# Complex query
sdb sql "SELECT u.name, COUNT(p.id) as post_count FROM users u LEFT JOIN posts p ON u.id = p.user_id GROUP BY u.id"
```

## Import/Export Commands

### load-csv

Load data from CSV file into a table.

```bash
sdb load-csv FILE [OPTIONS]
```

**Arguments:**
- `FILE`: Path to CSV file

**Options:**
- `--table, -t TEXT`: Table name (defaults to filename)
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--create-table/--no-create-table`: Create table if it doesn't exist (default: true)
- `--delimiter, -d TEXT`: CSV delimiter (default: ",")

**Example:**
```bash
sdb load-csv users.csv --table users
```

### load-json

Load data from JSON file into a table.

```bash
sdb load-json FILE [OPTIONS]
```

**Arguments:**
- `FILE`: Path to JSON file

**Options:**
- `--table, -t TEXT`: Table name (defaults to filename)
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--create-table/--no-create-table`: Create table if it doesn't exist (default: true)
- `--key, -k TEXT`: JSON key containing array data

**Examples:**
```bash
# Load from array
sdb load-json data.json --table products

# Load from nested key
sdb load-json response.json --table users --key "data.users"
```

### export-csv

Export table data to CSV file.

```bash
sdb export-csv TABLE FILE [OPTIONS]
```

**Arguments:**
- `TABLE`: Table name to export
- `FILE`: Output CSV file path

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--where, -w TEXT`: WHERE clause for filtering
- `--delimiter, -d TEXT`: CSV delimiter (default: ",")

**Examples:**
```bash
# Export all data
sdb export-csv users users_export.csv

# Export filtered data
sdb export-csv orders orders_2024.csv --where "created_at >= '2024-01-01'"
```

### export-json

Export table data to JSON file.

```bash
sdb export-json TABLE FILE [OPTIONS]
```

**Arguments:**
- `TABLE`: Table name to export
- `FILE`: Output JSON file path

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--where, -w TEXT`: WHERE clause for filtering
- `--indent INT`: JSON indentation (default: 2)

**Example:**
```bash
sdb export-json products products.json --indent 4
```

## Configuration Commands

### config init

Create a sample configuration file.

```bash
sdb config init [OPTIONS]
```

**Options:**
- `--path, -p TEXT`: Config file path (default: ".synthdb.json")
- `--format, -f TEXT`: Config format - json, yaml, or toml (default: "json")
- `--force`: Overwrite existing config

**Example:**
```bash
sdb config init --format yaml --path .synthdb.yml
```

### config show

Show current configuration.

```bash
sdb config show [OPTIONS]
```

**Options:**
- `--config, -c TEXT`: Specific config file to show

**Example:**
```bash
sdb config show --config /etc/synthdb/config.json
```

### config connections

List available named connections.

```bash
sdb config connections
```

### config test

Test a database connection.

```bash
sdb config test [CONNECTION_NAME]
```

**Arguments:**
- `CONNECTION_NAME`: Connection name to test (tests default if not specified)

**Example:**
```bash
sdb config test production
```

## Project Commands

### project init

Initialize a new SynthDB project with .synthdb directory.

```bash
sdb project init [OPTIONS]
```

**Options:**
- `--directory, -d TEXT`: Directory to initialize project in (default: ".")
- `--force, -f`: Overwrite existing .synthdb directory

**Example:**
```bash
sdb project init --directory myproject
```

### project status

Show project status and active branch.

```bash
sdb project status
```

## Branch Commands

### branch list

List all branches in the project.

```bash
sdb branch list
```

### branch create

Create a new branch with a copy of the database.

```bash
sdb branch create NAME [OPTIONS]
```

**Arguments:**
- `NAME`: Name for the new branch

**Options:**
- `--from, -f TEXT`: Source branch to copy from (default: current branch)
- `--switch/--no-switch`: Switch to the new branch after creation (default: true)

**Examples:**
```bash
# Create from current branch
sdb branch create feature-x

# Create from specific branch without switching
sdb branch create hotfix --from main --no-switch
```

### branch switch

Switch to a different branch.

```bash
sdb branch switch NAME
```

**Arguments:**
- `NAME`: Branch name to switch to

**Example:**
```bash
sdb branch switch feature-x
```

### branch current

Show the current active branch.

```bash
sdb branch current
```

### branch delete

Delete a branch and its database.

```bash
sdb branch delete NAME [OPTIONS]
```

**Arguments:**
- `NAME`: Branch name to delete

**Options:**
- `--force, -f`: Force deletion without confirmation

**Example:**
```bash
sdb branch delete old-feature --force
```

### branch merge

Merge table structure changes from one branch to another.

```bash
sdb branch merge SOURCE [OPTIONS]
```

**Arguments:**
- `SOURCE`: Source branch to merge from

**Options:**
- `--into, -i TEXT`: Target branch to merge into (default: current branch)
- `--dry-run, -n`: Show what would be merged without making changes

**Examples:**
```bash
# Merge into current branch
sdb branch merge feature-x

# Merge into specific branch
sdb branch merge feature-x --into main

# Preview changes
sdb branch merge feature-x --dry-run
```

## Saved Query Commands

### query create

Create a new saved query.

```bash
sdb query create NAME [OPTIONS]
```

**Arguments:**
- `NAME`: Query name

**Options:**
- `--query, -q TEXT`: SQL query text
- `--file, -f PATH`: File containing SQL query
- `--description, -d TEXT`: Query description
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--connection, -c TEXT`: Named connection

**Examples:**
```bash
# Inline query
sdb query create user_stats --query "SELECT COUNT(*) as total, AVG(age) as avg_age FROM users"

# From file
sdb query create complex_report --file queries/monthly_report.sql --description "Monthly sales report"
```

### query list

List all saved queries.

```bash
sdb query list [OPTIONS]
```

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--connection, -c TEXT`: Named connection
- `--include-deleted`: Include soft-deleted queries

**Example:**
```bash
sdb query list --include-deleted
```

### query show

Show details of a specific saved query.

```bash
sdb query show NAME [OPTIONS]
```

**Arguments:**
- `NAME`: Query name

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--connection, -c TEXT`: Named connection

**Example:**
```bash
sdb query show user_stats
```

### query exec

Execute a saved query with parameters.

```bash
sdb query exec NAME [OPTIONS]
```

**Arguments:**
- `NAME`: Query name

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--connection, -c TEXT`: Named connection
- `--param TEXT`: Parameter as name=value (can be used multiple times)

**Examples:**
```bash
# Query without parameters
sdb query exec all_users

# Query with parameters
sdb query exec users_by_age --param min_age=25 --param max_age=35
```

### query delete

Delete a saved query.

```bash
sdb query delete NAME [OPTIONS]
```

**Arguments:**
- `NAME`: Query name

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--connection, -c TEXT`: Named connection
- `--hard`: Permanently delete (cannot be undone)

**Example:**
```bash
sdb query delete old_report --hard
```

## API Commands

### api serve

Start the SynthDB API server.

```bash
sdb api serve [OPTIONS]
```

**Options:**
- `--host, -h TEXT`: Host to bind to (default: "127.0.0.1")
- `--port, -p INT`: Port to bind to (default: 8000)
- `--reload, -r`: Enable auto-reload for development

**Examples:**
```bash
# Start server
sdb api serve

# Development mode with reload
sdb api serve --reload --host 0.0.0.0
```

### api test

Test connection to SynthDB API server.

```bash
sdb api test [OPTIONS]
```

**Options:**
- `--url, -u TEXT`: API server URL (default: "http://localhost:8000")
- `--database, -d TEXT`: Database name to test (default: "test.db")

**Example:**
```bash
sdb api test --url http://api.example.com:8080 --database production
```

## Model Commands

### models generate

Generate type-safe models from database schema.

```bash
sdb models generate OUTPUT [OPTIONS]
```

**Arguments:**
- `OUTPUT`: Output file path

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--connection, -c TEXT`: Named connection
- `--template, -t TEXT`: Model template - pydantic or dataclass (default: "pydantic")
- `--include-queries`: Include saved query models

**Examples:**
```bash
# Generate basic models
sdb models generate models.py

# Include saved queries
sdb models generate models.py --include-queries
```

### models test

Test type-safe models functionality.

```bash
sdb models test [OPTIONS]
```

**Options:**
- `--path, -p TEXT`: Database file path (default: "db.db")
- `--backend, -b TEXT`: Database backend
- `--connection, -c TEXT`: Named connection

**Example:**
```bash
sdb models test
```

## Common Workflows

### Creating and Populating a Database

```bash
# Initialize database
sdb db init --path myapp.db

# Create tables
sdb table create users
sdb table create posts

# Add columns
sdb table add column users name text
sdb table add column users email text
sdb table add column users age integer
sdb table add column posts title text
sdb table add column posts content text
sdb table add column posts user_id text

# Insert data
sdb add users '{"name": "John Doe", "email": "john@example.com", "age": 30}'
sdb add users '{"name": "Jane Smith", "email": "jane@example.com", "age": 25}'

# Query data
sdb query users --where "age > 25"
```

### Working with Branches

```bash
# Initialize project
sdb project init

# Create feature branch
sdb branch create new-feature

# Make changes
sdb table create experiments
sdb table add column experiments name text
sdb table add column experiments status text

# Switch back to main
sdb branch switch main

# Merge changes
sdb branch merge new-feature
```

### Using Saved Queries

```bash
# Create a parameterized query
sdb query create active_users --query "SELECT * FROM users WHERE status = ? AND created_at > ?" 

# Execute with parameters
sdb query exec active_users --param status=active --param created_at="2024-01-01"

# Export results
sdb query exec active_users --param status=active --param created_at="2024-01-01" | sdb export-csv - active_users.csv
```

## Configuration Files

SynthDB looks for configuration files in the following order:
1. `.synthdb.json` in the current directory
2. `.synthdb.yml` or `.synthdb.yaml` in the current directory
3. `.synthdb.toml` in the current directory
4. `.synthdb/config` in the current directory (for projects)
5. `$HOME/.config/synthdb/config.json`
6. `/etc/synthdb/config.json`

Example configuration:

```json
{
  "database": {
    "default_path": "data/main.db",
    "default_backend": "libsql"
  },
  "connections": {
    "production": {
      "backend": "libsql",
      "path": "/var/lib/synthdb/prod.db"
    },
    "test": {
      "backend": "sqlite",
      "path": "test.db"
    }
  }
}
```

## Tips and Best Practices

1. **Use Projects for Complex Applications**: Initialize a project with `sdb project init` to get branch support and better organization.

2. **Leverage Type Inference**: Use the `--auto` flag or the `add` command to let SynthDB infer data types automatically.

3. **Save Common Queries**: Use saved queries for frequently-used complex SQL to avoid rewriting them.

4. **Export Models**: Generate type-safe models with `sdb models generate` for better IDE support and type checking.

5. **Use Branches for Experiments**: Create branches to test schema changes without affecting your main database.

6. **Soft Delete by Default**: SynthDB soft-deletes by default, preserving data. Use `--hard` only when you're sure.

7. **Named Connections**: Define named connections in your config file for easy access to different databases.
# CLI Quick Start Guide

This guide will help you get started with the SynthDB command-line interface (CLI) quickly.

## Installation

```bash
pip install synthdb
```

The CLI is available as both `synthdb` and `sdb` (shorter alias).

## Basic Workflow

### 1. Create a Database

```bash
# Create a new database (default: db.db)
sdb db init

# Or specify a custom path
sdb db init --path myapp.db
```

### 2. Create Tables

```bash
# Create a users table
sdb table create users

# Create a posts table  
sdb table create posts
```

### 3. Add Columns

```bash
# Add columns to users table
sdb table add column users name text
sdb table add column users email text
sdb table add column users age integer

# Add columns to posts table
sdb table add column posts title text
sdb table add column posts content text
sdb table add column posts user_id text
sdb table add column posts created_at timestamp
```

### 4. Insert Data

```bash
# Insert data with auto-generated IDs
sdb add users '{"name": "Alice", "email": "alice@example.com", "age": 28}'
sdb add users '{"name": "Bob", "email": "bob@example.com", "age": 35}'

# Insert with specific ID
sdb add posts '{"title": "Hello World", "content": "My first post", "user_id": "123"}' --id post001
```

### 5. Query Data

```bash
# Query all users
sdb query users

# Query with conditions
sdb query users --where "age > 30"

# Use SQL for complex queries
sdb sql "SELECT u.name, COUNT(p.id) as posts FROM users u LEFT JOIN posts p ON u.id = p.user_id GROUP BY u.id"
```

## Common Tasks

### Working with CSV Files

```bash
# Import CSV data
sdb load-csv users.csv --table users

# Export to CSV
sdb export-csv users users_backup.csv
```

### Working with JSON

```bash
# Import JSON data
sdb load-json data.json --table products

# Export to JSON
sdb export-json products products.json
```

### Managing Tables

```bash
# List all tables
sdb table list

# Show table details
sdb table show users

# List columns in a table
sdb table list users

# Copy a table
sdb table copy users users_backup --with-data
```

### Using Projects and Branches

```bash
# Initialize a project
sdb project init

# Create a feature branch
sdb branch create new-feature

# Make changes on the branch
sdb table create experiments
sdb table add column experiments name text

# Switch back to main
sdb branch switch main

# Merge changes
sdb branch merge new-feature
```

### Saved Queries

```bash
# Save a frequently-used query
sdb query create active_users --query "SELECT * FROM users WHERE status = 'active'"

# Execute the saved query
sdb query exec active_users

# Save a parameterized query
sdb query create users_by_age --query "SELECT * FROM users WHERE age BETWEEN ? AND ?"

# Execute with parameters
sdb query exec users_by_age --param min=25 --param max=35
```

## Quick Reference

### Most Common Commands

| Command | Description |
|---------|-------------|
| `sdb db init` | Create a new database |
| `sdb table create NAME` | Create a table |
| `sdb table add column TABLE COL TYPE` | Add a column |
| `sdb add TABLE 'JSON'` | Insert data with auto ID |
| `sdb query TABLE` | Query table data |
| `sdb sql "SELECT..."` | Run SQL query |
| `sdb table list` | List all tables |

### Data Types

- `text` - String values
- `integer` - Whole numbers
- `real` - Decimal numbers
- `timestamp` - Date/time values

### Output Formats

Many commands support different output formats:

```bash
# Table format (default)
sdb query users

# JSON format
sdb query users --format json

# CSV format (for sql command)
sdb sql "SELECT * FROM users" --format csv
```

## Tips

1. **Use `--auto` for smart type inference**:
   ```bash
   sdb insert users user001 joined_at "2024-01-01" --auto
   ```

2. **Pipe commands together**:
   ```bash
   sdb sql "SELECT * FROM users WHERE active = true" | grep alice
   ```

3. **Use config files for connection settings**:
   ```bash
   sdb config init
   # Edit .synthdb.json
   sdb query users  # Uses config settings
   ```

4. **Check command help**:
   ```bash
   sdb table --help
   sdb table create --help
   ```

## Next Steps

- Read the [full CLI reference](../cli-reference.md) for all commands
- Learn about [SQL queries](sql-queries.md) in SynthDB
- Explore [Python API](../api/connection.md) for programmatic access
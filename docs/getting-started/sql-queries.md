# SQL Query Execution

SynthDB provides safe SQL query execution capabilities, allowing you to leverage the full power of SQL for data analysis while maintaining security and data integrity.

## Overview

The SQL execution feature allows you to:
- Execute complex SELECT queries with full SQL syntax
- Use parameterized queries to prevent SQL injection
- Access data through familiar SQL interfaces
- Export results in multiple formats (table, JSON, CSV)

## Safety Features

SynthDB enforces several safety mechanisms:

1. **SELECT-only queries**: Only read operations are allowed
2. **No DDL operations**: Cannot CREATE, ALTER, DROP tables
3. **No DML operations**: Cannot INSERT, UPDATE, DELETE data
4. **Internal table protection**: Cannot access SynthDB's internal tables
5. **SQL injection prevention**: Full support for parameterized queries

## Python API

### Basic Usage

```python
import synthdb

db = synthdb.connect('myapp.db')

# Simple query
results = db.execute_sql("SELECT * FROM users WHERE age > 25")

# Query with parameters (recommended for user input)
results = db.execute_sql(
    "SELECT * FROM users WHERE age > ? AND department = ?",
    [25, 'Engineering']
)

# Complex analytical query
analytics = db.execute_sql("""
    SELECT 
        department,
        COUNT(*) as employee_count,
        AVG(salary) as avg_salary,
        MAX(salary) as max_salary
    FROM users
    WHERE active = 1
    GROUP BY department
    ORDER BY avg_salary DESC
""")
```

### Working with Results

Query results are returned as a list of dictionaries:

```python
results = db.execute_sql("SELECT name, age FROM users LIMIT 3")
for row in results:
    print(f"{row['name']}: {row['age']} years old")

# Convert to pandas DataFrame
import pandas as pd
df = pd.DataFrame(results)
```

### Error Handling

```python
try:
    # This will fail - INSERT not allowed
    db.execute_sql("INSERT INTO users (name) VALUES ('Test')")
except ValueError as e:
    print(f"Query blocked: {e}")

try:
    # This will fail - internal table access
    db.execute_sql("SELECT * FROM table_definitions")
except ValueError as e:
    print(f"Access denied: {e}")
```

## CLI Usage

### Basic Queries

```bash
# Simple SELECT
sdb sql "SELECT * FROM users"

# With WHERE clause
sdb sql "SELECT * FROM users WHERE age > 25"

# Limit results
sdb sql "SELECT * FROM products LIMIT 10"
```

### Parameterized Queries

```bash
# Single parameter
sdb sql "SELECT * FROM users WHERE age > ?" --params "[25]"

# Multiple parameters
sdb sql "SELECT * FROM users WHERE age > ? AND department = ?" --params "[25, \"Sales\"]"

# With dates
sdb sql "SELECT * FROM orders WHERE created_at > ?" --params "[\"2024-01-01\"]"
```

### Output Formats

```bash
# Default table format
sdb sql "SELECT * FROM users"

# JSON output
sdb sql "SELECT * FROM users" --format json

# CSV output
sdb sql "SELECT * FROM users" --format csv

# Save to file
sdb sql "SELECT * FROM users" --format csv --output users.csv
sdb sql "SELECT * FROM users" --format json --output users.json
```

### Complex Queries

```bash
# Aggregations
sdb sql "SELECT department, COUNT(*) as count, AVG(salary) as avg_salary FROM users GROUP BY department"

# Joins
sdb sql "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.row_id = o.user_id GROUP BY u.row_id"

# Subqueries
sdb sql "SELECT * FROM users WHERE salary > (SELECT AVG(salary) FROM users)"

# Window functions (SQLite 3.25+)
sdb sql "SELECT name, salary, ROW_NUMBER() OVER (ORDER BY salary DESC) as rank FROM users"
```

## SQL Features Supported

### SELECT Clauses
- `SELECT` with column selection and aliases
- `DISTINCT` for unique results
- `*` for all columns

### FROM and JOIN
- Single table queries
- `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN`
- `CROSS JOIN` (use with caution)
- Table aliases

### WHERE Conditions
- Comparison operators: `=`, `!=`, `<>`, `<`, `>`, `<=`, `>=`
- `LIKE` for pattern matching
- `IN` and `NOT IN`
- `BETWEEN`
- `IS NULL` and `IS NOT NULL`
- `AND`, `OR`, `NOT` logical operators

### Grouping and Aggregation
- `GROUP BY` with multiple columns
- `HAVING` for group filtering
- Aggregate functions: `COUNT()`, `SUM()`, `AVG()`, `MIN()`, `MAX()`

### Ordering and Limiting
- `ORDER BY` with `ASC`/`DESC`
- `LIMIT` and `OFFSET` for pagination

### Advanced Features
- Subqueries in `WHERE` and `FROM` clauses
- `CASE WHEN` expressions
- `UNION`, `INTERSECT`, `EXCEPT`
- Common Table Expressions (CTEs) with `WITH`

## Working with SynthDB Features

### Accessing Row Metadata

```sql
-- Get all data with creation timestamps
SELECT *, created_at, updated_at FROM users

-- Find recently updated records
SELECT * FROM products WHERE updated_at > date('now', '-7 days')

-- Access row_id for joining
SELECT u.*, o.* 
FROM users u 
JOIN orders o ON u.row_id = o.user_id
```

### Type Handling

SynthDB automatically handles type conversions:

```sql
-- Numeric comparisons work across integer/real columns
SELECT * FROM products WHERE price > 100

-- Text comparisons
SELECT * FROM users WHERE name LIKE 'John%'

-- Boolean values (stored as integers)
SELECT * FROM users WHERE active = 1  -- or active = true in Python
```

## Security Best Practices

### Always Use Parameters

```python
# GOOD - Safe from SQL injection
user_input = "'; DROP TABLE users; --"
results = db.execute_sql(
    "SELECT * FROM users WHERE name = ?", 
    [user_input]
)

# BAD - Vulnerable to SQL injection
# results = db.execute_sql(f"SELECT * FROM users WHERE name = '{user_input}'")
```

### Validate User Input

```python
# Validate numeric inputs
def get_users_by_age(min_age):
    if not isinstance(min_age, (int, float)) or min_age < 0:
        raise ValueError("Invalid age parameter")
    
    return db.execute_sql(
        "SELECT * FROM users WHERE age >= ?",
        [min_age]
    )
```

## Performance Tips

1. **Use specific column names** instead of `SELECT *` when possible
2. **Add WHERE clauses** to limit result sets
3. **Use LIMIT** for large tables when testing queries
4. **Create appropriate indexes** (in regular SQL, outside SynthDB)
5. **Use EXPLAIN QUERY PLAN** to understand query performance

## Limitations

- **No write operations**: Cannot modify data through SQL
- **No schema changes**: Cannot create/alter/drop tables
- **No transactions**: Each query runs independently
- **No stored procedures**: Not supported
- **No direct index creation**: Use SynthDB API for optimization

## Examples

### Sales Analytics

```sql
-- Monthly sales summary
SELECT 
    strftime('%Y-%m', created_at) as month,
    COUNT(*) as order_count,
    SUM(total) as revenue,
    AVG(total) as avg_order_value
FROM orders
WHERE status = 'completed'
GROUP BY month
ORDER BY month DESC
```

### User Activity Report

```sql
-- Active users by department with order stats
SELECT 
    u.department,
    COUNT(DISTINCT u.row_id) as user_count,
    COUNT(o.row_id) as total_orders,
    COALESCE(SUM(o.total), 0) as total_spent
FROM users u
LEFT JOIN orders o ON u.row_id = o.user_id
WHERE u.active = 1
GROUP BY u.department
```

### Data Quality Check

```sql
-- Find potential duplicate entries
SELECT 
    name, 
    email, 
    COUNT(*) as duplicate_count
FROM users
GROUP BY name, email
HAVING COUNT(*) > 1
```

## See Also

- [Connection API Reference](../api/connection.md) - Complete API documentation
- [Query Builder](../api/query-builder.md) - Programmatic query construction
- [Examples](../examples/sql-queries.md) - More SQL query examples
# CLI Examples and Recipes

This page provides practical examples and recipes for common SynthDB CLI tasks.

## Database Management

### Creating a Database with Custom Settings

```bash
# Create with LibSQL backend
sdb db init --path analytics.db --backend libsql

# Force overwrite existing database
sdb db init --path test.db --force
```

### Database Information and Statistics

```bash
# Show database overview
sdb db info

# Show info for specific database
sdb db info --path production.db
```

## Table Operations

### Creating and Structuring Tables

```bash
# Create multiple related tables
sdb table create customers
sdb table create orders
sdb table create order_items

# Add columns with appropriate types
sdb table add column customers customer_id text
sdb table add column customers name text
sdb table add column customers email text
sdb table add column customers created_at timestamp

sdb table add column orders order_id text
sdb table add column orders customer_id text
sdb table add column orders total real
sdb table add column orders status text
sdb table add column orders created_at timestamp

sdb table add column order_items item_id text
sdb table add column order_items order_id text
sdb table add column order_items product_name text
sdb table add column order_items quantity integer
sdb table add column order_items price real
```

### Table Maintenance

```bash
# Create a backup of a table
sdb table copy customers customers_backup_$(date +%Y%m%d) --with-data

# Export table schema for documentation
sdb table export customers > schema/customers.sql
sdb table export orders > schema/orders.sql

# Clean up old columns (soft delete)
sdb table delete-column customers old_field

# Rename columns for consistency
sdb table rename-column customers customer_id id
sdb table rename-column orders customer_id customer_ref
```

## Data Import/Export

### CSV Import with Custom Settings

```bash
# Import CSV with semicolon delimiter
sdb load-csv european_data.csv --table sales --delimiter ";"

# Import without creating table (table must exist)
sdb load-csv updates.csv --table products --no-create-table
```

### JSON Import from API Response

```bash
# Download and import API data
curl https://api.example.com/products | \
  jq '.data' > products.json && \
  sdb load-json products.json --table products --key "items"
```

### Filtered Export

```bash
# Export active customers only
sdb export-csv customers active_customers.csv \
  --where "status = 'active' AND created_at >= '2024-01-01'"

# Export with custom delimiter for Excel
sdb export-csv orders orders.tsv --delimiter "\t"

# Export formatted JSON
sdb export-json products products_pretty.json --indent 4
```

## Complex Queries

### Analytics Queries

```bash
# Customer order statistics
sdb sql "
SELECT 
    c.name,
    COUNT(DISTINCT o.id) as order_count,
    SUM(o.total) as total_spent,
    AVG(o.total) as avg_order_value
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_ref
GROUP BY c.id
ORDER BY total_spent DESC
" --format table

# Monthly sales report
sdb sql "
SELECT 
    strftime('%Y-%m', created_at) as month,
    COUNT(*) as order_count,
    SUM(total) as revenue
FROM orders
WHERE created_at >= date('now', '-12 months')
GROUP BY month
ORDER BY month
" --output monthly_sales.csv --format csv
```

### Parameterized Queries

```bash
# Query with date parameters
sdb sql "
SELECT * FROM orders 
WHERE created_at BETWEEN ? AND ? 
AND status = ?
" --params '["2024-01-01", "2024-12-31", "completed"]'

# Customer search
sdb sql "
SELECT * FROM customers 
WHERE name LIKE ? OR email LIKE ?
" --params '["%john%", "%john%"]'
```

## Saved Queries

### Creating Reusable Reports

```bash
# Create monthly revenue query
cat > monthly_revenue.sql << 'EOF'
SELECT 
    strftime('%Y-%m', created_at) as month,
    COUNT(*) as orders,
    SUM(total) as revenue,
    AVG(total) as avg_order
FROM orders
WHERE created_at BETWEEN ? AND ?
GROUP BY month
ORDER BY month
EOF

sdb query create monthly_revenue \
  --file monthly_revenue.sql \
  --description "Monthly revenue report with date range parameters"

# Create customer lifetime value query
sdb query create customer_ltv --query "
SELECT 
    c.id,
    c.name,
    COUNT(o.id) as total_orders,
    COALESCE(SUM(o.total), 0) as lifetime_value,
    MAX(o.created_at) as last_order_date
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_ref
GROUP BY c.id
HAVING lifetime_value > ?
ORDER BY lifetime_value DESC
" --description "Customer lifetime value above threshold"
```

### Running Saved Queries

```bash
# Run monthly revenue for Q1 2024
sdb query exec monthly_revenue \
  --param start_date=2024-01-01 \
  --param end_date=2024-03-31

# Find high-value customers
sdb query exec customer_ltv --param threshold=1000
```

## Project and Branch Workflows

### Feature Development Workflow

```bash
# Initialize project
sdb project init
cd myproject

# Create feature branch
sdb branch create add-inventory

# Add new tables and columns
sdb table create inventory
sdb table add column inventory product_id text
sdb table add column inventory quantity integer
sdb table add column inventory location text
sdb table add column inventory last_updated timestamp

# Test with sample data
sdb add inventory '{"product_id": "PROD001", "quantity": 100, "location": "A1"}'

# Review changes
sdb table list
sdb query inventory

# Merge back to main
sdb branch switch main
sdb branch merge add-inventory --dry-run  # Preview first
sdb branch merge add-inventory
```

### A/B Testing Database Schemas

```bash
# Create branches for different schema designs
sdb branch create design-a
sdb branch create design-b

# Test design A
sdb branch switch design-a
sdb table create user_preferences
sdb table add column user_preferences user_id text
sdb table add column user_preferences preferences text  # JSON stored as text

# Test design B
sdb branch switch design-b
sdb table create user_settings
sdb table add column user_settings user_id text
sdb table add column user_settings setting_key text
sdb table add column user_settings setting_value text

# Compare and choose
sdb branch switch main
sdb branch merge design-a  # Choose design A
```

## API Server Operations

### Running API Server with Custom Config

```bash
# Create config file
cat > api_config.json << EOF
{
  "database": {
    "default_path": "/var/lib/synthdb/main.db",
    "default_backend": "libsql"
  },
  "connections": {
    "analytics": {
      "backend": "libsql",
      "path": "/var/lib/synthdb/analytics.db"
    }
  }
}
EOF

# Start server with config
SYNTHDB_CONFIG=api_config.json sdb api serve --host 0.0.0.0 --port 8080
```

### Testing API Endpoints

```bash
# Test local server
sdb api test

# Test remote server
sdb api test --url https://api.myapp.com --database production

# Use curl for custom tests
curl -X POST http://localhost:8000/api/v1/test.db/tables \
  -H "Content-Type: application/json" \
  -d '{"name": "test_table"}'
```

## Model Generation

### Generating and Using Models

```bash
# Generate models for all tables
sdb models generate models/generated.py

# Generate with saved queries
sdb models generate models/complete.py --include-queries

# Test generated models
python << 'EOF'
from models.generated import UsersBase, OrdersBase

# Models will be validated when connecting
import synthdb
db = synthdb.connect('db.db', models=True)

# Use models
user = UsersBase(name="Test User", email="test@example.com")
user.save()

# Query with models
users = UsersBase.find_all("age > 25")
EOF
```

## Performance and Maintenance

### Database Optimization

```bash
# Export large table data before cleanup
sdb export-csv logs logs_backup_$(date +%Y%m%d).csv \
  --where "created_at < date('now', '-30 days')"

# Create new optimized table
sdb table copy logs logs_new
sdb sql "INSERT INTO logs_new SELECT * FROM logs WHERE created_at >= date('now', '-30 days')"

# Verify and swap
sdb query logs_new | head
sdb table delete logs --hard --yes
sdb table rename logs_new logs
```

### Batch Operations

```bash
# Bulk insert from multiple CSV files
for file in data/*.csv; do
  table=$(basename "$file" .csv)
  echo "Loading $file into $table..."
  sdb load-csv "$file" --table "$table"
done

# Parallel export of all tables
sdb table list | grep -v "^ID" | awk '{print $2}' | \
  xargs -P 4 -I {} sh -c 'sdb export-json {} exports/{}.json'
```

## Scripting and Automation

### Backup Script

```bash
#!/bin/bash
# backup_synthdb.sh

DB_PATH="production.db"
BACKUP_DIR="backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Export schema
for table in $(sdb table list --path $DB_PATH | grep -v "^ID" | awk '{print $2}'); do
  sdb table export $table --path $DB_PATH > "$BACKUP_DIR/${table}_schema.sql"
  sdb export-json $table "$BACKUP_DIR/${table}_data.json" --path $DB_PATH
done

# Compress backup
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

echo "Backup completed: $BACKUP_DIR.tar.gz"
```

### Data Pipeline

```bash
#!/bin/bash
# etl_pipeline.sh

# Extract from API
curl -s https://api.source.com/data | jq '.records' > raw_data.json

# Transform and load
sdb load-json raw_data.json --table staging_data

# Process with SQL
sdb sql "
INSERT INTO processed_data
SELECT 
    id,
    UPPER(name) as name,
    CAST(amount as REAL) as amount,
    datetime('now') as processed_at
FROM staging_data
WHERE status = 'valid'
"

# Export results
sdb export-csv processed_data "output/processed_$(date +%Y%m%d).csv"

# Cleanup staging
sdb table delete staging_data --hard --yes
```

## Configuration Examples

### Multi-Environment Setup

```yaml
# .synthdb.yml
database:
  default_backend: libsql
  
connections:
  development:
    backend: sqlite
    path: dev.db
    
  staging:
    backend: libsql
    path: /data/staging.db
    
  production:
    backend: libsql
    path: /data/production.db
    
defaults:
  connection: development
```

### Using Named Connections

```bash
# Development work
sdb query users --connection development

# Staging validation
sdb db info --connection staging

# Production queries (read-only)
sdb sql "SELECT COUNT(*) FROM orders" --connection production
```
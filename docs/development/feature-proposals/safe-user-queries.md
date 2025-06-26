# Feature Proposal: Safe User Query Execution

<div class="status-badge status-proposed">Proposed</div>

**Authors**: SynthDB Development Team  
**Created**: 2024-06-26  
**Status**: Proposal  
**Complexity**: Medium  

## Summary

Add the ability for users to execute custom SQL queries on SynthDB databases with built-in safety mechanisms that prevent modification of database structure or access to internal tables. This would enable advanced users to leverage SQL for complex queries while maintaining data integrity and security.

## Motivation

### Use Cases

1. **Advanced Analytics**: Complex analytical queries that are difficult to express through the standard API
2. **Reporting**: Custom report generation with sophisticated aggregations and calculations
3. **Data Exploration**: Ad-hoc queries for data discovery and analysis
4. **Migration Support**: Easier transition for SQL-experienced users
5. **Performance Optimization**: Direct SQL for performance-critical queries
6. **Integration**: Support for SQL-based tools and libraries

### Current Limitations

- All queries must use the predefined API methods
- No way to execute custom analytical SQL
- Complex aggregations require multiple API calls and client-side processing
- Advanced SQL features (window functions, CTEs) are not accessible
- Difficult to integrate with SQL-based reporting tools

### Example Scenarios

```python
# Current approach - complex client-side aggregation
users = db.query('users')
orders = db.query('orders')

# Manual aggregation in Python
user_stats = {}
for user in users:
    user_orders = [o for o in orders if o['user_id'] == user['row_id']]
    user_stats[user['row_id']] = {
        'name': user['name'],
        'order_count': len(user_orders),
        'total_spent': sum(float(o['total']) for o in user_orders),
        'avg_order': sum(float(o['total']) for o in user_orders) / len(user_orders) if user_orders else 0
    }

# Desired approach - direct SQL execution
result = db.execute_query("""
    SELECT 
        u.name,
        COUNT(o.row_id) as order_count,
        SUM(o.total) as total_spent,
        AVG(o.total) as avg_order_value
    FROM users u
    LEFT JOIN orders o ON u.row_id = o.user_id
    GROUP BY u.row_id, u.name
    HAVING order_count > 0
    ORDER BY total_spent DESC
""")
```

## Detailed Design

### Core Concepts

#### Query Types
1. **Read-Only Queries**: SELECT statements only, no modifications
2. **View Queries**: Queries against automatically generated views
3. **Analytical Queries**: Complex aggregations, window functions, CTEs
4. **Restricted Queries**: Access only to user tables, not internal schema

#### Safety Mechanisms
1. **SQL Parsing**: Parse and validate SQL before execution
2. **Whitelist Operations**: Only allow safe SQL operations
3. **Table Access Control**: Restrict access to internal tables
4. **Query Transformation**: Automatically transform queries to work with SynthDB's views

### API Design

#### Basic Query Execution

```python
import synthdb

db = synthdb.connect('app.limbo')  # Uses Limbo by default

# Simple read-only query
result = db.execute_query("SELECT * FROM users WHERE age > 25")

# Complex analytical query
analytics = db.execute_query("""
    SELECT 
        category,
        COUNT(*) as product_count,
        AVG(price) as avg_price,
        MAX(price) as max_price,
        MIN(price) as min_price
    FROM products 
    GROUP BY category
    ORDER BY avg_price DESC
""")

# Query with parameters (safe from SQL injection)
filtered_results = db.execute_query(
    "SELECT * FROM orders WHERE status = ? AND total > ?",
    params=['completed', 100.0]
)
```

#### Query Validation and Safety

```python
# Query validation before execution
validation = db.validate_query("SELECT * FROM users")
if validation.is_safe:
    result = db.execute_query(validation.query)
else:
    print(f"Unsafe query: {validation.errors}")

# Safe query execution with automatic fixes
result = db.execute_safe_query("""
    -- This might reference internal tables
    SELECT * FROM text_values WHERE table_id = 1
""")
# Automatically transforms to:
# SELECT * FROM users  -- if table_id 1 corresponds to 'users'

# Dry run mode
plan = db.explain_query("SELECT COUNT(*) FROM orders")
print(f"Estimated rows: {plan.estimated_rows}")
print(f"Execution time: {plan.estimated_time}ms")
```

#### Advanced Features

```python
# Query builder with safety
query = (db.query_builder()
    .select('name', 'email', 'COUNT(orders.row_id) as order_count')
    .from_table('users')
    .left_join('orders', 'users.row_id = orders.user_id')
    .where('users.active = ?', [True])
    .group_by('users.row_id')
    .having('order_count > ?', [5])
    .order_by('order_count DESC')
    .limit(10))

result = query.execute()

# Query with custom functions
result = db.execute_query("""
    SELECT 
        name,
        email,
        DATE(created_at) as signup_date,
        JULIANDAY('now') - JULIANDAY(created_at) as days_since_signup
    FROM users
    WHERE signup_date > DATE('2024-01-01')
""")

# Window functions
result = db.execute_query("""
    SELECT 
        name,
        total,
        ROW_NUMBER() OVER (ORDER BY total DESC) as rank,
        PERCENT_RANK() OVER (ORDER BY total) as percentile
    FROM orders
""")
```

### Implementation Architecture

#### SQL Parser and Validator

```python
import sqlparse
from sqlparse.sql import Statement, TokenList
from sqlparse.tokens import Keyword, Name

class SQLValidator:
    ALLOWED_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 
        'ORDER BY', 'LIMIT', 'OFFSET', 'JOIN', 'LEFT JOIN',
        'RIGHT JOIN', 'INNER JOIN', 'OUTER JOIN', 'ON',
        'AS', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'CASE',
        'WHEN', 'THEN', 'ELSE', 'END', 'WITH'
    }
    
    FORBIDDEN_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE',
        'ALTER', 'TRUNCATE', 'GRANT', 'REVOKE', 'COMMIT',
        'ROLLBACK', 'SAVEPOINT', 'PRAGMA'
    }
    
    INTERNAL_TABLES = {
        'table_definitions', 'column_definitions', 'row_metadata',
        'text_values', 'integer_values', 'real_values', 'timestamp_values'
    }
    
    def validate_query(self, sql: str) -> ValidationResult:
        try:
            parsed = sqlparse.parse(sql)[0]
            return self._validate_statement(parsed)
        except Exception as e:
            return ValidationResult(False, [f"Parse error: {e}"])
    
    def _validate_statement(self, statement: Statement) -> ValidationResult:
        errors = []
        
        # Check for forbidden keywords
        for token in statement.flatten():
            if token.ttype is Keyword and token.value.upper() in self.FORBIDDEN_KEYWORDS:
                errors.append(f"Forbidden operation: {token.value}")
        
        # Check for internal table access
        table_names = self._extract_table_names(statement)
        for table in table_names:
            if table.lower() in self.INTERNAL_TABLES:
                errors.append(f"Access to internal table not allowed: {table}")
        
        # Validate SELECT-only queries
        if not self._is_select_query(statement):
            errors.append("Only SELECT queries are allowed")
        
        return ValidationResult(len(errors) == 0, errors)
```

#### Query Transformation

```python
class QueryTransformer:
    def __init__(self, connection):
        self.connection = connection
        self.user_tables = self._get_user_tables()
    
    def transform_query(self, sql: str) -> str:
        """Transform user SQL to work with SynthDB views."""
        parsed = sqlparse.parse(sql)[0]
        
        # Replace table references with view references
        transformed = self._replace_table_references(parsed)
        
        # Add row_id, created_at, updated_at columns if needed
        transformed = self._ensure_metadata_columns(transformed)
        
        return str(transformed)
    
    def _replace_table_references(self, statement):
        """Replace direct table references with SynthDB views."""
        # Implementation would traverse the AST and replace
        # table names with their corresponding view names
        pass
        
    def _get_user_tables(self):
        """Get list of user-created tables (excluding internal tables)."""
        return [t['name'] for t in self.connection.list_tables()]
```

#### Execution Engine

```python
class SafeQueryExecutor:
    def __init__(self, connection):
        self.connection = connection
        self.validator = SQLValidator()
        self.transformer = QueryTransformer(connection)
    
    def execute_query(self, sql: str, params: list = None) -> QueryResult:
        # Validate query safety
        validation = self.validator.validate_query(sql)
        if not validation.is_safe:
            raise UnsafeQueryError(validation.errors)
        
        # Transform query to work with SynthDB schema
        transformed_sql = self.transformer.transform_query(sql)
        
        # Execute with parameters
        try:
            cursor = self.connection.execute(transformed_sql, params or [])
            rows = cursor.fetchall()
            
            return QueryResult(
                rows=rows,
                columns=[desc[0] for desc in cursor.description],
                row_count=len(rows),
                execution_time_ms=self._get_execution_time(cursor)
            )
        except Exception as e:
            raise QueryExecutionError(f"Query failed: {e}")
    
    def explain_query(self, sql: str) -> QueryPlan:
        """Get execution plan without running the query."""
        validation = self.validator.validate_query(sql)
        if not validation.is_safe:
            raise UnsafeQueryError(validation.errors)
        
        transformed_sql = self.transformer.transform_query(sql)
        explain_sql = f"EXPLAIN QUERY PLAN {transformed_sql}"
        
        cursor = self.connection.execute(explain_sql)
        plan_rows = cursor.fetchall()
        
        return QueryPlan(plan_rows)
```

### Security Considerations

#### SQL Injection Prevention

```python
# Always use parameterized queries
def execute_safe_query(self, sql: str, params: dict = None):
    # Named parameter binding
    if params:
        # Validate parameter names to prevent injection
        safe_params = self._validate_parameters(params)
        return self.connection.execute(sql, safe_params)
    else:
        return self.connection.execute(sql)

def _validate_parameters(self, params: dict) -> dict:
    """Validate parameter names and values."""
    safe_params = {}
    for key, value in params.items():
        # Only allow alphanumeric parameter names
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
            raise ValueError(f"Invalid parameter name: {key}")
        safe_params[key] = value
    return safe_params
```

#### Access Control

```python
class TableAccessControl:
    def __init__(self, connection):
        self.connection = connection
        self.user_tables = set(self._get_user_tables())
        self.internal_tables = set(SQLValidator.INTERNAL_TABLES)
    
    def can_access_table(self, table_name: str) -> bool:
        """Check if user can access the specified table."""
        return table_name.lower() in self.user_tables
    
    def filter_accessible_tables(self, table_names: list) -> list:
        """Filter list to only include accessible tables."""
        return [t for t in table_names if self.can_access_table(t)]
```

### CLI Integration

```bash
# Execute custom queries
sdb query-sql "SELECT COUNT(*) FROM users WHERE active = true"

# Query with parameters
sdb query-sql "SELECT * FROM orders WHERE total > ?" --params 100.0

# Output formats
sdb query-sql "SELECT name, email FROM users" --format csv
sdb query-sql "SELECT * FROM products" --format json --output products.json

# Validate query without execution
sdb query-sql "SELECT * FROM users" --validate-only

# Explain query execution plan
sdb query-sql "SELECT * FROM orders GROUP BY status" --explain

# Interactive SQL shell
sdb sql-shell
# SynthDB SQL> SELECT COUNT(*) FROM users;
# SynthDB SQL> .tables
# SynthDB SQL> .schema users
# SynthDB SQL> .exit
```

### Implementation Plan

#### Phase 1: Basic SQL Execution (3-4 weeks)
- [ ] SQL parser and validator implementation
- [ ] Basic SELECT query support
- [ ] Table access control
- [ ] Parameter binding for safety
- [ ] Connection API integration

#### Phase 2: Query Transformation (2-3 weeks)
- [ ] Query transformer for SynthDB views
- [ ] Automatic table reference replacement
- [ ] Error handling and validation
- [ ] Basic testing and validation

#### Phase 3: Advanced Features (3-4 weeks)
- [ ] Complex SQL features (JOINs, subqueries, CTEs)
- [ ] Query explanation and planning
- [ ] Performance optimization
- [ ] CLI integration and SQL shell

#### Phase 4: Production Features (2-3 weeks)
- [ ] Comprehensive security testing
- [ ] Performance benchmarking
- [ ] Documentation and examples
- [ ] Integration with reporting tools

## API Examples

### Basic Usage

```python
import synthdb

# Setup
db = synthdb.connect('analytics.limbo')  # Uses Limbo by default

# Simple queries
user_count = db.execute_query("SELECT COUNT(*) as total FROM users")[0]['total']

# Analytical queries
top_customers = db.execute_query("""
    SELECT 
        u.name,
        u.email,
        COUNT(o.row_id) as order_count,
        SUM(o.total) as lifetime_value,
        AVG(o.total) as avg_order_value
    FROM users u
    JOIN orders o ON u.row_id = o.user_id
    WHERE o.status = 'completed'
    GROUP BY u.row_id
    ORDER BY lifetime_value DESC
    LIMIT 10
""")

for customer in top_customers:
    print(f"{customer['name']}: ${customer['lifetime_value']:.2f}")
```

### Advanced Analytics

```python
# Time series analysis
monthly_sales = db.execute_query("""
    SELECT 
        strftime('%Y-%m', created_at) as month,
        COUNT(*) as order_count,
        SUM(total) as revenue,
        AVG(total) as avg_order_value
    FROM orders
    WHERE status = 'completed'
    GROUP BY month
    ORDER BY month
""")

# Cohort analysis
cohort_data = db.execute_query("""
    WITH first_purchase AS (
        SELECT 
            user_id,
            MIN(DATE(created_at)) as first_purchase_date
        FROM orders
        GROUP BY user_id
    ),
    monthly_activity AS (
        SELECT 
            o.user_id,
            fp.first_purchase_date,
            strftime('%Y-%m', o.created_at) as activity_month,
            COUNT(*) as orders_in_month
        FROM orders o
        JOIN first_purchase fp ON o.user_id = fp.user_id
        WHERE o.status = 'completed'
        GROUP BY o.user_id, activity_month
    )
    SELECT 
        first_purchase_date,
        COUNT(DISTINCT user_id) as cohort_size,
        activity_month,
        COUNT(DISTINCT user_id) as active_users
    FROM monthly_activity
    GROUP BY first_purchase_date, activity_month
    ORDER BY first_purchase_date, activity_month
""")

# Product performance
product_stats = db.execute_query("""
    SELECT 
        p.name,
        p.category,
        COUNT(oi.row_id) as times_ordered,
        SUM(oi.quantity) as total_quantity,
        AVG(oi.price) as avg_price,
        SUM(oi.quantity * oi.price) as total_revenue
    FROM products p
    JOIN order_items oi ON p.row_id = oi.product_id
    JOIN orders o ON oi.order_id = o.row_id
    WHERE o.status = 'completed'
    GROUP BY p.row_id
    HAVING times_ordered >= 5
    ORDER BY total_revenue DESC
""")
```

## Performance Considerations

### Query Optimization
- **View Caching**: Cache generated views for better performance
- **Index Recommendations**: Suggest indexes for frequently queried columns
- **Query Planning**: Analyze and optimize complex queries
- **Result Caching**: Cache results of expensive analytical queries

### Resource Management
- **Query Timeouts**: Prevent long-running queries from blocking
- **Memory Limits**: Control memory usage for large result sets
- **Concurrent Access**: Handle multiple concurrent query executions

## Security Model

### Threat Prevention
1. **SQL Injection**: Parameterized queries and input validation
2. **Data Exfiltration**: Read-only access, no sensitive table exposure
3. **Resource Exhaustion**: Query timeouts and memory limits
4. **Privilege Escalation**: Strict table access control

### Audit Trail
```python
# Query execution logging
class QueryAuditor:
    def log_query_execution(self, sql: str, params: list, user: str, result_count: int):
        audit_entry = {
            'timestamp': datetime.utcnow(),
            'user': user,
            'query': sql,
            'parameters': params,
            'result_count': result_count,
            'execution_time_ms': execution_time
        }
        self.audit_log.append(audit_entry)
```

## Alternative Approaches

### 1. Query Templates
Provide predefined query templates for common analytical patterns.

**Pros**: Safe, optimized, easy to use
**Cons**: Limited flexibility, requires template maintenance

### 2. Restricted SQL Dialect
Create a custom SQL-like language with only safe operations.

**Pros**: Complete control over safety, optimized for SynthDB
**Cons**: Learning curve, limited SQL compatibility

### 3. View-Based Access
Only allow queries against predefined analytical views.

**Pros**: Simple implementation, good performance
**Cons**: Limited to predefined analyses, view management overhead

## Success Metrics

- **Safety**: Zero successful SQL injection or data breach attempts
- **Performance**: 95% of analytical queries complete within 5 seconds
- **Usability**: Users can express 90% of analytical needs through SQL
- **Adoption**: Feature used in >60% of SynthDB projects requiring analytics

## Future Enhancements

- **Query Optimization Engine**: Advanced query planning and optimization
- **Cached Analytics**: Automatic caching of expensive analytical queries
- **Real-time Analytics**: Streaming query support for real-time data
- **SQL Extensions**: Custom functions specific to SynthDB's domain
- **Integration APIs**: Direct integration with BI tools and data visualization

## Related Work

- **SQL Parsing**: sqlparse, SQLAlchemy expression language
- **Query Security**: PostgreSQL RLS, MySQL query rewriting
- **Analytics Databases**: ClickHouse analytical query patterns
- **Sandbox Execution**: Safe code execution patterns

## Conclusion

Adding safe user query execution to SynthDB would significantly enhance its analytical capabilities while maintaining security and data integrity. The proposed implementation balances flexibility with safety, enabling advanced SQL analytics while preventing harmful operations.

The security-first design ensures that users can leverage the full power of SQL for analytics without compromising the database or accessing sensitive internal structures. This feature would make SynthDB much more attractive for analytical workloads and data exploration use cases.
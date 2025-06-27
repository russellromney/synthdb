# Feature Proposal: Joined Table Queries

<div class="status-badge status-proposed">Proposed</div>

**Authors**: SynthDB Development Team  
**Created**: 2024-06-26  
**Status**: Proposal  
**Complexity**: Medium  

## Summary

Add support for joining multiple tables in SynthDB queries, enabling relational queries across the flexible schema-on-write architecture. This would allow users to perform complex analytical queries while maintaining SynthDB's dynamic schema benefits.

## Motivation

### Use Cases

1. **Relational Analysis**: Query related data across multiple tables
2. **Reporting**: Generate reports combining data from multiple entities
3. **Data Exploration**: Discover relationships between different data sets
4. **Migration from SQL**: Easier transition for users familiar with SQL joins
5. **Complex Filtering**: Filter one table based on conditions in related tables

### Current Limitations

- Queries are limited to single tables
- Related data must be manually fetched and combined in application code
- No way to leverage relationships between tables in queries
- Difficult to perform complex analytical operations

### Example Scenarios

```python
# Current approach (manual joining in code)
users = db.query('users', 'active = "true"')
orders = db.query('orders')
user_orders = []
for user in users:
    user_id = user['row_id']
    user_order_list = [o for o in orders if o['user_id'] == user_id]
    user_orders.append({'user': user, 'orders': user_order_list})

# Desired approach (joined queries)
user_orders = db.query_joined([
    ('users', 'u'),
    ('orders', 'o', 'u.row_id = o.user_id')
], 'u.active = "true"')
```

## Detailed Design

### Core Concepts

#### Join Types
1. **Inner Join**: Only rows with matches in both tables
2. **Left Join**: All rows from left table, with or without matches
3. **Right Join**: All rows from right table, with or without matches  
4. **Full Outer Join**: All rows from both tables
5. **Cross Join**: Cartesian product of both tables

#### Join Conditions
- **Explicit**: User-specified join conditions
- **Implicit**: Automatic detection based on common column names
- **Composite**: Multiple column joins

### API Design

#### Connection API Integration

```python
import synthdb

db = synthdb.connect('app.db')

# Simple join syntax
result = db.query_joined('users', 'orders', on='users.row_id = orders.user_id')

# Multiple table joins with aliases
result = db.query_joined([
    ('users', 'u'),
    ('orders', 'o', 'u.row_id = o.user_id'),
    ('products', 'p', 'o.product_id = p.row_id')
], where='u.active = "true" AND p.price > 100')

# Different join types
result = db.query_joined([
    ('users', 'u'),
    ('orders', 'o', 'u.row_id = o.user_id', 'LEFT')
])

# Aggregation with joins
result = db.query_joined([
    ('users', 'u'),
    ('orders', 'o', 'u.row_id = o.user_id')
], select='u.name, COUNT(o.row_id) as order_count', group_by='u.row_id')
```

#### Join Builder Pattern

```python
# Fluent interface for complex joins
query = (db.join_query()
    .from_table('users', 'u')
    .inner_join('orders', 'o', 'u.row_id = o.user_id')
    .left_join('profiles', 'p', 'u.row_id = p.user_id')
    .where('u.active = "true"')
    .select('u.name', 'u.email', 'COUNT(o.row_id) as order_count', 'p.bio')
    .group_by('u.row_id')
    .order_by('order_count DESC')
    .limit(10))

result = query.execute()
```

#### Relationship Definition

```python
# Define relationships for automatic joins
db.define_relationship('users', 'orders', 'row_id', 'user_id', name='user_orders')
db.define_relationship('orders', 'products', 'product_id', 'row_id', name='order_products')

# Use predefined relationships
result = db.query_with_relationships('users', include=['orders', 'orders.products'])
# Automatically joins based on defined relationships
```

### Implementation Architecture

#### Query Translation

SynthDB's EAV model requires special handling for joins:

```sql
-- Traditional SQL join
SELECT u.name, o.total 
FROM users u 
JOIN orders o ON u.id = o.user_id

-- SynthDB EAV translation
SELECT 
    u_name.value as user_name,
    o_total.value as order_total
FROM table_definitions td_users
JOIN text_values u_name ON td_users.id = u_name.table_id
JOIN column_definitions cd_u_name ON u_name.column_id = cd_u_name.id AND cd_u_name.name = 'name'
JOIN table_definitions td_orders
JOIN real_values o_total ON td_orders.id = o_total.table_id  
JOIN column_definitions cd_o_total ON o_total.column_id = cd_o_total.id AND cd_o_total.name = 'total'
WHERE td_users.name = 'users' 
  AND td_orders.name = 'orders'
  AND u_name.row_id = o_total.row_id  -- This is the actual join condition
```

#### Virtual View Generation

Create temporary views that present joined data in tabular format:

```python
class JoinQuery:
    def __init__(self, connection):
        self.connection = connection
        self.tables = []
        self.joins = []
        self.conditions = []
        
    def create_join_view(self):
        # Generate SQL for creating a temporary view
        # that represents the joined data
        view_sql = self._build_join_sql()
        view_name = f"temp_join_{uuid.uuid4().hex[:8]}"
        
        self.connection.execute(f"CREATE TEMP VIEW {view_name} AS {view_sql}")
        return view_name
        
    def execute(self):
        view_name = self.create_join_view()
        try:
            return self.connection.query_view(view_name)
        finally:
            self.connection.execute(f"DROP VIEW {view_name}")
```

#### Join Optimization

1. **Predicate Pushdown**: Move WHERE conditions closer to table scans
2. **Index Usage**: Leverage existing indexes on row_id columns
3. **View Caching**: Cache frequently used join patterns
4. **Statistics**: Collect statistics for join optimization

### Implementation Challenges

#### EAV Model Complexity

SynthDB's Entity-Attribute-Value model makes joins complex:

- **Multiple Value Tables**: Each data type has its own table
- **Dynamic Schema**: Column structure not known at query time
- **Row Reconstruction**: Need to aggregate values back into rows

**Solution**: Generate dynamic SQL that unions across value tables:

```python
def build_table_query(table_name, alias, columns=None):
    """Build a query that reconstructs a table from EAV format."""
    if columns is None:
        columns = self.list_columns(table_name)
    
    # Build CASE statements for each column
    select_clauses = []
    for column in columns:
        data_type = column['data_type']
        table_suffix = f"{data_type}_values"
        
        select_clauses.append(f"""
            MAX(CASE WHEN cd.name = '{column['name']}' 
                THEN {table_suffix}.value END) as {column['name']}
        """)
    
    return f"""
        SELECT 
            {alias}.row_id,
            {', '.join(select_clauses)}
        FROM table_definitions td
        JOIN ({' UNION ALL '.join([
            f"SELECT table_id, column_id, row_id, value FROM {dt}_values"
            for dt in ['text', 'integer', 'real', 'timestamp']
        ])}) vals ON td.id = vals.table_id
        JOIN column_definitions cd ON vals.column_id = cd.id
        WHERE td.name = '{table_name}'
        GROUP BY {alias}.row_id
    """
```

#### Performance Considerations

- **Large Tables**: Joins can be expensive with large datasets
- **Index Strategy**: Need appropriate indexes for join conditions
- **Memory Usage**: Temporary views may consume significant memory

**Mitigations**:
- Implement streaming joins for large datasets
- Add query planning and optimization
- Provide performance hints and warnings

### CLI Integration

```bash
# Simple join queries
sdb join users orders --on "users.row_id = orders.user_id"

# Complex joins with multiple tables
sdb join users,u orders,o products,p \
  --conditions "u.row_id = o.user_id AND o.product_id = p.row_id" \
  --where "u.active = true AND p.price > 100" \
  --select "u.name, p.name as product, o.quantity"

# Predefined relationship joins
sdb join users --include orders,products --limit 10

# Export joined results
sdb join users orders --on "users.row_id = orders.user_id" \
  --format csv --output user_orders.csv
```

## Implementation Plan

### Phase 1: Basic Joins (3-4 weeks)
- [ ] Inner join implementation
- [ ] Simple join conditions (single column)
- [ ] Basic query translation from EAV to relational
- [ ] Connection API integration
- [ ] Unit tests for core functionality

### Phase 2: Advanced Join Types (2-3 weeks)
- [ ] Left, right, and outer joins
- [ ] Multiple join conditions
- [ ] Join builder pattern API
- [ ] Performance optimization
- [ ] CLI integration

### Phase 3: Relationships and Optimization (3-4 weeks)
- [ ] Relationship definition system
- [ ] Automatic join detection
- [ ] Query optimization
- [ ] Caching for frequently used joins
- [ ] Advanced error handling and validation

### Phase 4: Advanced Features (2-3 weeks)
- [ ] Aggregation with joins
- [ ] Subqueries in join conditions
- [ ] Cross joins and complex patterns
- [ ] Performance monitoring and hints
- [ ] Documentation and examples

## API Examples

### Basic Usage

```python
# Setup test data
db = synthdb.connect('joined_queries_demo.db')

# Create tables
db.create_table('users')
db.add_columns('users', {'name': 'text', 'email': 'text', 'active': True})

db.create_table('orders')
db.add_columns('orders', {'user_id': 1, 'total': 99.99, 'status': 'text'})

db.create_table('products')
db.add_columns('products', {'name': 'text', 'price': 29.99, 'category': 'text'})

# Insert test data
user1 = db.insert('users', {'name': 'Alice', 'email': 'alice@test.com', 'active': True})
user2 = db.insert('users', {'name': 'Bob', 'email': 'bob@test.com', 'active': False})

order1 = db.insert('orders', {'user_id': user1, 'total': 150.00, 'status': 'completed'})
order2 = db.insert('orders', {'user_id': user1, 'total': 75.50, 'status': 'pending'})
order3 = db.insert('orders', {'user_id': user2, 'total': 200.00, 'status': 'completed'})

# Basic join query
active_user_orders = db.query_joined([
    ('users', 'u'),
    ('orders', 'o', 'u.row_id = o.user_id')
], where='u.active = "true"')

print(f"Active users with orders: {len(active_user_orders)}")
```

### Advanced Usage

```python
# Complex multi-table join with aggregation
user_stats = db.query_joined([
    ('users', 'u'),
    ('orders', 'o', 'u.row_id = o.user_id', 'LEFT')
], 
select='u.name, u.email, COUNT(o.row_id) as order_count, SUM(o.total) as total_spent',
group_by='u.row_id',
having='order_count > 0',
order_by='total_spent DESC')

# Relationship-based joins
db.define_relationship('users', 'orders', 'row_id', 'user_id')
db.define_relationship('orders', 'order_items', 'row_id', 'order_id')
db.define_relationship('order_items', 'products', 'product_id', 'row_id')

# Query with nested relationships
user_purchases = db.query_with_relationships('users', 
    include=['orders.order_items.products'],
    where='users.active = "true"')
```

## Performance Benchmarks

Target performance characteristics:
- **Small joins** (<1000 rows per table): <100ms
- **Medium joins** (<10,000 rows per table): <1 second  
- **Large joins** (<100,000 rows per table): <10 seconds
- **Memory usage**: <2x size of largest table involved

## Alternative Approaches

### 1. Materialized Join Tables
Pre-compute and store common joins as physical tables.

**Pros**: Fast query performance, simple implementation
**Cons**: Storage overhead, data consistency challenges

### 2. Graph Database Approach
Model relationships as graph edges instead of foreign keys.

**Pros**: Natural relationship handling, flexible queries
**Cons**: Major architecture change, learning curve

### 3. View-Based Joins
Create database views for common join patterns.

**Pros**: Leverage database optimization, familiar SQL
**Cons**: Limited to predefined patterns, view management overhead

## Success Metrics

- **Performance**: 90% of join queries complete within target benchmarks
- **Usability**: Users can express 80% of common join patterns with simple API
- **Correctness**: 99.9% accuracy compared to equivalent SQL joins
- **Adoption**: Feature used in >50% of SynthDB projects with multiple tables

## Future Enhancements

- **Join Hints**: User-provided optimization hints
- **Parallel Joins**: Multi-threaded join processing
- **Streaming Joins**: Process large datasets without loading entirely into memory
- **Smart Indexing**: Automatic index creation for frequent join patterns
- **Query Planning**: Cost-based optimization for complex joins

## Related Work

- **SQL Join Algorithms**: Hash joins, nested loop joins, sort-merge joins
- **NoSQL Join Patterns**: MongoDB aggregation pipeline, Elasticsearch parent-child
- **EAV Query Optimization**: Academic research on efficient EAV querying
- **Graph Databases**: Neo4j relationship traversal patterns

## Conclusion

Adding joined table queries to SynthDB would significantly enhance its analytical capabilities while maintaining its flexible schema benefits. The implementation requires careful handling of the EAV model but offers substantial value for complex data analysis use cases.

The proposed API balances simplicity for basic use cases with power for advanced scenarios. Starting with basic inner joins and expanding to advanced features allows for iterative development and user feedback integration.
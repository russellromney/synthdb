# SynthDB Saved Queries Feature Request

## Overview

This proposal introduces saved queries to SynthDB - reusable, named query definitions that can be accessed like views but with enhanced capabilities including parameterization, composition, and performance optimization. Saved queries would bridge the gap between simple table queries and complex analytical workloads while maintaining SynthDB's flexible schema design.

## Motivation

Currently, SynthDB generates SQL views dynamically for each table. While this provides basic querying capabilities, users often need to:

1. **Reuse complex queries** across applications without duplicating logic
2. **Create parameterized queries** that accept runtime inputs
3. **Compose queries** from other queries for modular design
4. **Optimize performance** for frequently-used complex queries
5. **Version control** query definitions alongside application code
6. **Abstract complexity** from API consumers

## Benefits

### 1. Query Reusability
- Define once, use everywhere
- Consistent business logic across applications
- Reduced code duplication

### 2. Performance Optimization
- Query plan caching for complex joins
- Optional materialization for expensive computations
- Incremental refresh strategies

### 3. Enhanced Developer Experience
- Named queries are self-documenting
- Type-safe query interfaces in SDKs
- Composable query building

### 4. Security & Access Control
- Hide complex implementation details
- Row-level security at the query level
- Audit trail for query usage

### 5. Version Control & Migration
- Track query changes in git
- Deploy query updates with applications
- Rollback capabilities

## Drawbacks & Challenges

### 1. Storage Overhead
- Query definitions must be stored
- Materialized queries consume space
- Version history accumulates

### 2. Maintenance Complexity
- Query dependencies must be tracked
- Schema changes may break queries
- Stale materialized data issues

### 3. Performance Considerations
- Query parsing overhead
- Cache invalidation complexity
- Memory usage for query plans

### 4. Implementation Complexity
- Parameter binding and validation
- Query composition engine
- Materialization strategies

### 5. Debugging Challenges
- Error messages may be less clear
- Performance issues harder to diagnose
- Circular dependencies possible

## Implementation Options

### Option 1: Database-Level Saved Queries (Recommended)

Store query definitions in SynthDB's metadata tables, similar to table and column definitions.

```sql
-- New metadata tables
CREATE TABLE query_definitions (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    query_text TEXT NOT NULL,
    parameters JSON,
    is_materialized BOOLEAN DEFAULT FALSE,
    refresh_strategy TEXT, -- 'manual', 'on_write', 'periodic'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE TABLE query_dependencies (
    query_id INTEGER,
    depends_on_table TEXT,
    depends_on_query TEXT,
    FOREIGN KEY (query_id) REFERENCES query_definitions(id)
);

CREATE TABLE query_parameters (
    id INTEGER PRIMARY KEY,
    query_id INTEGER,
    name TEXT NOT NULL,
    data_type TEXT NOT NULL,
    default_value TEXT,
    is_required BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (query_id) REFERENCES query_definitions(id)
);
```

**Pros:**
- Consistent with SynthDB's architecture
- Supports all backends (SQLite, LibSQL)
- Easy versioning and soft deletes
- Natural integration with existing tools

**Cons:**
- Requires schema migration
- More complex implementation
- Query parsing needed

### Option 2: Configuration File Based Queries

Store queries in external YAML/JSON files that are loaded at runtime.

```yaml
# queries/user_analytics.yaml
name: active_users_summary
description: Summary of active users by age group
parameters:
  - name: min_age
    type: integer
    default: 18
  - name: days_active
    type: integer
    default: 30
query: |
  SELECT 
    CASE 
      WHEN age < 25 THEN 'Under 25'
      WHEN age < 35 THEN '25-34'
      WHEN age < 45 THEN '35-44'
      ELSE '45+'
    END as age_group,
    COUNT(*) as user_count,
    AVG(total_purchases) as avg_purchases
  FROM users u
  JOIN (
    SELECT user_id, COUNT(*) as total_purchases
    FROM orders
    WHERE created_at > datetime('now', '-{days_active} days')
    GROUP BY user_id
  ) o ON u.id = o.user_id
  WHERE u.age >= {min_age}
  GROUP BY age_group
```

**Pros:**
- Easy version control
- No schema changes needed
- Familiar to developers
- Hot reloading possible

**Cons:**
- File system dependency
- Deployment complexity
- No built-in versioning
- Harder to manage at scale

### Option 3: Hybrid Approach

Combine database storage with file-based development workflow.

```python
# Development: Define queries in Python
from synthdb.queries import define_query

@define_query(
    name="user_activity",
    description="User activity over time",
    materialized=True,
    refresh="daily"
)
def user_activity_query(days_back: int = 30, min_events: int = 5):
    return f"""
    SELECT 
        u.id as user_id,
        u.email,
        COUNT(e.id) as event_count,
        MAX(e.created_at) as last_active
    FROM users u
    JOIN events e ON u.id = e.user_id
    WHERE e.created_at > datetime('now', '-{days_back} days')
    GROUP BY u.id, u.email
    HAVING COUNT(e.id) >= {min_events}
    """

# Deployment: Sync to database
synthdb queries sync
```

**Pros:**
- Best of both worlds
- Type-safe in development
- Flexible deployment
- Migration path clear

**Cons:**
- Most complex to implement
- Sync logic required
- Potential for drift

## Proposed API Design

### Python API

```python
from synthdb import connect

db = connect("app.db")

# Create a saved query
db.create_query(
    name="high_value_customers",
    query="""
        SELECT 
            c.id,
            c.name,
            c.email,
            SUM(o.total) as lifetime_value
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE o.status = 'completed'
        GROUP BY c.id, c.name, c.email
        HAVING SUM(o.total) > :min_value
    """,
    parameters={
        "min_value": {"type": "real", "default": 1000.0}
    }
)

# Use the saved query
results = db.query("high_value_customers", min_value=5000)

# Create a materialized query with auto-refresh
db.create_query(
    name="daily_revenue_summary",
    query="""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as order_count,
            SUM(total) as revenue
        FROM orders
        WHERE status = 'completed'
        GROUP BY DATE(created_at)
    """,
    materialized=True,
    refresh_strategy="on_write"  # Refresh when orders table changes
)

# Query composition
db.create_query(
    name="top_customers_by_month",
    query="""
        SELECT 
            strftime('%Y-%m', o.created_at) as month,
            hvc.*
        FROM high_value_customers(:min_value) hvc
        JOIN orders o ON hvc.id = o.customer_id
        WHERE o.created_at > :start_date
        ORDER BY month, hvc.lifetime_value DESC
    """,
    parameters={
        "min_value": {"type": "real", "default": 1000.0},
        "start_date": {"type": "timestamp", "required": True}
    }
)
```

### CLI Usage

```bash
# Create a query from file
synthdb query create --file queries/analytics.sql --name user_analytics

# List all queries
synthdb query list

# Execute a query
synthdb query exec high_value_customers --param min_value=5000

# Update a query
synthdb query update high_value_customers --file updated_query.sql

# Refresh materialized query
synthdb query refresh daily_revenue_summary

# Export query definition
synthdb query export high_value_customers > high_value_customers.sql

# Import queries from directory
synthdb query import ./queries/
```

### TypeScript SDK

```typescript
// Define typed query
interface HighValueCustomer {
  id: string;
  name: string;
  email: string;
  lifetime_value: number;
}

// Use saved query with type safety
const highValueCustomers = await db
  .query<HighValueCustomer>('high_value_customers')
  .params({ min_value: 5000 })
  .execute();

// Create query with builder
await db.createQuery('product_inventory')
  .select(['p.id', 'p.name', 'SUM(i.quantity) as total_stock'])
  .from('products p')
  .join('inventory i', 'p.id = i.product_id')
  .where('i.warehouse_id = :warehouse_id')
  .groupBy(['p.id', 'p.name'])
  .having('SUM(i.quantity) > 0')
  .parameters({
    warehouse_id: { type: 'text', required: true }
  })
  .save();
```

## Implementation Details

### Query Storage and Execution

```python
# synthdb/queries.py
class QueryManager:
    def create_query(self, name: str, query: str, 
                    parameters: Dict[str, Any] = None,
                    materialized: bool = False,
                    refresh_strategy: str = 'manual') -> Query:
        """Create a new saved query."""
        # Validate query syntax
        parsed = self._parse_query(query)
        
        # Extract dependencies
        dependencies = self._extract_dependencies(parsed)
        
        # Store in metadata
        query_id = self._store_query_definition(
            name, query, parameters, materialized, refresh_strategy
        )
        
        # Create materialized view if needed
        if materialized:
            self._create_materialized_view(query_id, query)
        
        return Query(query_id, name, self)
    
    def execute_query(self, name: str, **params) -> List[Dict]:
        """Execute a saved query with parameters."""
        query_def = self._get_query_definition(name)
        
        # Validate parameters
        self._validate_parameters(query_def, params)
        
        # Check if materialized and fresh
        if query_def.is_materialized and self._is_cache_fresh(query_def):
            return self._query_materialized_view(query_def)
        
        # Build final query with parameters
        final_query = self._bind_parameters(query_def.query_text, params)
        
        # Execute through normal SynthDB query mechanism
        return self.db.execute_sql(final_query)
```

### Dependency Tracking

```python
def _extract_dependencies(self, parsed_query) -> Dict[str, Set[str]]:
    """Extract table and query dependencies from parsed query."""
    dependencies = {
        'tables': set(),
        'queries': set()
    }
    
    # Walk the AST to find table references
    for node in parsed_query.walk():
        if node.type == 'table_reference':
            table_name = node.value
            
            # Check if it's a saved query reference
            if self._is_saved_query(table_name):
                dependencies['queries'].add(table_name)
            else:
                dependencies['tables'].add(table_name)
    
    return dependencies
```

### Materialization Strategies

```python
class MaterializationStrategy:
    """Base class for query materialization strategies."""
    
    def should_refresh(self, query_def: QueryDefinition) -> bool:
        """Determine if materialized view needs refresh."""
        raise NotImplementedError
    
    def refresh(self, query_def: QueryDefinition):
        """Refresh the materialized view."""
        raise NotImplementedError

class OnWriteStrategy(MaterializationStrategy):
    """Refresh when dependent tables are modified."""
    
    def setup_triggers(self, query_def: QueryDefinition):
        """Create triggers on dependent tables."""
        for table in query_def.dependencies['tables']:
            trigger_sql = f"""
            CREATE TRIGGER refresh_{query_def.name}_on_{table}
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            BEGIN
                UPDATE query_definitions 
                SET needs_refresh = 1 
                WHERE id = {query_def.id};
            END;
            """
            self.db.execute(trigger_sql)

class PeriodicStrategy(MaterializationStrategy):
    """Refresh on a schedule."""
    
    def should_refresh(self, query_def: QueryDefinition) -> bool:
        last_refresh = query_def.last_refresh_at
        refresh_interval = query_def.refresh_interval
        return datetime.now() - last_refresh > refresh_interval
```

## Migration Path

### Phase 1: Core Infrastructure
1. Add metadata tables for query definitions
2. Implement basic query storage and retrieval
3. Add parameter binding support

### Phase 2: Query Execution
1. Build query parser and validator
2. Implement parameter validation
3. Add dependency tracking

### Phase 3: Materialization
1. Create materialized view support
2. Implement refresh strategies
3. Add incremental refresh capabilities

### Phase 4: Advanced Features
1. Query composition support
2. Version history tracking
3. Performance optimization

### Phase 5: Tooling
1. CLI commands for query management
2. SDK support for all languages
3. IDE integration for query authoring

## Example Use Cases

### 1. Business Intelligence Dashboard

```python
# Define reusable metrics
db.create_query("monthly_revenue", """
    SELECT 
        strftime('%Y-%m', created_at) as month,
        SUM(total) as revenue,
        COUNT(*) as order_count,
        AVG(total) as avg_order_value
    FROM orders
    WHERE status = 'completed'
        AND created_at >= :start_date
        AND created_at < :end_date
    GROUP BY month
""", parameters={
    "start_date": {"type": "timestamp", "required": True},
    "end_date": {"type": "timestamp", "required": True}
}, materialized=True)

# Use in application
revenue_data = db.query("monthly_revenue", 
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

### 2. Multi-Tenant SaaS Application

```python
# Saved query with row-level security
db.create_query("tenant_users", """
    SELECT u.*
    FROM users u
    JOIN tenants t ON u.tenant_id = t.id
    WHERE t.id = :tenant_id
        AND u.status = 'active'
        AND (:role IS NULL OR u.role = :role)
    ORDER BY u.created_at DESC
""", parameters={
    "tenant_id": {"type": "text", "required": True},
    "role": {"type": "text", "required": False}
})

# SDK automatically injects tenant_id
users = await db.query('tenant_users', { role: 'admin' });
```

### 3. Complex Analytics Pipeline

```python
# Base queries
db.create_query("user_cohorts", """
    SELECT 
        id as user_id,
        DATE(created_at, 'start of month') as cohort_month
    FROM users
""")

db.create_query("cohort_retention", """
    SELECT 
        c.cohort_month,
        COUNT(DISTINCT c.user_id) as cohort_size,
        COUNT(DISTINCT e.user_id) as active_users,
        ROUND(100.0 * COUNT(DISTINCT e.user_id) / COUNT(DISTINCT c.user_id), 2) as retention_rate
    FROM user_cohorts() c
    LEFT JOIN events e ON c.user_id = e.user_id
        AND e.created_at >= :analysis_date
        AND e.created_at < date(:analysis_date, '+1 month')
    GROUP BY c.cohort_month
    ORDER BY c.cohort_month
""", parameters={
    "analysis_date": {"type": "timestamp", "required": True}
})
```

## Performance Considerations

1. **Query Plan Caching**: Cache parsed and optimized query plans
2. **Lazy Materialization**: Only materialize when access patterns justify it
3. **Incremental Updates**: Use CDC for incremental materialized view updates
4. **Partition Pruning**: Automatically detect and use time-based partitions
5. **Cost-Based Optimization**: Track query execution stats for optimization

## Security Considerations

1. **Query Injection**: Parameterized queries prevent SQL injection
2. **Access Control**: Queries respect table-level permissions
3. **Audit Logging**: Track who executes which queries when
4. **Resource Limits**: Prevent runaway queries with timeouts and limits
5. **Data Masking**: Support column-level masking in query results

## Future Enhancements

1. **Query Versioning**: Track query definition changes over time
2. **A/B Testing**: Compare query performance across versions
3. **Smart Caching**: ML-based cache invalidation strategies
4. **Query Recommendations**: Suggest optimizations based on usage
5. **Federated Queries**: Query across multiple SynthDB instances
6. **Streaming Queries**: Real-time query results via WebSockets
7. **Query Marketplace**: Share queries across organizations
8. **Visual Query Builder**: GUI for creating complex queries
9. **Query Profiling**: Detailed performance analysis tools
10. **Cross-Database Queries**: Join data across different databases

## Conclusion

Saved queries would significantly enhance SynthDB's capabilities by providing a reusable, performant, and maintainable way to define complex data access patterns. The recommended database-level implementation aligns with SynthDB's architecture while providing flexibility for future enhancements. This feature would position SynthDB as a powerful solution for both simple CRUD operations and complex analytical workloads.
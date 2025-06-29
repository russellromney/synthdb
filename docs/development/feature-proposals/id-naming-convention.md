# Feature Proposal: ID Naming Convention - row_id vs id

<div class="status-badge status-discussion">Discussion</div>

**Authors**: SynthDB Development Team  
**Created**: 2025-01-02  
**Status**: Discussion  
**Complexity**: Medium  
**Breaking Change**: Potentially Yes

## Summary

Evaluate whether SynthDB should continue using `row_id` as the primary identifier name, switch to `id`, or implement aliasing to show `id` to users while maintaining `row_id` internally. This decision impacts API design, user experience, and Python compatibility.

## Current State

SynthDB currently uses `row_id` as the primary identifier for all records:

```python
# Current usage
user_id = db.insert('users', {'name': 'Alice'})
users = db.query('users', f'row_id = "{user_id}"')
print(users[0]['row_id'])  # The identifier
```

## The Problem

1. **Unconventional**: Most databases and ORMs use `id` as the primary key name
2. **Verbose**: `row_id` is longer and less intuitive than `id`
3. **Learning Curve**: New users expect `id` based on convention
4. **Integration**: Third-party tools often expect an `id` field

However, `id` conflicts with Python's built-in `id()` function:

```python
# Python built-in
id(object)  # Returns object's memory address

# Potential conflict
user.id  # Attribute access - OK
id = user.id  # Variable assignment - Shadows built-in!
```

## Proposed Solutions

### Option 1: Keep row_id (Current Approach)

**Implementation**: No changes needed

```python
# Continue as-is
result = db.query('users')[0]
print(result['row_id'])  # Clear, no conflicts
```

**Pros:**
- ✅ No Python built-in conflicts
- ✅ Explicitly descriptive - it's the row's ID
- ✅ No breaking changes
- ✅ Consistent with internal naming (row_metadata table)
- ✅ Less ambiguous in complex queries with multiple IDs

**Cons:**
- ❌ Unconventional compared to industry standards
- ❌ More verbose
- ❌ Surprises new users
- ❌ Requires documentation/explanation

### Option 2: Switch Everything to id

**Implementation**: Major breaking change

```python
# Change internal schema
CREATE TABLE row_metadata (
    id TEXT PRIMARY KEY,  -- Changed from row_id
    ...
)

# Update all code
result = db.query('users')[0]
print(result['id'])  # Standard convention
```

**Pros:**
- ✅ Industry standard convention
- ✅ Shorter and cleaner
- ✅ Intuitive for new users
- ✅ Better third-party integration

**Cons:**
- ❌ **Major breaking change** for all existing code
- ❌ Python built-in shadowing issues
- ❌ Migration complexity for existing databases
- ❌ Ambiguity in code (which `id`?)

### Option 3: Alias row_id to id in Results

**Implementation**: Transparent aliasing

```python
class Connection:
    def query(self, table: str, where_clause: str = None, 
              use_id_alias: bool = True) -> List[Dict]:
        results = self._query_internal(table, where_clause)
        
        if use_id_alias:
            # Rename row_id to id in results
            for row in results:
                if 'row_id' in row:
                    row['id'] = row.pop('row_id')
        
        return results
```

**Usage:**
```python
# Default behavior - shows as 'id'
user = db.query('users')[0]
print(user['id'])  # Aliased from row_id

# Can still use row_id in WHERE clauses
users = db.query('users', 'row_id = "123"')  # Works
users = db.query('users', 'id = "123"')      # Also works

# Opt-out of aliasing if needed
user = db.query('users', use_id_alias=False)[0]
print(user['row_id'])  # Original name
```

**Pros:**
- ✅ User-friendly convention
- ✅ Backward compatible with option
- ✅ Gradual migration path
- ✅ Best of both worlds

**Cons:**
- ❌ Inconsistency between input and output
- ❌ Complexity in implementation
- ❌ Potential confusion about which name to use where
- ❌ WHERE clause ambiguity

### Option 4: Smart Context-Aware Naming

**Implementation**: Use appropriate name based on context

```python
# In dictionaries/JSON: use 'id'
result = db.query('users')[0]
print(result['id'])  # No conflict with built-in

# In Python objects: use 'row_id' 
@dataclass
class User:
    row_id: str  # Avoids attribute conflict
    name: str
    
    @property
    def id(self) -> str:
        """Alias for row_id"""
        return self.row_id

# In SQL: accept both
db.execute_sql("SELECT * FROM users WHERE id = ?", ["123"])
db.execute_sql("SELECT * FROM users WHERE row_id = ?", ["123"])
```

**Pros:**
- ✅ Natural in each context
- ✅ Avoids Python conflicts in classes
- ✅ Flexible for users

**Cons:**
- ❌ Inconsistent API
- ❌ More complex to document
- ❌ Cognitive overhead

## Analysis of Python Built-in Conflict

The concern about shadowing Python's `id()` built-in is valid but may be overstated:

### Real-world Impact

```python
# This is fine - no conflict
user = {'id': '123', 'name': 'Alice'}
print(user['id'])  # Dictionary key access

# This is fine - no conflict  
class User:
    def __init__(self, id, name):
        self.id = id  # Instance attribute
        self.name = name

# This IS problematic
id = user['id']  # Shadows built-in
print(id(some_object))  # Error! id is now a string

# But this is common practice in many ORMs
from sqlalchemy import Column, String
class User(Base):
    id = Column(String, primary_key=True)  # SQLAlchemy does this
```

### Industry Precedent

Major Python ORMs and databases use `id` despite the conflict:

1. **Django**: `id` field by default
2. **SQLAlchemy**: Commonly uses `id`
3. **Peewee**: Uses `id` 
4. **MongoDB**: Uses `_id`
5. **PostgreSQL/MySQL**: Convention is `id`

The Python community has generally accepted this trade-off.

## Migration Strategies

### If Moving to 'id' (Option 2)

```python
# Migration script
def migrate_to_id():
    # 1. Add compatibility layer
    db.execute("ALTER VIEW user_view ADD COLUMN id AS (row_id)")
    
    # 2. Update application code gradually
    # 3. Eventually rename column
    
# Provide compatibility period
class Connection:
    def __init__(self, use_legacy_row_id=False):
        self.use_legacy_row_id = use_legacy_row_id
```

### If Implementing Aliasing (Option 3)

```python
# Gradual rollout
class Connection:
    def __init__(self, id_alias_version='v1'):
        self.id_alias_version = id_alias_version
    
    def query(self, table, where=None):
        if self.id_alias_version == 'v2':
            # New behavior with aliasing
        else:
            # Current behavior
```

## Recommendation

After analyzing all options, I recommend **Option 3 (Aliasing) with a twist**:

1. **Keep `row_id` internally** for all schema and storage
2. **Show as `id` in query results** by default
3. **Accept both in WHERE clauses** for compatibility
4. **Use `row_id` in generated Python classes** to avoid conflicts
5. **Document the convention clearly**

This approach because:
- Maintains backward compatibility
- Provides familiar interface for new users
- Avoids Python namespace issues in critical contexts
- Allows gradual migration if needed

### Proposed Implementation

```python
class Connection:
    def __init__(self, config=None):
        self.config = config or {}
        # Default to user-friendly names
        self.use_id_alias = self.config.get('use_id_alias', True)
    
    def query(self, table: str, where: Optional[str] = None) -> List[Dict]:
        # Accept both in WHERE clause
        if where and self.use_id_alias:
            where = where.replace(' id ', ' row_id ')
            where = where.replace('(id ', '(row_id ')
            where = where.replace(' id=', ' row_id=')
        
        results = self._execute_query(table, where)
        
        # Alias in output
        if self.use_id_alias:
            for row in results:
                row['id'] = row.pop('row_id', None)
        
        return results
    
    def insert(self, table: str, data: Dict) -> str:
        # Always return the ID value, not the key name
        return self._insert_internal(table, data)
```

### Documentation Approach

```markdown
## Primary Keys in SynthDB

SynthDB uses `row_id` internally but presents it as `id` in query results
for familiarity:

- Query results show `id`: `user['id']`
- WHERE clauses accept both: `WHERE id = ?` or `WHERE row_id = ?`
- Python classes use `row_id` to avoid conflicts: `user.row_id`
- Insert/upsert return the ID value directly: `user_id = db.insert(...)`

This design balances Python best practices with database conventions.
```

## Alternative: Configurable Naming

Allow users to choose their preference:

```python
# Global configuration
synthdb.configure(primary_key_name='id')  # or 'row_id' or '_id'

# Per-connection configuration
db = synthdb.connect('app.db', primary_key_name='id')

# Per-query configuration
db.query('users', primary_key_name='_id')  # MongoDB style
```

## Conclusion

The `row_id` vs `id` debate represents a classic trade-off between:
- Following conventions vs avoiding language conflicts
- User familiarity vs technical correctness
- Breaking changes vs inconsistency

The aliasing approach (Option 3) offers the best balance, providing a familiar interface while maintaining technical soundness. It allows SynthDB to present a conventional face to users while avoiding the real issues that come from conflicting with Python built-ins in critical contexts.

The key insight is that different contexts (SQL queries, Python dictionaries, Python classes) have different constraints, and we can optimize for each context appropriately.
# Feature Proposal: Type-Safe Database Models

<div class="status-badge status-proposed">Proposed</div>

**Authors**: SynthDB Development Team  
**Created**: 2025-01-02  
**Status**: Proposal  
**Complexity**: High  

## Summary

Add the ability to dynamically generate Python classes from SynthDB table structures, providing type-safe query results with full IDE support including autocomplete, type checking, and better developer experience. This would bridge the gap between SynthDB's flexible schema and Python's static typing system.

## Motivation

### Current Limitations

1. **No Type Safety**: Query results are plain dictionaries with no type information
2. **No IDE Support**: No autocomplete for column names or types
3. **Runtime Errors**: Typos in column names only caught at runtime
4. **Manual Type Casting**: Developers must manually handle type conversions
5. **No Validation**: No automatic validation of data types

### Example Pain Points

```python
# Current approach - no type safety
users = db.query('users')
for user in users:
    # No autocomplete, potential typos
    print(user['fisrt_name'])  # Runtime error: KeyError
    
    # Manual type handling
    age = int(user['age']) if user['age'] else 0
    
    # No IDE hints about available fields
    email = user.get('email', '')  # Is this field available?
```

### Desired Experience

```python
# Import generated models
from myapp.models import User, Product, Order

# Type-safe queries
users: List[User] = db.query_typed(User)
for user in users:
    # Full autocomplete and type checking
    print(user.first_name)  # IDE knows this exists and is str
    print(user.age)         # IDE knows this is int
    print(user.created_at)  # IDE knows this is datetime

# Type-safe inserts
new_user = User(
    first_name="Alice",
    last_name="Smith",
    age=30,  # Type checked as int
    email="alice@example.com"
)
user_id = db.insert_typed(new_user)

# Relationship access
orders: List[Order] = db.query_typed(Order, f'customer_id = "{user.row_id}"')
```

## Detailed Design

### Core Concepts

#### 1. Model Generation Strategies

**Runtime Generation** (Recommended for development)
```python
# Generate models at runtime
models = db.generate_models()

# Access generated classes
User = models.User
Product = models.Product

# Use in queries
users = db.query_typed(User)
```

**Code Generation** (Recommended for production)
```bash
# CLI command to generate model files
sdb generate-models --output models.py

# Creates models.py with all table classes
```

**Hybrid Approach**
```python
# Check if models exist, generate if needed
try:
    from .models import User
except ImportError:
    models = db.generate_models()
    User = models.User
```

#### 2. Type Mapping

SynthDB Type → Python Type mapping:
- `text` → `str`
- `integer` → `int`
- `real` → `float`
- `timestamp` → `datetime`
- `boolean` (stored as integer) → `bool`

#### 3. Model Features

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    """Auto-generated model for 'users' table."""
    # Required fields (no default)
    row_id: str
    first_name: str
    last_name: str
    
    # Optional fields (with defaults)
    age: Optional[int] = None
    email: Optional[str] = None
    is_active: bool = True
    
    # Auto-managed fields
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Table metadata
    __table_name__ = 'users'
    __primary_key__ = 'row_id'
    
    # Helper methods
    def to_dict(self) -> dict:
        """Convert to dictionary for insertion."""
        return {k: v for k, v in self.__dict__.items() 
                if not k.startswith('_') and v is not None}
```

### Implementation Approaches

#### Approach 1: Dataclasses (Recommended)

```python
from dataclasses import make_dataclass, field
from typing import Type, Dict, Any

class ModelGenerator:
    def __init__(self, connection):
        self.connection = connection
    
    def generate_model(self, table_name: str) -> Type:
        """Generate a dataclass model for a table."""
        columns = self.connection.list_columns(table_name)
        
        # Build field definitions
        fields = [
            ('row_id', str, field(default=None)),
            ('created_at', Optional[datetime], field(default=None)),
            ('updated_at', Optional[datetime], field(default=None))
        ]
        
        for col in columns:
            python_type = self._map_type(col['data_type'])
            # Make field optional if it can be null
            field_type = Optional[python_type]
            fields.append((col['name'], field_type, field(default=None)))
        
        # Create dataclass
        model_class = make_dataclass(
            table_name.title().replace('_', ''),
            fields,
            namespace={'__table_name__': table_name}
        )
        
        return model_class
    
    def _map_type(self, synthdb_type: str) -> Type:
        """Map SynthDB types to Python types."""
        type_map = {
            'text': str,
            'integer': int,
            'real': float,
            'timestamp': datetime
        }
        return type_map.get(synthdb_type, str)
```

#### Approach 2: Pydantic Models

```python
from pydantic import BaseModel, create_model
from typing import Type, Optional

class PydanticModelGenerator:
    def generate_model(self, table_name: str) -> Type[BaseModel]:
        """Generate a Pydantic model for validation."""
        columns = self.connection.list_columns(table_name)
        
        # Build field definitions
        field_definitions = {
            'row_id': (Optional[str], None),
            'created_at': (Optional[datetime], None),
            'updated_at': (Optional[datetime], None)
        }
        
        for col in columns:
            python_type = self._map_type(col['data_type'])
            field_definitions[col['name']] = (Optional[python_type], None)
        
        # Create Pydantic model
        model = create_model(
            table_name.title().replace('_', ''),
            __table_name__=(str, table_name),
            **field_definitions
        )
        
        return model
```

#### Approach 3: Code Generation

```python
class CodeGenerator:
    def generate_models_file(self, output_path: str):
        """Generate a Python file with all models."""
        tables = self.connection.list_tables()
        
        code = [
            "# Auto-generated models for SynthDB",
            "from dataclasses import dataclass",
            "from datetime import datetime",
            "from typing import Optional",
            "",
        ]
        
        for table in tables:
            code.extend(self._generate_model_code(table['name']))
            code.append("")
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(code))
    
    def _generate_model_code(self, table_name: str) -> List[str]:
        """Generate code for a single model."""
        columns = self.connection.list_columns(table_name)
        class_name = table_name.title().replace('_', '')
        
        code = [
            f"@dataclass",
            f"class {class_name}:",
            f'    """Model for {table_name} table."""',
            f"    row_id: Optional[str] = None",
            f"    created_at: Optional[datetime] = None",
            f"    updated_at: Optional[datetime] = None"
        ]
        
        for col in columns:
            python_type = self._type_to_string(col['data_type'])
            code.append(f"    {col['name']}: Optional[{python_type}] = None")
        
        code.extend([
            f"    ",
            f"    __table_name__ = '{table_name}'"
        ])
        
        return code
```

### API Design

#### Connection Extensions

```python
# Extend Connection class
class Connection:
    def query_typed(self, model_class: Type[T], 
                   where_clause: Optional[str] = None) -> List[T]:
        """Query with type-safe results."""
        table_name = model_class.__table_name__
        results = self.query(table_name, where_clause)
        
        # Convert dicts to model instances
        return [self._dict_to_model(row, model_class) for row in results]
    
    def insert_typed(self, model_instance: Any) -> str:
        """Insert using model instance."""
        table_name = model_instance.__table_name__
        data = model_instance.to_dict()
        return self.insert(table_name, data)
    
    def generate_models(self, 
                       namespace: Optional[str] = None) -> ModuleType:
        """Generate models for all tables."""
        generator = ModelGenerator(self)
        models = {}
        
        for table in self.list_tables():
            model_class = generator.generate_model(table['name'])
            models[model_class.__name__] = model_class
        
        # Create module with models
        if namespace:
            module = ModuleType(namespace)
            for name, cls in models.items():
                setattr(module, name, cls)
            return module
        
        return SimpleNamespace(**models)
```

#### CLI Integration

```bash
# Generate models to file
sdb generate-models --output app/models.py

# Generate with custom template
sdb generate-models --template pydantic --output app/schemas.py

# Generate TypeScript definitions
sdb generate-models --language typescript --output app/types.ts

# Watch mode - regenerate on schema changes
sdb generate-models --watch --output app/models.py
```

### Type Stub Generation

For better IDE support, generate .pyi stub files:

```python
# models.pyi
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    row_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    age: Optional[int]
    is_active: Optional[bool]
    
    __table_name__: str
    
    def to_dict(self) -> dict[str, Any]: ...
```

### Schema Evolution Handling

```python
class SchemaWatcher:
    """Watch for schema changes and regenerate models."""
    
    def __init__(self, connection, output_path: str):
        self.connection = connection
        self.output_path = output_path
        self.last_schema = self._get_current_schema()
    
    def check_and_regenerate(self):
        """Check if schema changed and regenerate if needed."""
        current_schema = self._get_current_schema()
        
        if current_schema != self.last_schema:
            print("Schema changed, regenerating models...")
            generator = CodeGenerator(self.connection)
            generator.generate_models_file(self.output_path)
            self.last_schema = current_schema
            
            # Reload modules if in development
            if os.environ.get('SYNTHDB_AUTO_RELOAD'):
                importlib.reload(sys.modules['app.models'])
```

## Trade-offs and Considerations

### Advantages

1. **Type Safety**: Catch errors at development time
2. **IDE Support**: Full autocomplete and inline documentation
3. **Better DX**: More intuitive API for Python developers
4. **Validation**: Optional data validation with Pydantic
5. **Documentation**: Auto-generated from schema
6. **Compatibility**: Works with mypy and other type checkers

### Disadvantages

1. **Complexity**: Adds significant complexity to the codebase
2. **Performance**: Model instantiation overhead for large result sets
3. **Schema Sync**: Models must be regenerated when schema changes
4. **Memory Usage**: Model instances use more memory than dicts
5. **Learning Curve**: Additional concepts for users to learn

### Performance Impact

```python
# Benchmark results (hypothetical)
# Query 10,000 rows:
# - Dict results: 0.15s, 50MB memory
# - Dataclass results: 0.35s, 85MB memory  
# - Pydantic results: 0.75s, 110MB memory

# Mitigation strategies:
# 1. Lazy model conversion
# 2. Optional model usage
# 3. Streaming results
# 4. __slots__ for memory efficiency
```

### Alternative Approaches

1. **TypedDict** (Simpler but less featured)
```python
from typing import TypedDict

class UserDict(TypedDict):
    row_id: str
    first_name: str
    last_name: str
    age: Optional[int]
```

2. **Protocol-based** (More flexible)
```python
from typing import Protocol

class UserProtocol(Protocol):
    row_id: str
    first_name: str
    last_name: str
```

3. **Query Builder with Types**
```python
# Type-safe query builder
users = (db.select(User)
           .where(User.age > 25)
           .order_by(User.created_at.desc())
           .fetch())
```

## Implementation Plan

### Phase 1: Core Model Generation (2-3 weeks)
- [ ] Implement dataclass generator
- [ ] Add type mapping system
- [ ] Create query_typed method
- [ ] Basic testing

### Phase 2: Code Generation (1-2 weeks)
- [ ] CLI command for generation
- [ ] File writing with templates
- [ ] Import/export utilities

### Phase 3: Advanced Features (2-3 weeks)
- [ ] Pydantic model support
- [ ] Relationship handling
- [ ] Schema watching
- [ ] Migration handling

### Phase 4: IDE Integration (1-2 weeks)
- [ ] Generate .pyi stubs
- [ ] VSCode extension
- [ ] Documentation

## Example Usage

### Basic CRUD with Models

```python
from synthdb import connect
from synthdb.models import generate_models

# Setup
db = connect('app.db')
models = generate_models(db)

# Create
user = models.User(
    first_name="Alice",
    last_name="Smith",
    email="alice@example.com",
    age=30
)
user_id = db.insert_typed(user)

# Read
users = db.query_typed(models.User, 'age > 25')
for user in users:
    print(f"{user.first_name} is {user.age} years old")

# Update
user.email = "newemail@example.com"
db.update_typed(user)

# Delete
db.delete_typed(user)
```

### Complex Queries with Type Safety

```python
# Join query with type inference
results = db.execute_sql_typed(
    """
    SELECT u.*, COUNT(o.row_id) as order_count
    FROM users u
    LEFT JOIN orders o ON u.row_id = o.user_id
    GROUP BY u.row_id
    """,
    model=models.UserWithOrderCount
)

for user in results:
    print(f"{user.first_name}: {user.order_count} orders")
```

### Integration with Existing Code

```python
# Gradual adoption - both APIs work
dict_results = db.query('users')  # Current API
typed_results = db.query_typed(models.User)  # New API

# Convert between formats
user_dict = typed_results[0].to_dict()
user_model = models.User(**dict_results[0])
```

## Integration with Saved Queries

Type-safe models can be seamlessly integrated with saved queries to provide type safety for complex, reusable queries. This combination offers the best of both worlds: reusable query logic with compile-time type checking.

### Generating Models from Saved Queries

```python
# Define a saved query
db.create_query(
    name="user_order_summary",
    query="""
        SELECT 
            u.row_id,
            u.first_name,
            u.last_name,
            u.email,
            COUNT(o.row_id) as order_count,
            SUM(o.total_amount) as total_spent,
            MAX(o.order_date) as last_order_date
        FROM users u
        LEFT JOIN orders o ON u.row_id = o.customer_id
        WHERE u.is_active = 1
            AND (:min_spent IS NULL OR total_spent >= :min_spent)
        GROUP BY u.row_id
    """,
    parameters={
        "min_spent": {"type": "real", "required": False}
    }
)

# Generate a model for the query result
@dataclass
class UserOrderSummary:
    """Auto-generated from saved query 'user_order_summary'."""
    row_id: str
    first_name: str
    last_name: str
    email: str
    order_count: int
    total_spent: float
    last_order_date: Optional[datetime]
    
    __query_name__ = 'user_order_summary'
```

### Type-Safe Query Execution

```python
# Execute saved query with type safety
summaries: List[UserOrderSummary] = db.execute_query_typed(
    'user_order_summary',
    model=UserOrderSummary,
    params={'min_spent': 100.0}
)

for summary in summaries:
    # Full type checking and autocomplete
    print(f"{summary.first_name} has {summary.order_count} orders")
    if summary.last_order_date:
        days_since = (datetime.now() - summary.last_order_date).days
        print(f"Last order: {days_since} days ago")
```

### Automatic Model Generation for Queries

```python
# Generate models for all saved queries
query_models = db.generate_query_models()

# Access generated classes
UserStats = query_models.UserOrderSummary
ProductAnalytics = query_models.ProductPerformance

# Use in type-safe queries
results = db.execute_query_typed('user_order_summary', model=UserStats)
```

### CLI Integration

```bash
# Generate models for both tables and saved queries
sdb generate-models --include-queries --output app/models.py

# Generate only query models
sdb generate-query-models --output app/query_models.py

# Watch for new saved queries and regenerate
sdb generate-models --watch --include-queries --output app/models.py
```

### Advanced Query Model Features

```python
class QueryModelGenerator:
    def generate_from_query(self, query_name: str) -> Type:
        """Generate model from saved query result schema."""
        # Analyze query to determine result columns
        query_def = self.db.get_query_definition(query_name)
        result_schema = self.analyze_query_results(query_def.query_text)
        
        # Generate dataclass with proper types
        fields = []
        for col in result_schema:
            python_type = self._map_sql_type(col.type)
            fields.append((col.name, python_type, field(default=None)))
        
        # Add query metadata
        namespace = {
            '__query_name__': query_name,
            '__parameters__': query_def.parameters,
            'execute': lambda self, **params: self._db.execute_query_typed(
                query_name, model=self.__class__, params=params
            )
        }
        
        return make_dataclass(
            f"{query_name.title().replace('_', '')}Result",
            fields,
            namespace=namespace
        )
```

### Composing Models with Queries

```python
# Define base model
@dataclass
class User:
    row_id: str
    first_name: str
    last_name: str
    email: str
    
    def get_order_summary(self) -> UserOrderSummary:
        """Execute saved query for this user."""
        results = db.execute_query_typed(
            'user_order_summary',
            model=UserOrderSummary,
            params={'user_id': self.row_id}
        )
        return results[0] if results else None
```

### Benefits of Integration

1. **Type Safety for Complex Queries**: Get compile-time checking for saved query results
2. **Reusability**: Define query once, use with type safety everywhere
3. **Documentation**: Generated models document query result structure
4. **Refactoring Safety**: Changes to query structure are caught at compile time
5. **IDE Support**: Full autocomplete for query results

## Future Enhancements

1. **Relationship Support**
```python
@dataclass
class User:
    # ... fields ...
    
    @property
    def orders(self) -> List['Order']:
        return self._db.query_typed(Order, f'user_id = "{self.row_id}"')
```

2. **Custom Validators**
```python
@dataclass
class User:
    email: str
    
    def __post_init__(self):
        if '@' not in self.email:
            raise ValueError("Invalid email")
```

3. **GraphQL Integration**
```python
# Auto-generate GraphQL schema from models
schema = generate_graphql_schema(models)
```

4. **ORM-like Features**
```python
# Active Record pattern
user = User.find_by_id(user_id)
user.email = "new@example.com"
user.save()
```

5. **Query Result Caching with Types**
```python
# Cache typed results from saved queries
@cached_query(ttl=300)
def get_user_stats(min_spent: float) -> List[UserOrderSummary]:
    return db.execute_query_typed(
        'user_order_summary',
        model=UserOrderSummary,
        params={'min_spent': min_spent}
    )
```

## Conclusion

Type-safe models would significantly improve the developer experience when working with SynthDB, providing the benefits of static typing while maintaining the flexibility of dynamic schemas. The implementation should be optional and non-breaking, allowing gradual adoption and supporting both typed and untyped usage patterns.

The recommended approach is to start with dataclass-based runtime generation for simplicity, then add code generation for production use cases. This provides a good balance between functionality, performance, and maintainability.
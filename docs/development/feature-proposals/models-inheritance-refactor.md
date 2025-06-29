# Feature Proposal: Models Inheritance Refactor

## Summary
Refactor the current dynamic extension approach for models to use proper inheritance, improving type safety, IDE support, and code clarity.

## Current Implementation
Currently, we dynamically extend the Connection class with model methods using `extend_connection_with_models()`:

```python
def extend_connection_with_models(connection: Connection) -> None:
    """Extend Connection class with model-related methods."""
    connection.query_typed = query_typed.__get__(connection, Connection)
    connection.insert_typed = insert_typed.__get__(connection, Connection)
    # ... etc
```

### Problems with Current Approach
1. **Type checking issues** - IDEs and mypy can't see dynamically added methods
2. **Runtime overhead** - Method binding happens at runtime
3. **Poor discoverability** - Developers can't easily see what methods are available
4. **Violates principle of least surprise** - Methods appear/disappear based on runtime state
5. **Complex testing** - Need to test both states (with/without models)

## Proposed Solution

### Option 1: Pure Inheritance
```python
class ConnectionWithModels(Connection):
    """Connection with type-safe model support."""
    
    def query_typed(self, model_class: Type[SynthDBModel], 
                   where: Optional[str] = None) -> List[SynthDBModel]:
        """Query data and return typed model instances."""
        table_name = model_class.get_table_name()
        results = self.query(table_name, where)
        return [model_class.from_dict(row) for row in results]
    
    def insert_typed(self, model_instance: SynthDBModel) -> str:
        """Insert a model instance into the database."""
        table_name = model_instance.get_table_name()
        data = model_instance.to_dict(exclude_meta=True)
        return self.insert(table_name, data)
    
    def upsert_typed(self, model_instance: SynthDBModel) -> str:
        """Upsert a model instance into the database."""
        if not model_instance.id:
            return self.insert_typed(model_instance)
        
        table_name = model_instance.get_table_name()
        data = model_instance.to_dict(exclude_meta=True)
        return self.upsert(table_name, data, model_instance.id)
    
    def execute_query_typed(self, query_name: str, model_class: Type[SynthDBModel],
                           **params) -> List[SynthDBModel]:
        """Execute a saved query and return typed model instances."""
        results = self.queries.execute_query(query_name, **params)
        return [model_class.from_dict(row) for row in results]
    
    def generate_models(self) -> Dict[str, Type[SynthDBModel]]:
        """Generate models for all tables."""
        generator = ModelGenerator(self)
        return generator.generate_all_models()
    
    def generate_model(self, table_name: str) -> Type[SynthDBModel]:
        """Generate a model for a specific table."""
        generator = ModelGenerator(self)
        return generator.generate_model(table_name)
```

### Option 2: Mixin-Based Approach (Recommended)
```python
class ModelMixin:
    """Mixin providing model functionality for connections."""
    
    def query_typed(self: 'Connection', model_class: Type[SynthDBModel], 
                   where: Optional[str] = None) -> List[SynthDBModel]:
        """Query data and return typed model instances."""
        table_name = model_class.get_table_name()
        results = self.query(table_name, where)
        return [model_class.from_dict(row) for row in results]
    
    # ... other model methods

class Connection:
    """Base connection class."""
    # ... existing implementation

class ConnectionWithModels(Connection, ModelMixin):
    """Connection with integrated model support."""
    pass

# Update connect function with proper return type
@overload
def connect(connection_info: Union[str, Dict[str, Any]] = None, 
           backend: Optional[str] = None, 
           auto_init: bool = True, 
           models: Literal[False] = False) -> Connection: ...

@overload
def connect(connection_info: Union[str, Dict[str, Any]] = None, 
           backend: Optional[str] = None, 
           auto_init: bool = True, 
           models: Literal[True] = True) -> ConnectionWithModels: ...

def connect(connection_info: Union[str, Dict[str, Any]] = None, 
           backend: Optional[str] = None, 
           auto_init: bool = True, 
           models: bool = False) -> Union[Connection, ConnectionWithModels]:
    """Create a SynthDB connection."""
    if models:
        return ConnectionWithModels(connection_info, backend, auto_init)
    return Connection(connection_info, backend, auto_init)
```

## Benefits

1. **Full type safety** - IDEs and type checkers can see all methods
2. **Better performance** - No runtime method binding
3. **Clear API** - Users can see exactly what methods are available
4. **Easier testing** - Test each class independently
5. **Better documentation** - Each class documents its specific functionality
6. **Follows SOLID principles** - Single responsibility, open/closed

## Migration Path

1. Create new classes without removing old functionality
2. Deprecate `extend_connection_with_models()` with warnings
3. Update documentation and examples
4. Remove deprecated code in next major version

## Implementation Considerations

### Backward Compatibility
```python
def extend_connection_with_models(connection: Connection) -> None:
    """DEPRECATED: Use connect(..., models=True) instead."""
    import warnings
    warnings.warn(
        "extend_connection_with_models is deprecated. "
        "Use connect(..., models=True) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Still work but log warning
```

### Type Stubs
For better IDE support, we could provide type stubs:

```python
# synthdb/py.typed  # marker file

# synthdb/__init__.pyi
from typing import Union, overload, Literal
from .connection import Connection, ConnectionWithModels

@overload
def connect(..., models: Literal[False] = False) -> Connection: ...
@overload  
def connect(..., models: Literal[True]) -> ConnectionWithModels: ...
```

## Example Usage

```python
# Without models - returns Connection
db = synthdb.connect('mydb.db')
# db.query_typed()  # ← IDE shows error: no such method

# With models - returns ConnectionWithModels  
db = synthdb.connect('mydb.db', models=True)
# db.query_typed()  # ← IDE shows method with full type hints

# Type annotations work correctly
def process_users(db: ConnectionWithModels) -> None:
    users = db.query_typed(User)  # Full type safety
    for user in users:
        print(user.name)  # IDE knows user is a User instance
```

## Timeline

1. **Phase 1** (v0.x.0): Implement new classes alongside existing code
2. **Phase 2** (v0.x.1): Add deprecation warnings
3. **Phase 3** (v1.0.0): Remove deprecated dynamic extension code

## Related Work

This pattern is used successfully in many Python libraries:
- SQLAlchemy: `Session` vs `AsyncSession`
- Django: `Model` vs `Model` with mixins
- Flask: `Flask` vs `Flask` with extensions

## Decision

**Status**: Proposed

**Next Steps**: 
1. Gather feedback from users
2. Create proof of concept
3. Benchmark performance difference
4. Plan migration strategy
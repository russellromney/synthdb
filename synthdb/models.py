"""Type-safe models for SynthDB using Pydantic."""

import re
from datetime import datetime
from typing import Type, Dict, Any, List, Optional
from pydantic import BaseModel, Field, create_model, ConfigDict

from .connection import Connection


class SynthDBModel(BaseModel):
    """Base class for all SynthDB models."""
    
    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True,
        str_strip_whitespace=True,
        populate_by_name=True
    )
    
    # Metadata fields - these are always present
    id: Optional[str] = Field(None, description="Row identifier")
    created_at: Optional[datetime] = Field(None, description="Row creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Row last update timestamp")
    
    # Class attributes for table metadata
    __table_name__: str = ""
    __connection__: Optional[Connection] = None
    
    @classmethod
    def get_table_name(cls) -> str:
        """Get the table name for this model."""
        if cls.__table_name__:
            return cls.__table_name__
        # Convert class name to snake_case
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    
    @classmethod
    def set_connection(cls, connection: Connection) -> None:
        """Set the database connection for this model."""
        cls.__connection__ = connection
    
    def to_dict(self, exclude_meta: bool = False) -> Dict[str, Any]:
        """Convert model to dictionary for database operations."""
        data = self.model_dump(exclude_unset=True, exclude_none=True)
        if exclude_meta:
            meta_fields = {'id', 'created_at', 'updated_at'}
            data = {k: v for k, v in data.items() if k not in meta_fields}
        return data
    
    def save(self) -> str:
        """Save this model instance to the database."""
        if not self.__connection__:
            raise ValueError("No database connection set for this model")
        
        table_name = self.get_table_name()
        data = self.to_dict(exclude_meta=True)
        
        if self.id:
            # Update existing record
            self.__connection__.upsert(table_name, data, self.id)
            return self.id
        else:
            # Insert new record
            new_id = self.__connection__.insert(table_name, data)
            self.id = new_id
            return new_id
    
    def delete(self) -> bool:
        """Delete this model instance from the database."""
        if not self.__connection__:
            raise ValueError("No database connection set for this model")
        if not self.id:
            raise ValueError("Cannot delete model without an ID")
        
        table_name = self.get_table_name()
        return self.__connection__.delete_row(table_name, self.id)
    
    def refresh(self) -> None:
        """Refresh this model instance from the database."""
        if not self.__connection__:
            raise ValueError("No database connection set for this model")
        if not self.id:
            raise ValueError("Cannot refresh model without an ID")
        
        table_name = self.get_table_name()
        results = self.__connection__.query(table_name, f"id = '{self.id}'")
        if not results:
            raise ValueError(f"Record with id '{self.id}' not found")
        
        # Update this instance with fresh data
        for key, value in results[0].items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def find_by_id(cls, id: str) -> Optional['SynthDBModel']:
        """Find a model instance by ID."""
        if not cls.__connection__:
            raise ValueError("No database connection set for this model")
        
        table_name = cls.get_table_name()
        results = cls.__connection__.query(table_name, f"id = '{id}'")
        if not results:
            return None
        
        return cls.from_dict(results[0])
    
    @classmethod
    def find_all(cls, where: Optional[str] = None) -> List['SynthDBModel']:
        """Find all model instances matching the where clause."""
        if not cls.__connection__:
            raise ValueError("No database connection set for this model")
        
        table_name = cls.get_table_name()
        results = cls.__connection__.query(table_name, where)
        return [cls.from_dict(row) for row in results]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SynthDBModel':
        """Create a model instance from a dictionary."""
        return cls(**data)


class ModelGenerator:
    """Generate Pydantic models from SynthDB table schemas."""
    
    def __init__(self, connection: Connection):
        self.connection = connection
    
    def generate_model(self, table_name: str, model_name: Optional[str] = None) -> Type[SynthDBModel]:
        """Generate a Pydantic model for a specific table."""
        if model_name is None:
            # Convert table name to PascalCase
            model_name = self._table_name_to_class_name(table_name)
        
        # Get table columns
        columns = self.connection.list_columns(table_name)
        
        # Build field definitions
        field_definitions = {}
        
        for col in columns:
            if col['name'] in ('id', 'created_at', 'updated_at'):
                # These are handled by the base class
                continue
            
            python_type = self._map_synthdb_type(col['data_type'])
            # Make all fields optional by default since SynthDB is flexible
            field_type = Optional[python_type]
            field_definitions[col['name']] = (field_type, Field(None, description=f"Column '{col['name']}' from table '{table_name}'"))
        
        # Create the model
        model = create_model(
            model_name,
            __base__=SynthDBModel,
            __table_name__=(str, table_name),
            **field_definitions
        )
        
        # Set the connection
        model.set_connection(self.connection)
        
        return model
    
    def generate_all_models(self) -> Dict[str, Type[SynthDBModel]]:
        """Generate models for all tables in the database."""
        tables = self.connection.list_tables()
        models = {}
        
        for table in tables:
            table_name = table['name']
            model = self.generate_model(table_name)
            models[model.__name__] = model
        
        return models
    
    def generate_query_model(self, query_name: str, model_name: Optional[str] = None) -> Type[SynthDBModel]:
        """Generate a model for a saved query result."""
        if model_name is None:
            model_name = self._query_name_to_class_name(query_name)
        
        # Get the query definition
        query_def = self.connection.queries.get_query(query_name)
        if not query_def:
            raise ValueError(f"Saved query '{query_name}' not found")
        
        # Execute the query with LIMIT 0 to get column information
        # This is a trick to get column info without actual data
        limited_query = f"SELECT * FROM ({query_def.query_text}) LIMIT 0"
        
        try:
            # Try to execute the query to get column information
            # Since we limited to 0, we won't get any rows, but we need to infer from the actual query
            # For now, we'll create a generic model and let runtime validation handle it
            
            # Create a model with flexible fields
            field_definitions = {
                '__query_name__': (str, query_name),
            }
            
            # Create the model with the base fields only for now
            # In a more sophisticated implementation, we could parse the SQL to determine columns
            model = create_model(
                model_name,
                __base__=SynthDBModel,
                __query_name__=(str, query_name),
                **field_definitions
            )
            
            model.set_connection(self.connection)
            return model
            
        except Exception as e:
            raise ValueError(f"Could not analyze query '{query_name}': {e}")
    
    def _map_synthdb_type(self, synthdb_type: str) -> Type:
        """Map SynthDB types to Python types."""
        type_mapping = {
            'text': str,
            'integer': int,
            'real': float,
            'timestamp': datetime,
        }
        return type_mapping.get(synthdb_type.lower(), str)
    
    def _table_name_to_class_name(self, table_name: str) -> str:
        """Convert table name to PascalCase class name."""
        # Split on underscores and capitalize each part
        parts = table_name.split('_')
        return ''.join(word.capitalize() for word in parts)
    
    def _query_name_to_class_name(self, query_name: str) -> str:
        """Convert query name to PascalCase class name."""
        # Split on underscores and capitalize each part, add Result suffix
        parts = query_name.split('_')
        return ''.join(word.capitalize() for word in parts) + 'Result'


class Relationship:
    """Define relationships between models."""
    
    def __init__(self, related_model: Type[SynthDBModel], foreign_key: str, 
                 related_key: str = 'id', relationship_type: str = 'one_to_many'):
        self.related_model = related_model
        self.foreign_key = foreign_key
        self.related_key = related_key
        self.relationship_type = relationship_type  # 'one_to_many', 'many_to_one', 'one_to_one'
    
    def get_related(self, instance: SynthDBModel) -> List[SynthDBModel]:
        """Get related model instances."""
        if not instance.__connection__:
            raise ValueError("No database connection set")
        
        if self.relationship_type == 'one_to_many':
            # Get related records where foreign_key matches this instance's related_key
            key_value = getattr(instance, self.related_key)
            if key_value is None:
                return []
            
            where_clause = f"{self.foreign_key} = '{key_value}'"
            return self.related_model.find_all(where_clause)
            
        elif self.relationship_type == 'many_to_one':
            # Get the single related record
            foreign_key_value = getattr(instance, self.foreign_key)
            if foreign_key_value is None:
                return []
            
            related = self.related_model.find_by_id(foreign_key_value)
            return [related] if related else []
            
        elif self.relationship_type == 'one_to_one':
            # Similar to many_to_one but expects exactly one result
            return self.get_related_one_to_one(instance)
        
        return []
    
    def get_related_one_to_one(self, instance: SynthDBModel) -> List[SynthDBModel]:
        """Get related model for one-to-one relationship."""
        foreign_key_value = getattr(instance, self.foreign_key)
        if foreign_key_value is None:
            return []
        
        where_clause = f"{self.related_key} = '{foreign_key_value}'"
        results = self.related_model.find_all(where_clause)
        return results[:1]  # Return at most one result


def add_relationship(model_class: Type[SynthDBModel], relationship_name: str, 
                    relationship: Relationship) -> None:
    """Add a relationship property to a model class."""
    
    def get_related_instances(self) -> List[SynthDBModel]:
        """Get instances related through the defined relationship."""
        return relationship.get_related(self)
    
    # Add the property to the model class
    setattr(model_class, relationship_name, property(get_related_instances))


# Connection extension methods
def extend_connection_with_models(connection: Connection) -> None:
    """Extend Connection class with model-related methods."""
    
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
    
    # Add methods to the connection instance
    connection.query_typed = query_typed.__get__(connection, Connection)
    connection.insert_typed = insert_typed.__get__(connection, Connection)
    connection.upsert_typed = upsert_typed.__get__(connection, Connection)
    connection.execute_query_typed = execute_query_typed.__get__(connection, Connection)
    connection.generate_models = generate_models.__get__(connection, Connection)
    connection.generate_model = generate_model.__get__(connection, Connection)


# Automatically extend connections when this module is imported
def connect_with_models(*args, **kwargs) -> Connection:
    """Create a connection with model support enabled."""
    from . import connect
    connection = connect(*args, **kwargs)
    extend_connection_with_models(connection)
    return connection
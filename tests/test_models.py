"""Tests for type-safe models functionality."""

import tempfile
import os
import pytest
from datetime import datetime

from synthdb import connect
from synthdb.models import (
    SynthDBModel, ModelGenerator, extend_connection_with_models,
    Relationship, add_relationship
)


class TestTypeafeModels:
    """Test type-safe models functionality."""
    
    def setup_method(self):
        """Set up test database."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        # Create database with test data
        self.db = connect(self.db_path)
        extend_connection_with_models(self.db)
        
        # Create test tables
        self.db.create_table('users')
        self.db.add_columns('users', {
            'name': 'text',
            'email': 'text',
            'age': 'integer',
            'is_active': 'integer'  # Will be treated as boolean
        })
        
        self.db.create_table('posts')
        self.db.add_columns('posts', {
            'title': 'text',
            'content': 'text',
            'user_id': 'text',
            'views': 'integer'
        })
        
        # Insert test data
        self.user_id = self.db.insert('users', {
            'name': 'Alice',
            'email': 'alice@example.com',
            'age': 25,
            'is_active': 1
        })
        
        self.post_id = self.db.insert('posts', {
            'title': 'Test Post',
            'content': 'This is a test post',
            'user_id': self.user_id,
            'views': 100
        })
    
    def teardown_method(self):
        """Clean up test database."""
        if hasattr(self, 'db'):
            self.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_model_generation(self):
        """Test generating models from table schema."""
        generator = ModelGenerator(self.db)
        
        # Generate User model
        User = generator.generate_model('users')
        
        assert User.__name__ == 'Users'
        assert User.get_table_name() == 'users'
        assert hasattr(User, 'name')
        assert hasattr(User, 'email')
        assert hasattr(User, 'age')
        assert hasattr(User, 'is_active')
        
        # Test model instantiation
        user = User(name="Bob", email="bob@example.com", age=30)
        assert user.name == "Bob"
        assert user.email == "bob@example.com"
        assert user.age == 30
    
    def test_model_crud_operations(self):
        """Test CRUD operations with models."""
        # Generate model
        User = self.db.generate_model('users')
        
        # Create a new user
        new_user = User(
            name="Charlie",
            email="charlie@example.com",
            age=28,
            is_active=1
        )
        
        # Save to database
        user_id = new_user.save()
        assert user_id is not None
        assert new_user.id == user_id
        
        # Find by ID
        found_user = User.find_by_id(user_id)
        assert found_user is not None
        assert found_user.name == "Charlie"
        assert found_user.email == "charlie@example.com"
        
        # Update
        found_user.age = 29
        found_user.save()
        
        # Refresh
        found_user.refresh()
        assert found_user.age == 29
        
        # Delete
        deleted = found_user.delete()
        assert deleted is True
        
        # Verify deletion
        deleted_user = User.find_by_id(user_id)
        assert deleted_user is None
    
    def test_model_queries(self):
        """Test querying with models."""
        # Generate model
        User = self.db.generate_model('users')
        
        # Query all users
        all_users = User.find_all()
        assert len(all_users) == 1  # One user from setup
        assert all_users[0].name == "Alice"
        
        # Query with where clause
        active_users = User.find_all("is_active = 1")
        assert len(active_users) == 1
        
        # Query with connection's typed methods
        typed_users = self.db.query_typed(User)
        assert len(typed_users) == 1
        assert isinstance(typed_users[0], User)
    
    def test_model_validation(self):
        """Test Pydantic validation in models."""
        User = self.db.generate_model('users')
        
        # Valid data
        user = User(name="Valid User", email="valid@example.com", age=25)
        assert user.name == "Valid User"
        
        # Test type coercion
        user_with_string_age = User(name="User", email="user@example.com", age="30")
        assert user_with_string_age.age == 30
        assert isinstance(user_with_string_age.age, int)
    
    def test_generate_all_models(self):
        """Test generating models for all tables."""
        models = self.db.generate_models()
        
        assert 'Users' in models
        assert 'Posts' in models
        
        User = models['Users']
        Post = models['Posts']
        
        assert User.get_table_name() == 'users'
        assert Post.get_table_name() == 'posts'
    
    def test_model_to_dict(self):
        """Test converting models to dictionaries."""
        User = self.db.generate_model('users')
        
        user = User(name="Test User", email="test@example.com", age=25)
        
        # Full dict
        full_dict = user.to_dict()
        assert 'name' in full_dict
        assert 'email' in full_dict
        assert 'age' in full_dict
        
        # Exclude meta fields
        data_dict = user.to_dict(exclude_meta=True)
        assert 'name' in data_dict
        assert 'id' not in data_dict
        assert 'created_at' not in data_dict
        assert 'updated_at' not in data_dict
    
    def test_model_from_dict(self):
        """Test creating models from dictionaries."""
        User = self.db.generate_model('users')
        
        data = {
            'id': '123',
            'name': 'Dict User',
            'email': 'dict@example.com',
            'age': 30,
            'is_active': 1,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        user = User.from_dict(data)
        assert user.id == '123'
        assert user.name == 'Dict User'
        assert user.email == 'dict@example.com'
        assert user.age == 30
    
    def test_relationship_support(self):
        """Test relationship functionality between models."""
        User = self.db.generate_model('users')
        Post = self.db.generate_model('posts')
        
        # Define relationship: User has many Posts
        user_posts_relationship = Relationship(
            related_model=Post,
            foreign_key='user_id',
            related_key='id',
            relationship_type='one_to_many'
        )
        
        add_relationship(User, 'posts', user_posts_relationship)
        
        # Get user
        user = User.find_by_id(self.user_id)
        assert user is not None
        
        # Access related posts
        posts = user.posts  # This should work due to the relationship
        assert len(posts) == 1
        assert posts[0].title == 'Test Post'
        assert posts[0].user_id == self.user_id
    
    def test_connection_extension_methods(self):
        """Test connection methods added by model extension."""
        User = self.db.generate_model('users')
        
        # Test query_typed
        users = self.db.query_typed(User, "age > 20")
        assert len(users) == 1
        assert isinstance(users[0], User)
        
        # Test insert_typed
        new_user = User(name="Typed User", email="typed@example.com", age=35)
        user_id = self.db.insert_typed(new_user)
        assert user_id is not None
        
        # Test upsert_typed
        new_user.id = user_id
        new_user.age = 36
        updated_id = self.db.upsert_typed(new_user)
        assert updated_id == user_id
        
        # Verify update
        updated_user = User.find_by_id(user_id)
        assert updated_user.age == 36
    
    def test_model_inheritance(self):
        """Test that generated models inherit from SynthDBModel."""
        User = self.db.generate_model('users')
        
        assert issubclass(User, SynthDBModel)
        
        # Test base model functionality
        user = User(name="Inherited User", email="inherit@example.com")
        assert hasattr(user, 'id')
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')
        assert hasattr(user, 'save')
        assert hasattr(user, 'delete')
        assert hasattr(user, 'refresh')
    
    def test_model_table_name_conversion(self):
        """Test table name to class name conversion."""
        generator = ModelGenerator(self.db)
        
        # Test various naming conventions
        assert generator._table_name_to_class_name('users') == 'Users'
        assert generator._table_name_to_class_name('user_profiles') == 'UserProfiles'
        assert generator._table_name_to_class_name('order_line_items') == 'OrderLineItems'
        assert generator._table_name_to_class_name('api_keys') == 'ApiKeys'
    
    def test_type_mapping(self):
        """Test SynthDB to Python type mapping."""
        generator = ModelGenerator(self.db)
        
        assert generator._map_synthdb_type('text') == str
        assert generator._map_synthdb_type('integer') == int
        assert generator._map_synthdb_type('real') == float
        assert generator._map_synthdb_type('timestamp') == datetime
        assert generator._map_synthdb_type('unknown_type') == str  # Default fallback
    
    def test_model_without_connection_error(self):
        """Test that models require a connection for database operations."""
        generator = ModelGenerator(self.db)
        User = generator.generate_model('users')
        
        # Clear the connection
        User.__connection__ = None
        
        user = User(name="No Connection", email="no@example.com")
        
        # These should raise ValueError
        with pytest.raises(ValueError, match="No database connection"):
            user.save()
        
        with pytest.raises(ValueError, match="No database connection"):
            User.find_by_id("123")
        
        with pytest.raises(ValueError, match="No database connection"):
            User.find_all()
    
    def test_model_operations_without_id(self):
        """Test model operations that require an ID."""
        User = self.db.generate_model('users')
        
        user = User(name="No ID User", email="noid@example.com")
        
        # These should raise ValueError because user has no ID
        with pytest.raises(ValueError, match="Cannot delete model without an ID"):
            user.delete()
        
        with pytest.raises(ValueError, match="Cannot refresh model without an ID"):
            user.refresh()
    
    def test_model_config(self):
        """Test Pydantic model configuration."""
        User = self.db.generate_model('users')
        
        # Test that the model has proper configuration
        assert User.model_config['extra'] == 'forbid'  # Should not allow extra fields
        assert User.model_config['validate_assignment'] is True
        
        # Test extra field rejection
        with pytest.raises(Exception):  # Pydantic ValidationError
            User(name="Test", email="test@example.com", unknown_field="value")
    
    def test_query_model_generation(self):
        """Test generating models for saved queries."""
        # First create a saved query
        self.db.queries.create_query(
            name='user_stats',
            query_text='SELECT name, age, COUNT(*) as post_count FROM users u LEFT JOIN posts p ON u.id = p.user_id GROUP BY u.id',
            description='User statistics with post count'
        )
        
        # Generate model for the query
        generator = ModelGenerator(self.db)
        UserStatsResult = generator.generate_query_model('user_stats')
        
        assert UserStatsResult.__name__ == 'UserStatsResult'
        assert hasattr(UserStatsResult, '__query_name__')
        assert UserStatsResult.__query_name__ == 'user_stats'
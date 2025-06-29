"""Tests for saved queries functionality."""

import tempfile
import os
import pytest
from synthdb import connect
from synthdb.saved_queries import QueryManager, SavedQuery, QueryParameter


class TestSavedQueries:
    """Test saved queries functionality."""
    
    def setup_method(self):
        """Set up test database."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        # Create database with test data
        self.db = connect(self.db_path)
        
        # Create test tables
        self.db.create_table('users')
        self.db.add_columns('users', {
            'name': 'text',
            'age': 'integer',
            'email': 'text',
            'status': 'text'
        })
        
        self.db.create_table('orders')
        self.db.add_columns('orders', {
            'user_id': 'text',
            'product': 'text',
            'total': 'real',
            'status': 'text'
        })
        
        # Insert test data
        user1_id = self.db.insert('users', {
            'name': 'Alice',
            'age': 25,
            'email': 'alice@example.com',
            'status': 'active'
        })
        user2_id = self.db.insert('users', {
            'name': 'Bob',
            'age': 30,
            'email': 'bob@example.com',
            'status': 'active'
        })
        user3_id = self.db.insert('users', {
            'name': 'Charlie',
            'age': 20,
            'email': 'charlie@example.com',
            'status': 'inactive'
        })
        
        self.db.insert('orders', {
            'user_id': user1_id,
            'product': 'Widget A',
            'total': 99.99,
            'status': 'completed'
        })
        self.db.insert('orders', {
            'user_id': user2_id,
            'product': 'Widget B',
            'total': 149.99,
            'status': 'completed'
        })
        self.db.insert('orders', {
            'user_id': user1_id,
            'product': 'Widget C',
            'total': 79.99,
            'status': 'pending'
        })
    
    def teardown_method(self):
        """Clean up test database."""
        if hasattr(self, 'db'):
            self.db.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_create_simple_query(self):
        """Test creating a simple query without parameters."""
        query = self.db.queries.create_query(
            name='all_users',
            query_text='SELECT * FROM users',
            description='Get all users'
        )
        
        assert query.name == 'all_users'
        assert query.description == 'Get all users'
        assert query.id is not None
        assert len(query.parameters) == 0
    
    def test_create_query_with_parameters(self):
        """Test creating a query with parameters."""
        query = self.db.queries.create_query(
            name='adults_only',
            query_text='SELECT * FROM users WHERE age >= :min_age AND status = :status',
            description='Get users above minimum age with specific status',
            parameters={
                'min_age': {
                    'type': 'integer',
                    'default': 18,
                    'description': 'Minimum age threshold'
                },
                'status': {
                    'type': 'text',
                    'required': True,
                    'description': 'User status to filter by'
                }
            }
        )
        
        assert query.name == 'adults_only'
        assert len(query.parameters) == 2
        
        # Check min_age parameter
        min_age_param = next(p for p in query.parameters if p.name == 'min_age')
        assert min_age_param.data_type == 'integer'
        assert min_age_param.default_value == '18'
        assert not min_age_param.is_required  # Should not be required since it has a default
        
        # Check status parameter
        status_param = next(p for p in query.parameters if p.name == 'status')
        assert status_param.data_type == 'text'
        assert status_param.default_value is None
        assert status_param.is_required
    
    def test_query_name_validation(self):
        """Test query name validation."""
        # Valid names
        valid_names = ['users_query', 'user123', 'user_data_v2', 'Q1-2024']
        for name in valid_names:
            query = self.db.queries.create_query(
                name=name,
                query_text='SELECT * FROM users'
            )
            assert query.name == name
        
        # Invalid names
        invalid_names = ['123users', '', 'user query', 'user@query', None]
        for name in invalid_names:
            with pytest.raises(ValueError):
                self.db.queries.create_query(
                    name=name,
                    query_text='SELECT * FROM users'
                )
    
    def test_query_syntax_validation(self):
        """Test query syntax validation."""
        # Valid SELECT queries
        valid_queries = [
            'SELECT * FROM users',
            'select name, age from users where age > 25',
            'SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id'
        ]
        for i, query_text in enumerate(valid_queries):
            query = self.db.queries.create_query(
                name=f'valid_query_{i}',
                query_text=query_text
            )
            assert query.query_text == query_text
        
        # Invalid queries
        invalid_queries = [
            '',
            'DROP TABLE users',
            'INSERT INTO users VALUES (1, "test")',
            'UPDATE users SET name = "test"',
            'DELETE FROM users',
            'CREATE TABLE test (id INTEGER)',
            'ALTER TABLE users ADD COLUMN test TEXT'
        ]
        for query_text in invalid_queries:
            with pytest.raises(ValueError):
                self.db.queries.create_query(
                    name='invalid_query',
                    query_text=query_text
                )
    
    def test_duplicate_query_names(self):
        """Test that duplicate query names are not allowed."""
        self.db.queries.create_query(
            name='test_query',
            query_text='SELECT * FROM users'
        )
        
        with pytest.raises(ValueError, match="already exists"):
            self.db.queries.create_query(
                name='test_query',
                query_text='SELECT * FROM orders'
            )
    
    def test_get_query(self):
        """Test retrieving a saved query."""
        original = self.db.queries.create_query(
            name='test_get',
            query_text='SELECT name FROM users WHERE age > :age',
            description='Test query for retrieval',
            parameters={
                'age': {'type': 'integer', 'default': 25}
            }
        )
        
        retrieved = self.db.queries.get_query('test_get')
        assert retrieved is not None
        assert retrieved.name == original.name
        assert retrieved.query_text == original.query_text
        assert retrieved.description == original.description
        assert len(retrieved.parameters) == len(original.parameters)
        
        # Test non-existent query
        assert self.db.queries.get_query('non_existent') is None
    
    def test_list_queries(self):
        """Test listing saved queries."""
        # Create multiple queries
        queries_data = [
            ('query1', 'SELECT * FROM users'),
            ('query2', 'SELECT * FROM orders'),
            ('query3', 'SELECT name FROM users WHERE age > 25')
        ]
        
        for name, query_text in queries_data:
            self.db.queries.create_query(name=name, query_text=query_text)
        
        # List all queries
        queries = self.db.queries.list_queries()
        assert len(queries) == 3
        query_names = [q.name for q in queries]
        assert 'query1' in query_names
        assert 'query2' in query_names
        assert 'query3' in query_names
    
    def test_execute_query_without_parameters(self):
        """Test executing a query without parameters."""
        self.db.queries.create_query(
            name='active_users',
            query_text="SELECT name, age FROM users WHERE status = 'active'"
        )
        
        results = self.db.queries.execute_query('active_users')
        assert len(results) == 2  # Alice and Bob
        names = [r['name'] for r in results]
        assert 'Alice' in names
        assert 'Bob' in names
        assert 'Charlie' not in names  # Charlie is inactive
    
    def test_execute_query_with_parameters(self):
        """Test executing a query with parameters."""
        self.db.queries.create_query(
            name='users_by_age',
            query_text='SELECT name, age FROM users WHERE age >= :min_age',
            parameters={
                'min_age': {'type': 'integer', 'default': 18}
            }
        )
        
        # Execute with default parameter
        results = self.db.queries.execute_query('users_by_age')
        assert len(results) == 3  # All users
        
        # Execute with specific parameter
        results = self.db.queries.execute_query('users_by_age', min_age=25)
        assert len(results) == 2  # Alice and Bob
        names = [r['name'] for r in results]
        assert 'Alice' in names
        assert 'Bob' in names
        assert 'Charlie' not in names
    
    def test_execute_query_parameter_validation(self):
        """Test parameter validation during query execution."""
        self.db.queries.create_query(
            name='test_validation',
            query_text='SELECT * FROM users WHERE age >= :min_age AND status = :status',
            parameters={
                'min_age': {'type': 'integer', 'required': True},
                'status': {'type': 'text', 'required': True}
            }
        )
        
        # Missing required parameter
        with pytest.raises(ValueError, match="Required parameter"):
            self.db.queries.execute_query('test_validation', min_age=25)
        
        # Unexpected parameter
        with pytest.raises(ValueError, match="Unexpected parameters"):
            self.db.queries.execute_query('test_validation',
                                        min_age=25, status='active', extra_param='invalid')
        
        # Valid execution
        results = self.db.queries.execute_query('test_validation',
                                              min_age=25, status='active')
        assert len(results) == 2
    
    def test_delete_query_soft(self):
        """Test soft deleting a query."""
        self.db.queries.create_query(
            name='to_delete',
            query_text='SELECT * FROM users'
        )
        
        # Verify query exists
        assert self.db.queries.get_query('to_delete') is not None
        
        # Soft delete
        deleted = self.db.queries.delete_query('to_delete', hard_delete=False)
        assert deleted is True
        
        # Verify query is not found in normal listing
        assert self.db.queries.get_query('to_delete') is None
        
        # Verify query shows up in deleted listing
        all_queries = self.db.queries.list_queries(include_deleted=True)
        deleted_query = next((q for q in all_queries if q.name == 'to_delete'), None)
        assert deleted_query is not None
        assert deleted_query.deleted_at is not None
    
    def test_delete_query_hard(self):
        """Test hard deleting a query."""
        self.db.queries.create_query(
            name='to_hard_delete',
            query_text='SELECT * FROM users'
        )
        
        # Hard delete
        deleted = self.db.queries.delete_query('to_hard_delete', hard_delete=True)
        assert deleted is True
        
        # Verify query is completely gone
        assert self.db.queries.get_query('to_hard_delete') is None
        all_queries = self.db.queries.list_queries(include_deleted=True)
        assert not any(q.name == 'to_hard_delete' for q in all_queries)
    
    def test_delete_nonexistent_query(self):
        """Test deleting a non-existent query."""
        deleted = self.db.queries.delete_query('nonexistent')
        assert deleted is False
    
    def test_parameter_type_conversion(self):
        """Test parameter type conversion."""
        self.db.queries.create_query(
            name='type_test',
            query_text='SELECT * FROM users WHERE age = :age AND name = :user_name',
            parameters={
                'age': {'type': 'integer'},
                'user_name': {'type': 'text'}
            }
        )
        
        # Test type conversion
        results = self.db.queries.execute_query('type_test',
                                              age='25',  # String that should convert to int
                                              user_name='Alice')
        assert len(results) == 1
        assert results[0]['name'] == 'Alice'
    
    def test_complex_query_with_joins(self):
        """Test a complex query with joins."""
        self.db.queries.create_query(
            name='user_orders',
            query_text='''
                SELECT u.name, u.email, COUNT(o.id) as order_count, SUM(o.total) as total_spent
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id
                WHERE u.status = :status
                GROUP BY u.id, u.name, u.email
                HAVING COUNT(o.id) >= :min_orders
                ORDER BY total_spent DESC
            ''',
            parameters={
                'status': {'type': 'text', 'default': 'active'},
                'min_orders': {'type': 'integer', 'default': 0}
            }
        )
        
        results = self.db.queries.execute_query('user_orders', min_orders=1)
        assert len(results) >= 1
        # Alice should be first (higher total spent)
        assert results[0]['name'] == 'Alice'
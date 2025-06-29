"""Tests for safe SQL execution functionality."""

import pytest
import tempfile
import os
import synthdb


class TestSQLExecution:
    """Test the safe SQL execution features."""
    
    def setup_method(self):
        """Set up test database."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        # Create connection and setup test data
        self.db = synthdb.connect(self.db_path)
        self._setup_test_data()
    
    def teardown_method(self):
        """Clean up test database."""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass
    
    def _setup_test_data(self):
        """Create test tables and data."""
        # Create users table
        self.db.create_table('users')
        self.db.add_columns('users', {
            'name': 'text',
            'email': 'text',
            'age': 25,
            'active': True
        })
        
        # Insert test users
        self.db.insert('users', {'name': 'Alice', 'email': 'alice@example.com', 'age': 30, 'active': True})
        self.db.insert('users', {'name': 'Bob', 'email': 'bob@example.com', 'age': 25, 'active': False})
        self.db.insert('users', {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 35, 'active': True})
        
        # Create products table
        self.db.create_table('products')
        self.db.add_columns('products', {
            'name': 'text',
            'price': 19.99,
            'category': 'text',
            'stock': 100
        })
        
        # Insert test products
        self.db.insert('products', {'name': 'Widget A', 'price': 19.99, 'category': 'widgets', 'stock': 50})
        self.db.insert('products', {'name': 'Widget B', 'price': 29.99, 'category': 'widgets', 'stock': 30})
        self.db.insert('products', {'name': 'Gadget X', 'price': 49.99, 'category': 'gadgets', 'stock': 20})
    
    def test_simple_select(self):
        """Test basic SELECT query."""
        results = self.db.execute_sql("SELECT * FROM users")
        assert len(results) == 3
        assert all('name' in row and 'email' in row for row in results)
    
    def test_select_with_where(self):
        """Test SELECT with WHERE clause."""
        results = self.db.execute_sql("SELECT * FROM users WHERE age > 25")
        assert len(results) == 2
        assert all(row['age'] > 25 for row in results)
    
    def test_select_with_parameters(self):
        """Test parameterized queries."""
        results = self.db.execute_sql(
            "SELECT * FROM users WHERE age > ? AND active = ?",
            [25, 1]
        )
        assert len(results) == 2
        assert all(row['age'] > 25 and row['active'] == 1 for row in results)
    
    def test_aggregation_queries(self):
        """Test aggregation functions."""
        # COUNT
        results = self.db.execute_sql("SELECT COUNT(*) as total FROM users")
        assert results[0]['total'] == 3
        
        # AVG
        results = self.db.execute_sql("SELECT AVG(age) as avg_age FROM users")
        assert results[0]['avg_age'] == 30  # (30 + 25 + 35) / 3
        
        # GROUP BY
        results = self.db.execute_sql("""
            SELECT category, COUNT(*) as count, AVG(price) as avg_price
            FROM products
            GROUP BY category
            ORDER BY category
        """)
        assert len(results) == 2
        gadgets = next(r for r in results if r['category'] == 'gadgets')
        assert gadgets['count'] == 1
        assert gadgets['avg_price'] == 49.99
    
    def test_join_query(self):
        """Test JOIN operations."""
        # Create orders table
        self.db.create_table('orders')
        self.db.add_columns('orders', {
            'user_id': 'text',
            'product_name': 'text',
            'quantity': 1
        })
        
        # Get user IDs (using 'id' since aliasing is enabled by default)
        users = self.db.query('users')
        alice_id = next(u['id'] for u in users if u['name'] == 'Alice')
        
        # Insert order
        self.db.insert('orders', {
            'user_id': alice_id,
            'product_name': 'Widget A',
            'quantity': 2
        })
        
        # Test JOIN (using 'id' since aliasing is enabled)
        results = self.db.execute_sql("""
            SELECT u.name, o.product_name, o.quantity
            FROM users u
            JOIN orders o ON u.id = o.user_id
        """)
        assert len(results) == 1
        assert results[0]['name'] == 'Alice'
        assert results[0]['product_name'] == 'Widget A'
    
    def test_forbidden_operations(self):
        """Test that forbidden operations are blocked."""
        # INSERT
        with pytest.raises(ValueError, match="Forbidden operation: INSERT"):
            self.db.execute_sql("INSERT INTO users (name) VALUES ('Test')")
        
        # UPDATE
        with pytest.raises(ValueError, match="Forbidden operation: UPDATE"):
            self.db.execute_sql("UPDATE users SET name = 'Test'")
        
        # DELETE
        with pytest.raises(ValueError, match="Forbidden operation: DELETE"):
            self.db.execute_sql("DELETE FROM users")
        
        # DROP
        with pytest.raises(ValueError, match="Forbidden operation: DROP"):
            self.db.execute_sql("DROP TABLE users")
        
        # CREATE
        with pytest.raises(ValueError, match="Forbidden operation: CREATE"):
            self.db.execute_sql("CREATE TABLE test (id INTEGER)")
    
    def test_internal_table_access(self):
        """Test that internal tables cannot be accessed."""
        # Try to access internal tables
        with pytest.raises(ValueError, match="Access to internal table not allowed"):
            self.db.execute_sql("SELECT * FROM table_definitions")
        
        with pytest.raises(ValueError, match="Access to internal table not allowed"):
            self.db.execute_sql("SELECT * FROM column_definitions")
        
        with pytest.raises(ValueError, match="Access to internal table not allowed"):
            self.db.execute_sql("SELECT * FROM text_values")
    
    def test_non_select_queries(self):
        """Test that only SELECT queries are allowed."""
        with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
            self.db.execute_sql("EXPLAIN QUERY PLAN SELECT * FROM users")
    
    def test_multiple_statements(self):
        """Test that multiple statements are blocked."""
        with pytest.raises(ValueError, match="Multiple statements not allowed"):
            self.db.execute_sql("SELECT * FROM users; DROP TABLE users")
    
    def test_sql_comments(self):
        """Test that SQL comments are blocked."""
        with pytest.raises(ValueError, match="SQL comments not allowed"):
            self.db.execute_sql("SELECT * FROM users -- comment")
        
        with pytest.raises(ValueError, match="SQL comments not allowed"):
            self.db.execute_sql("SELECT * FROM users /* comment */")
    
    def test_case_insensitive_keywords(self):
        """Test that keywords are checked case-insensitively."""
        # Lower case forbidden operations
        with pytest.raises(ValueError, match="Forbidden operation"):
            self.db.execute_sql("insert into users (name) values ('test')")
        
        # Mixed case
        with pytest.raises(ValueError, match="Forbidden operation"):
            self.db.execute_sql("DeLeTe FROM users")
    
    def test_subqueries(self):
        """Test that subqueries work."""
        results = self.db.execute_sql("""
            SELECT name, age
            FROM users
            WHERE age > (SELECT AVG(age) FROM users)
        """)
        assert len(results) == 1
        assert results[0]['name'] == 'Charlie'
        assert results[0]['age'] == 35
    
    def test_limit_offset(self):
        """Test LIMIT and OFFSET clauses."""
        results = self.db.execute_sql("SELECT * FROM users ORDER BY name LIMIT 2")
        assert len(results) == 2
        
        results = self.db.execute_sql("SELECT * FROM users ORDER BY name LIMIT 1 OFFSET 1")
        assert len(results) == 1
        assert results[0]['name'] == 'Bob'  # Second in alphabetical order
    
    def test_empty_results(self):
        """Test queries that return no results."""
        results = self.db.execute_sql("SELECT * FROM users WHERE age > 100")
        assert results == []


class TestSQLKeywordValidation:
    """Test SQL keyword validation for table and column names."""
    
    def setup_method(self):
        """Set up test database."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_file.name
        self.temp_file.close()
        self.db = synthdb.connect(self.db_path)
    
    def teardown_method(self):
        """Clean up test database."""
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass
    
    def test_create_table_with_sql_keyword(self):
        """Test that tables can't be created with SQL keyword names."""
        # DDL keywords
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.create_table('CREATE')
        
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.create_table('DROP')
        
        # DML keywords
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.create_table('SELECT')
        
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.create_table('UPDATE')
        
        # Common keywords
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.create_table('TABLE')
        
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.create_table('FROM')
    
    def test_add_column_with_sql_keyword(self):
        """Test that columns can't be created with SQL keyword names."""
        self.db.create_table('test_table')
        
        # DDL keywords
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.add_column('test_table', 'ALTER', 'text')
        
        # DML keywords
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.add_column('test_table', 'INSERT', 'text')
        
        # Common keywords
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.add_column('test_table', 'WHERE', 'text')
        
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.add_column('test_table', 'COLUMN', 'text')
        
        # Type names
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.add_column('test_table', 'INTEGER', 'text')
    
    def test_case_insensitive_keyword_validation(self):
        """Test that keyword validation is case-insensitive."""
        # Lower case
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.create_table('select')
        
        # Mixed case
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.create_table('SeLeCt')
        
        # For columns
        self.db.create_table('test_table')
        with pytest.raises(ValueError, match="reserved SQL keyword"):
            self.db.add_column('test_table', 'where', 'text')
    
    def test_internal_table_name_validation(self):
        """Test that internal table names are blocked."""
        with pytest.raises(ValueError, match="conflicts with internal SynthDB tables"):
            self.db.create_table('table_definitions')
        
        with pytest.raises(ValueError, match="conflicts with internal SynthDB tables"):
            self.db.create_table('column_definitions')
        
        with pytest.raises(ValueError, match="conflicts with internal SynthDB tables"):
            self.db.create_table('text_values')
    
    def test_valid_names_allowed(self):
        """Test that valid names are allowed."""
        # These should work fine
        self.db.create_table('users')
        self.db.create_table('products_catalog')
        self.db.create_table('order_items')
        
        # Add columns with valid names
        self.db.add_column('users', 'first_name', 'text')
        self.db.add_column('users', 'email_address', 'text')
        self.db.add_column('users', 'is_active', 'integer')
        
        # Verify they were created
        tables = self.db.list_tables()
        table_names = [t['name'] for t in tables]
        assert 'users' in table_names
        assert 'products_catalog' in table_names
        assert 'order_items' in table_names
        
        columns = self.db.list_columns('users')
        column_names = [c['name'] for c in columns]
        assert 'first_name' in column_names
        assert 'email_address' in column_names
        assert 'is_active' in column_names
    
    def test_identifier_pattern_validation(self):
        """Test identifier pattern requirements."""
        # Must start with letter or underscore
        with pytest.raises(ValueError, match="must start with a letter or underscore"):
            self.db.create_table('123table')
        
        with pytest.raises(ValueError, match="must start with a letter or underscore"):
            self.db.create_table('!table')
        
        # Can contain numbers after first character
        self.db.create_table('table1')
        self.db.create_table('_private_table')
        
        # Special characters not allowed
        with pytest.raises(ValueError, match="must start with a letter or underscore"):
            self.db.create_table('table-name')
        
        with pytest.raises(ValueError, match="must start with a letter or underscore"):
            self.db.create_table('table.name')
    
    def test_length_validation(self):
        """Test identifier length limits."""
        # Max length is 64 characters
        long_name = 'a' * 65
        with pytest.raises(ValueError, match="name too long"):
            self.db.create_table(long_name)
        
        # 64 characters should work
        valid_long_name = 'a' * 64
        self.db.create_table(valid_long_name)
        
        # Test for columns too
        with pytest.raises(ValueError, match="name too long"):
            self.db.add_column(valid_long_name, 'b' * 65, 'text')
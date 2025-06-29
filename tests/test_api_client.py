"""Tests for API client functionality."""

import pytest
import tempfile
import os
import threading
import time
from unittest.mock import patch, MagicMock

import httpx

from synthdb.api_client import RemoteConnection, APIError, connect_remote


class TestAPIClient:
    """Test API client functionality."""
    
    def test_remote_connection_initialization(self):
        """Test RemoteConnection initialization."""
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        assert conn.base_url == "http://localhost:8000"
        assert conn.database_name == "test.db"
        assert conn.timeout == 30.0
        assert isinstance(conn.client, httpx.Client)
    
    def test_db_endpoint_generation(self):
        """Test database endpoint URL generation."""
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        assert conn._db_endpoint() == "/api/v1/databases/test.db"
        assert conn._db_endpoint("tables") == "/api/v1/databases/test.db/tables"
        assert conn._db_endpoint("/tables/users") == "/api/v1/databases/test.db/tables/users"
    
    @patch('httpx.Client.request')
    def test_successful_api_request(self, mock_request):
        """Test successful API request handling."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {"test": "data"},
            "error": None
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        result = conn._make_request('GET', '/test')
        
        assert result == {"test": "data"}
        mock_request.assert_called_once()
    
    @patch('httpx.Client.request')
    def test_api_error_handling(self, mock_request):
        """Test API error response handling."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "data": None,
            "error": {
                "code": "TABLE_NOT_FOUND",
                "message": "Table 'users' not found"
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        with pytest.raises(APIError) as exc_info:
            conn._make_request('GET', '/test')
        
        assert "Table 'users' not found" in str(exc_info.value)
        assert exc_info.value.status_code == 400
    
    @patch('httpx.Client.request')
    def test_http_error_handling(self, mock_request):
        """Test HTTP error handling."""
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Not found"}
        
        mock_request.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=mock_response
        )
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        with pytest.raises(APIError) as exc_info:
            conn._make_request('GET', '/test')
        
        assert exc_info.value.status_code == 404
    
    @patch('httpx.Client.request')
    def test_connection_error_handling(self, mock_request):
        """Test connection error handling."""
        # Mock connection error
        mock_request.side_effect = httpx.ConnectError("Connection failed")
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        with pytest.raises(APIError) as exc_info:
            conn._make_request('GET', '/test')
        
        assert "Connection error" in str(exc_info.value)
    
    @patch('httpx.Client.request')
    def test_database_operations(self, mock_request):
        """Test database operation methods."""
        # Mock successful responses
        def mock_request_side_effect(method, url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            if 'init' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"database": "test.db", "backend": "sqlite", "initialized": True}
                }
            elif 'info' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"database": "test.db", "tables_count": 2, "total_columns": 10}
                }
            
            return mock_response
        
        mock_request.side_effect = mock_request_side_effect
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        # Test init_db
        conn.init_db(backend="sqlite", force=True)
        
        # Test get_info
        info = conn.get_info()
        assert info["database"] == "test.db"
        assert info["tables_count"] == 2
    
    @patch('httpx.Client.request')
    def test_table_operations(self, mock_request):
        """Test table operation methods."""
        def mock_request_side_effect(method, url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            if method == 'POST' and 'tables' in url and not any(sub in url for sub in ['columns', 'rows']):
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"table_id": 1, "table_name": "users", "columns": []}
                }
            elif method == 'GET' and 'tables' in url and url.endswith('tables'):
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"tables": [{"name": "users"}, {"name": "posts"}]}
                }
            elif method == 'DELETE' and 'tables' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"table_name": "users", "deleted": True}
                }
            
            return mock_response
        
        mock_request.side_effect = mock_request_side_effect
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        # Test create_table
        table_id = conn.create_table("users")
        assert table_id == 1
        
        # Test list_tables
        tables = conn.list_tables()
        assert len(tables) == 2
        assert tables[0]["name"] == "users"
        
        # Test delete_table
        conn.delete_table("users", hard_delete=True)
    
    @patch('httpx.Client.request')
    def test_data_operations(self, mock_request):
        """Test data operation methods."""
        def mock_request_side_effect(method, url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            if method == 'POST' and 'rows' in url and not 'bulk' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"id": "user-123", "inserted": True}
                }
            elif method == 'GET' and 'rows' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"rows": [{"id": "user-123", "name": "Alice"}]}
                }
            elif method == 'PUT' and 'rows' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"id": "user-123", "upserted": True}
                }
            elif method == 'DELETE' and 'rows' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"id": "user-123", "deleted": True}
                }
            
            return mock_response
        
        mock_request.side_effect = mock_request_side_effect
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        # Test insert
        user_id = conn.insert("users", {"name": "Alice", "age": 25})
        assert user_id == "user-123"
        
        # Test query
        rows = conn.query("users", "age > 20")
        assert len(rows) == 1
        assert rows[0]["name"] == "Alice"
        
        # Test upsert
        updated_id = conn.upsert("users", {"name": "Alice Updated"}, "user-123")
        assert updated_id == "user-123"
        
        # Test delete_row
        deleted = conn.delete_row("users", "user-123")
        assert deleted is True
    
    @patch('httpx.Client.request')
    def test_sql_execution(self, mock_request):
        """Test SQL query execution."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "results": [{"name": "Alice", "age": 25}],
                "rows_returned": 1
            }
        }
        mock_request.return_value = mock_response
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        results = conn.execute_sql("SELECT * FROM users WHERE age > ?", [20])
        assert len(results) == 1
        assert results[0]["name"] == "Alice"
    
    @patch('httpx.Client.request')
    def test_saved_queries_operations(self, mock_request):
        """Test saved queries operations."""
        def mock_request_side_effect(method, url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            if method == 'POST' and 'queries' in url and not 'execute' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"id": 1, "name": "test_query", "created": True}
                }
            elif method == 'GET' and 'queries' in url and url.endswith('queries'):
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"queries": [{"name": "test_query", "id": 1}]}
                }
            elif method == 'POST' and 'execute' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"results": [{"count": 5}], "rows_returned": 1}
                }
            
            return mock_response
        
        mock_request.side_effect = mock_request_side_effect
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        # Test create query
        result = conn.queries.create_query(
            "test_query",
            "SELECT COUNT(*) FROM users"
        )
        assert result["name"] == "test_query"
        
        # Test list queries
        queries = conn.queries.list_queries()
        assert len(queries) == 1
        assert queries[0]["name"] == "test_query"
        
        # Test execute query
        results = conn.queries.execute_query("test_query")
        assert len(results) == 1
        assert results[0]["count"] == 5
    
    def test_context_manager(self):
        """Test RemoteConnection as context manager."""
        with patch('httpx.Client.close') as mock_close:
            with RemoteConnection("http://localhost:8000", "test.db") as conn:
                assert isinstance(conn, RemoteConnection)
            
            mock_close.assert_called_once()
    
    def test_connect_remote_factory(self):
        """Test the connect_remote factory function."""
        conn = connect_remote("http://localhost:8000", "test.db", timeout=60.0)
        
        assert isinstance(conn, RemoteConnection)
        assert conn.base_url == "http://localhost:8000"
        assert conn.database_name == "test.db"
        assert conn.timeout == 60.0
    
    def test_api_error_with_response_data(self):
        """Test APIError with response data."""
        response_data = {
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": "Invalid data"},
            "metadata": {"timestamp": "2024-01-01T00:00:00Z"}
        }
        
        error = APIError("Test error", status_code=400, response_data=response_data)
        
        assert str(error) == "Test error"
        assert error.status_code == 400
        assert error.response_data == response_data
    
    @patch('httpx.Client.request')
    def test_bulk_insert(self, mock_request):
        """Test bulk insert functionality."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "inserted_ids": ["user-1", "user-2", "user-3"],
                "rows_inserted": 3
            }
        }
        mock_request.return_value = mock_response
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        data = [
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 30},
            {"name": "Charlie", "age": 35}
        ]
        
        ids = conn.insert_bulk("users", data)
        assert len(ids) == 3
        assert ids[0] == "user-1"
    
    @patch('httpx.Client.request')
    def test_column_operations(self, mock_request):
        """Test column operation methods."""
        def mock_request_side_effect(method, url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            if method == 'POST' and 'columns' in url and not 'bulk' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"column_id": 1, "column_name": "email"}
                }
            elif method == 'POST' and 'bulk' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"column_ids": {"email": 1, "phone": 2}}
                }
            elif method == 'GET' and 'columns' in url:
                mock_response.json.return_value = {
                    "success": True,
                    "data": {"columns": [{"name": "email", "type": "text"}]}
                }
            
            return mock_response
        
        mock_request.side_effect = mock_request_side_effect
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        # Test add_column
        column_id = conn.add_column("users", "email", "text")
        assert column_id == 1
        
        # Test add_columns (bulk)
        column_ids = conn.add_columns("users", {"email": "text", "phone": "text"})
        assert column_ids["email"] == 1
        assert column_ids["phone"] == 2
        
        # Test list_columns
        columns = conn.list_columns("users")
        assert len(columns) == 1
        assert columns[0]["name"] == "email"
    
    @patch('httpx.Client.request')
    def test_error_response_handling_variations(self, mock_request):
        """Test various error response formats."""
        # Test error response without detail field
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = Exception("Invalid JSON")
        
        mock_request.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error", request=MagicMock(), response=mock_response
        )
        
        conn = RemoteConnection("http://localhost:8000", "test.db")
        
        with pytest.raises(APIError) as exc_info:
            conn._make_request('GET', '/test')
        
        assert "500 Internal Server Error" in str(exc_info.value)
    
    def test_repr(self):
        """Test string representation of RemoteConnection."""
        conn = RemoteConnection("http://localhost:8000", "test.db")
        repr_str = repr(conn)
        
        assert "RemoteConnection" in repr_str
        assert "http://localhost:8000" in repr_str
        assert "test.db" in repr_str
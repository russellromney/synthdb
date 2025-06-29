"""API client for SynthDB remote connections."""

import json
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin

import httpx

from .models import SynthDBModel, ModelGenerator, extend_connection_with_models


class APIError(Exception):
    """Exception raised for API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class RemoteConnection:
    """Remote connection to SynthDB API server."""
    
    def __init__(self, base_url: str, database_name: str, timeout: float = 30.0):
        """Initialize remote connection.
        
        Args:
            base_url: Base URL of the API server (e.g., "http://localhost:8000")
            database_name: Name of the database to connect to
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.database_name = database_name
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
        self._model_generator = None
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to the API."""
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        try:
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('success', True):
                error_info = data.get('error', {})
                raise APIError(
                    error_info.get('message', 'Unknown API error'),
                    response.status_code,
                    data
                )
            
            return data.get('data', {})
            
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_msg = error_data.get('detail', str(e))
            except:
                error_msg = str(e)
            raise APIError(error_msg, e.response.status_code)
        except httpx.RequestError as e:
            raise APIError(f"Connection error: {e}")
    
    def _db_endpoint(self, path: str = '') -> str:
        """Get database-specific endpoint."""
        base = f"/api/v1/databases/{self.database_name}"
        return base + ('/' + path.lstrip('/') if path else '')
    
    # Database operations
    def init_db(self, backend: str = 'sqlite', force: bool = False) -> None:
        """Initialize the database."""
        self._make_request(
            'POST',
            '/api/v1/databases/init',
            params={'db_name': self.database_name},
            json={'backend': backend, 'force': force}
        )
    
    def get_info(self) -> Dict[str, Any]:
        """Get database information."""
        return self._make_request('GET', self._db_endpoint('info'))
    
    # Table operations
    def create_table(self, name: str, columns: Optional[List[Dict[str, Any]]] = None) -> int:
        """Create a new table."""
        result = self._make_request(
            'POST',
            self._db_endpoint('tables'),
            json={'table_name': name, 'columns': columns or []}
        )
        return result['table_id']
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List all tables."""
        result = self._make_request('GET', self._db_endpoint('tables'))
        return result['tables']
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get table information."""
        return self._make_request('GET', self._db_endpoint(f'tables/{table_name}'))
    
    def delete_table(self, table_name: str, hard_delete: bool = False) -> None:
        """Delete a table."""
        self._make_request(
            'DELETE',
            self._db_endpoint(f'tables/{table_name}'),
            params={'hard_delete': hard_delete}
        )
    
    # Column operations
    def add_column(self, table_name: str, column_name: str, data_type: str) -> int:
        """Add a column to a table."""
        result = self._make_request(
            'POST',
            self._db_endpoint(f'tables/{table_name}/columns'),
            json={'column_name': column_name, 'data_type': data_type}
        )
        return result['column_id']
    
    def add_columns(self, table_name: str, columns: Dict[str, Union[str, Any]]) -> Dict[str, int]:
        """Add multiple columns to a table."""
        result = self._make_request(
            'POST',
            self._db_endpoint(f'tables/{table_name}/columns/bulk'),
            json={'columns': columns}
        )
        return result['column_ids']
    
    def list_columns(self, table_name: str, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """List columns in a table."""
        result = self._make_request(
            'GET',
            self._db_endpoint(f'tables/{table_name}/columns'),
            params={'include_deleted': include_deleted}
        )
        return result['columns']
    
    def delete_column(self, table_name: str, column_name: str, hard_delete: bool = False) -> None:
        """Delete a column from a table."""
        self._make_request(
            'DELETE',
            self._db_endpoint(f'tables/{table_name}/columns/{column_name}'),
            params={'hard_delete': hard_delete}
        )
    
    # Data operations
    def insert(self, table_name: str, data: Union[Dict[str, Any], str], 
               value: Optional[Any] = None, force_type: Optional[str] = None, 
               id: Optional[str] = None) -> str:
        """Insert data into a table."""
        result = self._make_request(
            'POST',
            self._db_endpoint(f'tables/{table_name}/rows'),
            json={
                'data': data,
                'value': value,
                'force_type': force_type,
                'id': id
            }
        )
        return result['id']
    
    def insert_bulk(self, table_name: str, data: List[Dict[str, Any]], 
                   infer_types: bool = True) -> List[str]:
        """Insert multiple rows into a table."""
        result = self._make_request(
            'POST',
            self._db_endpoint(f'tables/{table_name}/rows/bulk'),
            json={'data': data, 'infer_types': infer_types}
        )
        return result['inserted_ids']
    
    def query(self, table_name: str, where: Optional[str] = None, 
             limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Query data from a table."""
        params = {'limit': limit, 'offset': offset}
        if where:
            params['where'] = where
        
        result = self._make_request(
            'GET',
            self._db_endpoint(f'tables/{table_name}/rows'),
            params=params
        )
        return result['rows']
    
    def get_row(self, table_name: str, row_id: str) -> Dict[str, Any]:
        """Get a specific row by ID."""
        result = self._make_request(
            'GET',
            self._db_endpoint(f'tables/{table_name}/rows/{row_id}')
        )
        return result['row']
    
    def upsert(self, table_name: str, data: Dict[str, Any], id: str) -> str:
        """Update or insert a row."""
        result = self._make_request(
            'PUT',
            self._db_endpoint(f'tables/{table_name}/rows'),
            json={'data': data, 'id': id}
        )
        return result['id']
    
    def delete_row(self, table_name: str, row_id: str) -> bool:
        """Delete a row."""
        try:
            self._make_request(
                'DELETE',
                self._db_endpoint(f'tables/{table_name}/rows/{row_id}')
            )
            return True
        except APIError as e:
            if e.status_code == 404:
                return False
            raise
    
    # SQL execution
    def execute_sql(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query."""
        result = self._make_request(
            'POST',
            self._db_endpoint('sql'),
            json={'sql': sql, 'params': params}
        )
        return result['results']
    
    # Saved queries (requires API server to support saved queries)
    @property
    def queries(self):
        """Access saved queries functionality."""
        if not hasattr(self, '_queries'):
            self._queries = RemoteSavedQueries(self)
        return self._queries
    
    # Model support
    def generate_models(self) -> Dict[str, type]:
        """Generate models for all tables (requires models module)."""
        if not self._model_generator:
            self._model_generator = ModelGenerator(self)
        return self._model_generator.generate_all_models()
    
    def generate_model(self, table_name: str) -> type:
        """Generate a model for a specific table."""
        if not self._model_generator:
            self._model_generator = ModelGenerator(self)
        return self._model_generator.generate_model(table_name)
    
    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __repr__(self) -> str:
        return f"RemoteConnection({self.base_url}, database={self.database_name})"


class RemoteSavedQueries:
    """Remote saved queries client."""
    
    def __init__(self, connection: RemoteConnection):
        self.connection = connection
    
    def list_queries(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """List all saved queries."""
        result = self.connection._make_request(
            'GET',
            self.connection._db_endpoint('queries'),
            params={'include_deleted': include_deleted}
        )
        return result['queries']
    
    def create_query(self, name: str, query_text: str, 
                    description: Optional[str] = None,
                    parameters: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Create a new saved query."""
        return self.connection._make_request(
            'POST',
            self.connection._db_endpoint('queries'),
            json={
                'name': name,
                'query_text': query_text,
                'description': description,
                'parameters': parameters
            }
        )
    
    def get_query(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a saved query by name."""
        try:
            result = self.connection._make_request(
                'GET',
                self.connection._db_endpoint(f'queries/{name}')
            )
            return result['query']
        except APIError as e:
            if e.status_code == 404:
                return None
            raise
    
    def execute_query(self, name: str, **params) -> List[Dict[str, Any]]:
        """Execute a saved query."""
        result = self.connection._make_request(
            'POST',
            self.connection._db_endpoint(f'queries/{name}/execute'),
            json={'parameters': params}
        )
        return result['results']
    
    def delete_query(self, name: str, hard_delete: bool = False) -> bool:
        """Delete a saved query."""
        try:
            self.connection._make_request(
                'DELETE',
                self.connection._db_endpoint(f'queries/{name}'),
                params={'hard_delete': hard_delete}
            )
            return True
        except APIError as e:
            if e.status_code == 404:
                return False
            raise


# Connection factory function
def connect_remote(base_url: str, database_name: str, timeout: float = 30.0) -> RemoteConnection:
    """Create a remote connection to SynthDB API server.
    
    Args:
        base_url: Base URL of the API server (e.g., "http://localhost:8000")
        database_name: Name of the database to connect to
        timeout: Request timeout in seconds
        
    Returns:
        RemoteConnection instance
        
    Example:
        db = connect_remote("http://localhost:8000", "myapp.db")
        tables = db.list_tables()
    """
    connection = RemoteConnection(base_url, database_name, timeout)
    
    # Extend with model functionality if available
    try:
        extend_connection_with_models(connection)
    except:
        # Models functionality not available, continue without it
        pass
    
    return connection
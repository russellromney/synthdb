"""Saved queries functionality for SynthDB."""

import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from .backends import get_backend
from .config import config


@dataclass
class QueryParameter:
    """Represents a parameter for a saved query."""
    name: str
    data_type: str  # 'text', 'integer', 'real', 'timestamp'
    default_value: Optional[str] = None
    is_required: bool = True
    description: Optional[str] = None


@dataclass
class SavedQuery:
    """Represents a saved query definition."""
    id: int
    name: str
    query_text: str
    description: Optional[str] = None
    parameters: List[QueryParameter] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []


class QueryManager:
    """Manages saved queries in SynthDB."""
    
    def __init__(self, db_path: str, backend_name: Optional[str] = None):
        self.db_path = db_path
        self.backend_name = backend_name or config.get_backend_for_path(db_path)
        self.backend = get_backend(self.backend_name)
    
    def create_query(self, name: str, query_text: str, 
                    description: Optional[str] = None,
                    parameters: Optional[Dict[str, Dict[str, Any]]] = None) -> SavedQuery:
        """
        Create a new saved query.
        
        Args:
            name: Unique name for the query
            query_text: SQL query text with parameter placeholders (:param_name)
            description: Optional description
            parameters: Dict of parameter definitions
            
        Returns:
            SavedQuery object
            
        Examples:
            manager.create_query(
                name="high_value_customers",
                query_text='''
                    SELECT c.id, c.name, SUM(o.total) as lifetime_value
                    FROM customers c
                    JOIN orders o ON c.id = o.customer_id
                    WHERE o.status = 'completed'
                    GROUP BY c.id, c.name
                    HAVING SUM(o.total) > :min_value
                ''',
                parameters={
                    "min_value": {
                        "type": "real",
                        "default": 1000.0,
                        "description": "Minimum lifetime value"
                    }
                }
            )
        """
        # Validate query name
        if not self._is_valid_name(name):
            raise ValueError(f"Invalid query name: {name}")
        
        # Check if query already exists
        if self._query_exists(name):
            raise ValueError(f"Query '{name}' already exists")
        
        # Validate SQL syntax
        self._validate_query_syntax(query_text)
        
        # Parse parameters from query text
        detected_params = self._extract_parameters(query_text)
        param_defs = self._normalize_parameters(parameters or {}, detected_params)
        
        # Extract dependencies
        dependencies = self._extract_dependencies(query_text)
        
        # Create the saved query
        db = self.backend.connect(self.db_path)
        try:
            # Insert query definition
            query_id = self._insert_query_definition(
                db, name, query_text, description
            )
            
            # Insert parameters
            for param in param_defs:
                self._insert_parameter(db, query_id, param)
            
            # Insert dependencies
            for dep_type, dep_names in dependencies.items():
                for dep_name in dep_names:
                    self._insert_dependency(db, query_id, dep_type, dep_name)
            
            self.backend.commit(db)
            
            return SavedQuery(
                id=query_id,
                name=name,
                query_text=query_text,
                description=description,
                parameters=param_defs
            )
        finally:
            self.backend.close(db)
    
    def get_query(self, name: str) -> Optional[SavedQuery]:
        """Get a saved query by name."""
        db = self.backend.connect(self.db_path)
        try:
            # Get query definition
            cur = self.backend.execute(db, """
                SELECT id, name, description, query_text, created_at, updated_at, deleted_at
                FROM saved_queries 
                WHERE name = ? AND deleted_at IS NULL
            """, (name,))
            
            row = self.backend.fetchone(cur)
            if not row:
                return None
            
            # Get parameters
            params_cur = self.backend.execute(db, """
                SELECT name, data_type, default_value, is_required, description
                FROM query_parameters
                WHERE query_id = ?
                ORDER BY name
            """, (row['id'],))
            
            param_rows = self.backend.fetchall(params_cur)
            parameters = [
                QueryParameter(
                    name=p['name'],
                    data_type=p['data_type'],
                    default_value=p['default_value'],
                    is_required=bool(p['is_required']),
                    description=p['description']
                )
                for p in param_rows
            ]
            
            return SavedQuery(
                id=row['id'],
                name=row['name'],
                query_text=row['query_text'],
                description=row['description'],
                parameters=parameters,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                deleted_at=row['deleted_at']
            )
        finally:
            self.backend.close(db)
    
    def list_queries(self, include_deleted: bool = False) -> List[SavedQuery]:
        """List all saved queries."""
        db = self.backend.connect(self.db_path)
        try:
            where_clause = "" if include_deleted else "WHERE deleted_at IS NULL"
            cur = self.backend.execute(db, f"""
                SELECT id, name, description, query_text, created_at, updated_at, deleted_at
                FROM saved_queries
                {where_clause}
                ORDER BY name
            """)
            
            rows = self.backend.fetchall(cur)
            queries = []
            
            for row in rows:
                # Get parameters for each query
                params_cur = self.backend.execute(db, """
                    SELECT name, data_type, default_value, is_required, description
                    FROM query_parameters
                    WHERE query_id = ?
                    ORDER BY name
                """, (row['id'],))
                
                param_rows = self.backend.fetchall(params_cur)
                parameters = [
                    QueryParameter(
                        name=p['name'],
                        data_type=p['data_type'],
                        default_value=p['default_value'],
                        is_required=bool(p['is_required']),
                        description=p['description']
                    )
                    for p in param_rows
                ]
                
                queries.append(SavedQuery(
                    id=row['id'],
                    name=row['name'],
                    query_text=row['query_text'],
                    description=row['description'],
                    parameters=parameters,
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    deleted_at=row['deleted_at']
                ))
            
            return queries
        finally:
            self.backend.close(db)
    
    def execute_query(self, name: str, **params) -> List[Dict[str, Any]]:
        """
        Execute a saved query with parameters.
        
        Args:
            name: Name of the saved query
            **params: Parameter values
            
        Returns:
            List of result dictionaries
        """
        query_def = self.get_query(name)
        if not query_def:
            raise ValueError(f"Query '{name}' not found")
        
        # Validate and bind parameters
        final_params = self._validate_and_bind_parameters(query_def, params)
        
        # Execute the query with parameters
        final_query = self._bind_parameters(query_def.query_text, final_params)
        
        db = self.backend.connect(self.db_path)
        try:
            cur = self.backend.execute(db, final_query)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = self.backend.fetchall(cur)
            
            # Convert to list of dicts
            results = []
            for row in rows:
                if hasattr(row, 'keys'):
                    results.append(dict(row))
                else:
                    results.append(dict(zip(columns, row)))
            
            return results
        finally:
            self.backend.close(db)
    
    def delete_query(self, name: str, hard_delete: bool = False) -> bool:
        """
        Delete a saved query.
        
        Args:
            name: Name of the query to delete
            hard_delete: If True, permanently delete; if False, soft delete
            
        Returns:
            True if query was deleted, False if not found
        """
        query_def = self.get_query(name)
        if not query_def:
            return False
        
        db = self.backend.connect(self.db_path)
        try:
            if hard_delete:
                # Delete from database
                self.backend.execute(db, "DELETE FROM saved_queries WHERE id = ?", (query_def.id,))
            else:
                # Soft delete
                now = datetime.now().isoformat()
                self.backend.execute(db, 
                    "UPDATE saved_queries SET deleted_at = ? WHERE id = ?", 
                    (now, query_def.id)
                )
            
            self.backend.commit(db)
            return True
        finally:
            self.backend.close(db)
    
    
    # Private methods
    
    def _is_valid_name(self, name: str) -> bool:
        """Validate query name."""
        if not name or not isinstance(name, str):
            return False
        # Allow letters, numbers, underscores, and hyphens
        return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name))
    
    def _query_exists(self, name: str) -> bool:
        """Check if query name already exists."""
        db = self.backend.connect(self.db_path)
        try:
            cur = self.backend.execute(db, 
                "SELECT 1 FROM saved_queries WHERE name = ? AND deleted_at IS NULL", 
                (name,)
            )
            return self.backend.fetchone(cur) is not None
        finally:
            self.backend.close(db)
    
    def _validate_query_syntax(self, query_text: str) -> None:
        """Basic validation of query syntax."""
        if not query_text or not query_text.strip():
            raise ValueError("Query text cannot be empty")
        
        # Ensure it's a SELECT query
        cleaned = query_text.strip().upper()
        if not cleaned.startswith('SELECT'):
            raise ValueError("Only SELECT queries are supported")
        
        # Check for dangerous keywords
        dangerous = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE']
        for keyword in dangerous:
            if re.search(rf'\b{keyword}\b', cleaned):
                raise ValueError(f"Query contains forbidden keyword: {keyword}")
    
    def _extract_parameters(self, query_text: str) -> Set[str]:
        """Extract parameter names from query text."""
        # Find all :parameter_name patterns
        pattern = r':([a-zA-Z_][a-zA-Z0-9_]*)'
        return set(re.findall(pattern, query_text))
    
    def _normalize_parameters(self, param_defs: Dict[str, Dict[str, Any]], 
                            detected_params: Set[str]) -> List[QueryParameter]:
        """Normalize parameter definitions."""
        parameters = []
        
        for param_name in detected_params:
            if param_name in param_defs:
                definition = param_defs[param_name]
                # If 'required' is explicitly set, use that; otherwise, required if no default value
                has_default = 'default' in definition
                is_required = definition.get('required', not has_default)
                
                parameters.append(QueryParameter(
                    name=param_name,
                    data_type=definition.get('type', 'text'),
                    default_value=str(definition['default']) if 'default' in definition else None,
                    is_required=is_required,
                    description=definition.get('description')
                ))
            else:
                # Auto-detect parameter with defaults
                parameters.append(QueryParameter(
                    name=param_name,
                    data_type='text',
                    is_required=True
                ))
        
        return parameters
    
    def _extract_dependencies(self, query_text: str) -> Dict[str, Set[str]]:
        """Extract table dependencies from query text."""
        dependencies = {
            'tables': set(),
            'queries': set()
        }
        
        # Simple pattern to find table names after FROM and JOIN
        # This is a basic implementation - a full SQL parser would be more robust
        from_pattern = r'\bFROM\s+(\w+)'
        join_pattern = r'\bJOIN\s+(\w+)'
        
        for pattern in [from_pattern, join_pattern]:
            matches = re.findall(pattern, query_text, re.IGNORECASE)
            for match in matches:
                # Check if it's a saved query (this would need a lookup)
                # For now, assume all are tables
                dependencies['tables'].add(match.lower())
        
        return dependencies
    
    def _insert_query_definition(self, db, name: str, query_text: str, 
                                description: Optional[str]) -> int:
        """Insert query definition and return ID."""
        now = datetime.now().isoformat()
        cur = self.backend.execute(db, """
            INSERT INTO saved_queries 
            (name, description, query_text, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (name, description, query_text, now, now))
        
        return cur.lastrowid
    
    def _insert_parameter(self, db, query_id: int, param: QueryParameter) -> None:
        """Insert parameter definition."""
        self.backend.execute(db, """
            INSERT INTO query_parameters 
            (query_id, name, data_type, default_value, is_required, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (query_id, param.name, param.data_type, param.default_value, 
              param.is_required, param.description))
    
    def _insert_dependency(self, db, query_id: int, dep_type: str, dep_name: str) -> None:
        """Insert dependency record."""
        if dep_type == 'tables':
            self.backend.execute(db, """
                INSERT INTO query_dependencies (query_id, depends_on_table)
                VALUES (?, ?)
            """, (query_id, dep_name))
        elif dep_type == 'queries':
            self.backend.execute(db, """
                INSERT INTO query_dependencies (query_id, depends_on_query)
                VALUES (?, ?)
            """, (query_id, dep_name))
    
    def _validate_and_bind_parameters(self, query_def: SavedQuery, 
                                    params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters and apply defaults."""
        final_params = {}
        
        # Check all required parameters are provided
        for param in query_def.parameters:
            if param.name in params:
                # Validate type and convert
                final_params[param.name] = self._convert_parameter_value(
                    params[param.name], param.data_type
                )
            elif param.default_value is not None:
                # Use default value
                final_params[param.name] = self._convert_parameter_value(
                    param.default_value, param.data_type
                )
            elif param.is_required:
                raise ValueError(f"Required parameter '{param.name}' not provided")
        
        # Check for unexpected parameters
        param_names = {p.name for p in query_def.parameters}
        unexpected = set(params.keys()) - param_names
        if unexpected:
            raise ValueError(f"Unexpected parameters: {', '.join(unexpected)}")
        
        return final_params
    
    def _convert_parameter_value(self, value: Any, data_type: str) -> Any:
        """Convert parameter value to appropriate type."""
        if value is None:
            return None
        
        try:
            if data_type == 'integer':
                return int(value)
            elif data_type == 'real':
                return float(value)
            elif data_type == 'text':
                return str(value)
            elif data_type == 'timestamp':
                # Accept various timestamp formats
                if isinstance(value, str):
                    return value  # Assume it's already in correct format
                return str(value)
            else:
                return str(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert '{value}' to {data_type}: {e}")
    
    def _bind_parameters(self, query_text: str, params: Dict[str, Any]) -> str:
        """Bind parameters to query text."""
        result = query_text
        for name, value in params.items():
            placeholder = f":{name}"
            # Simple string replacement - proper implementation would use SQL parameter binding
            if isinstance(value, str):
                escaped_value = value.replace("'", "''")  # Basic SQL escaping
                result = result.replace(placeholder, f"'{escaped_value}'")
            elif value is None:
                result = result.replace(placeholder, "NULL")
            else:
                result = result.replace(placeholder, str(value))
        
        return result
    

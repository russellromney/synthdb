"""SQL validation and safety utilities for SynthDB."""

import re
from typing import List, Tuple, Optional, Dict, Any, Set
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of SQL validation."""
    is_safe: bool
    errors: List[str]
    warnings: List[str] = field(default_factory=list)


class SQLValidator:
    """Validates SQL queries and identifiers for safety."""
    
    # Core SQL keywords that should not be used as identifiers
    # This is a limited set of the most problematic keywords
    RESERVED_KEYWORDS = {
        # DDL operations
        'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'RENAME',
        # DML operations  
        'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'REPLACE',
        # DCL operations
        'GRANT', 'REVOKE', 
        # TCL operations
        'COMMIT', 'ROLLBACK', 'SAVEPOINT',
        # Common keywords that would cause confusion
        'SELECT', 'FROM', 'WHERE', 'TABLE', 'COLUMN',
        'INDEX', 'VIEW', 'TRIGGER', 'DATABASE', 'SCHEMA',
        'AND', 'OR', 'NOT', 'NULL', 'CONSTRAINT', 'KEY',
        'PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK', 'DEFAULT',
        'ORDER', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET',
        'JOIN', 'INNER', 'OUTER', 'LEFT', 'RIGHT', 'CROSS',
        'UNION', 'EXCEPT', 'INTERSECT', 'ALL', 'ANY', 'EXISTS',
        # Type names
        'INTEGER', 'TEXT', 'REAL', 'BLOB', 'NUMERIC',
        # SQLite specific
        'PRAGMA', 'ATTACH', 'DETACH', 'VACUUM', 'ANALYZE',
        # SynthDB internal
        'ID'
    }
    
    # Operations that are not allowed in user queries
    FORBIDDEN_OPERATIONS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE',
        'ALTER', 'TRUNCATE', 'GRANT', 'REVOKE', 'COMMIT',
        'ROLLBACK', 'SAVEPOINT', 'PRAGMA', 'ATTACH', 'DETACH',
        'VACUUM', 'ANALYZE', 'REPLACE', 'MERGE'
    }
    
    # SynthDB internal tables that should not be accessed directly
    INTERNAL_TABLES = {
        'table_definitions', 'column_definitions', 'row_metadata',
        'text_values', 'integer_values', 'real_values', 'timestamp_values',
        'deleted_rows', 'deleted_columns'
    }
    
    # Pattern for valid identifier names
    IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    
    # Maximum identifier length
    MAX_IDENTIFIER_LENGTH = 64
    
    def validate_identifier(self, name: str, identifier_type: str = "identifier") -> ValidationResult:
        """Validate a table or column name.
        
        Args:
            name: The identifier to validate
            identifier_type: Type of identifier (table/column) for error messages
            
        Returns:
            ValidationResult with any errors or warnings
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        # Check if empty
        if not name:
            errors.append(f"{identifier_type} name cannot be empty")
            return ValidationResult(False, errors, warnings)
        
        # Check length
        if len(name) > self.MAX_IDENTIFIER_LENGTH:
            errors.append(f"{identifier_type} name too long (max {self.MAX_IDENTIFIER_LENGTH} characters)")
        
        # Check pattern
        if not self.IDENTIFIER_PATTERN.match(name):
            errors.append(f"{identifier_type} name must start with a letter or underscore and contain only letters, numbers, and underscores")
        
        # Check reserved keywords
        if name.upper() in self.RESERVED_KEYWORDS:
            errors.append(f"{identifier_type} name '{name}' is a reserved SQL keyword")
        
        # Check internal table names
        if name.lower() in self.INTERNAL_TABLES:
            errors.append(f"{identifier_type} name '{name}' conflicts with internal SynthDB tables")
        
        # Warnings for potentially confusing names
        if name.lower() in {'id', 'rowid', 'oid', '_rowid_'}:
            warnings.append(f"{identifier_type} name '{name}' might be confused with SQLite's internal row identifiers")
        
        if name.startswith('_') and name.endswith('_'):
            warnings.append(f"{identifier_type} name '{name}' with double underscores might be reserved for future use")
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    def validate_table_name(self, name: str) -> ValidationResult:
        """Validate a table name."""
        return self.validate_identifier(name, "Table")
    
    def validate_column_name(self, name: str) -> ValidationResult:
        """Validate a column name."""
        return self.validate_identifier(name, "Column")
    
    def validate_query(self, sql: str) -> ValidationResult:
        """Validate a SQL query for safe execution.
        
        Args:
            sql: The SQL query to validate
            
        Returns:
            ValidationResult with any errors or warnings
        """
        errors = []
        warnings = []
        
        # Normalize SQL for checking
        sql_upper = sql.upper()
        sql_tokens = re.split(r'\s+', sql_upper)
        
        # Check for forbidden operations
        for token in sql_tokens:
            if token in self.FORBIDDEN_OPERATIONS:
                errors.append(f"Forbidden operation: {token}")
        
        # Check for internal table access
        # Simple pattern matching - a full parser would be more robust
        from_pattern = re.compile(r'FROM\s+(\w+)', re.IGNORECASE)
        join_pattern = re.compile(r'JOIN\s+(\w+)', re.IGNORECASE)
        
        tables = []
        tables.extend(from_pattern.findall(sql))
        tables.extend(join_pattern.findall(sql))
        
        for table in tables:
            if table.lower() in self.INTERNAL_TABLES:
                errors.append(f"Access to internal table not allowed: {table}")
        
        # Check if it's a SELECT query
        if not sql_upper.strip().startswith('SELECT'):
            errors.append("Only SELECT queries are allowed")
        
        # Check for dangerous patterns
        dangerous_patterns = [
            (r';\s*\w+', "Multiple statements not allowed"),
            (r'--[^\n]*\n?', "SQL comments not allowed"),
            (r'/\*.*?\*/', "SQL comments not allowed"),
        ]
        
        for pattern, message in dangerous_patterns:
            if re.search(pattern, sql, re.IGNORECASE | re.DOTALL):
                errors.append(message)
        
        # Warnings for potentially expensive operations
        if 'CROSS JOIN' in sql_upper:
            warnings.append("CROSS JOIN may result in large result sets")
        
        if not any(word in sql_upper for word in ['WHERE', 'LIMIT']):
            warnings.append("Query has no WHERE clause or LIMIT - may return large result sets")
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    def sanitize_identifier(self, name: str) -> str:
        """Sanitize an identifier by escaping it properly.
        
        Args:
            name: The identifier to sanitize
            
        Returns:
            Properly quoted identifier safe for SQL
        """
        # Replace any quotes in the name with escaped quotes
        escaped = name.replace('"', '""')
        # Wrap in double quotes for SQLite
        return f'"{escaped}"'
    
    def is_safe_parameter_value(self, value: Any) -> bool:
        """Check if a parameter value is safe for binding.
        
        Args:
            value: The parameter value to check
            
        Returns:
            True if the value is safe for parameter binding
        """
        # Basic types are always safe for parameter binding
        safe_types = (str, int, float, bool, type(None), bytes)
        return isinstance(value, safe_types)


class SafeQueryExecutor:
    """Executes SQL queries safely on SynthDB databases."""
    
    def __init__(self, connection: Any) -> None:
        """Initialize with a database connection.
        
        Args:
            connection: The database connection to use
        """
        self.connection = connection
        self.validator = SQLValidator()
        self._user_tables_cache: Optional[Set[str]] = None
    
    def _get_user_tables(self) -> Set[str]:
        """Get set of user-created table names."""
        if self._user_tables_cache is None:
            tables = self.connection.list_tables()
            self._user_tables_cache = {t['name'] for t in tables}
        return self._user_tables_cache
    
    def _validate_table_access(self, sql: str) -> ValidationResult:
        """Additional validation for table access in queries."""
        errors = []
        
        # Extract table names from query (simplified)
        from_pattern = re.compile(r'FROM\s+(\w+)', re.IGNORECASE)
        join_pattern = re.compile(r'JOIN\s+(\w+)', re.IGNORECASE)
        
        referenced_tables = set()
        referenced_tables.update(from_pattern.findall(sql))
        referenced_tables.update(join_pattern.findall(sql))
        
        user_tables = self._get_user_tables()
        
        for table in referenced_tables:
            if table.lower() not in {t.lower() for t in user_tables}:
                if table.lower() in SQLValidator.INTERNAL_TABLES:
                    errors.append(f"Cannot access internal table: {table}")
                else:
                    errors.append(f"Table not found: {table}")
        
        return ValidationResult(len(errors) == 0, errors)
    
    def validate_and_prepare_query(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[bool, str, List[str]]:
        """Validate a query and prepare it for execution.
        
        Args:
            sql: The SQL query to validate
            params: Optional parameters for the query
            
        Returns:
            Tuple of (is_valid, prepared_sql, errors)
        """
        # Basic SQL validation
        validation = self.validator.validate_query(sql)
        if not validation.is_safe:
            return False, sql, validation.errors
        
        # Table access validation
        table_validation = self._validate_table_access(sql)
        if not table_validation.is_safe:
            return False, sql, table_validation.errors
        
        # Parameter validation
        if params:
            for i, param in enumerate(params):
                if not self.validator.is_safe_parameter_value(param):
                    return False, sql, [f"Unsafe parameter at position {i}: {type(param).__name__}"]
        
        return True, sql, []
    
    def execute_query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query safely.
        
        Args:
            sql: The SELECT query to execute
            params: Optional parameters for the query
            
        Returns:
            List of dictionaries containing query results
            
        Raises:
            ValueError: If the query is unsafe or invalid
            Exception: If query execution fails
        """
        # Validate query
        is_valid, prepared_sql, errors = self.validate_and_prepare_query(sql, params)
        if not is_valid:
            raise ValueError(f"Unsafe query: {'; '.join(errors)}")
        
        # Execute query using the connection's backend
        from .backends import get_backend
        from .config import config
        
        # Get the backend based on connection's backend name
        db_path = self.connection._get_db_path()
        backend_name = self.connection.backend_name or config.get_backend_for_path(db_path)
        backend = get_backend(backend_name)
        
        # Connect and execute
        db = backend.connect(db_path)
        try:
            cursor = backend.execute(db, prepared_sql, tuple(params) if params else ())
            
            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch results
            rows = backend.fetchall(cursor)
            
            # Convert to list of dicts
            results = []
            for row in rows:
                # Handle row dict-like objects from backend
                if hasattr(row, 'keys'):
                    results.append(dict(row))
                else:
                    results.append(dict(zip(columns, row)))
            
            # Apply ID aliasing if enabled on the connection
            if hasattr(self.connection, 'use_id_alias') and self.connection.use_id_alias:
                results = self.connection._apply_id_alias(results)
            
            return results
        finally:
            backend.close(db)
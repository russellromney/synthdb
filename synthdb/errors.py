"""Enhanced error handling with helpful suggestions for SynthDB."""

import re
from typing import List, Dict, Any
from difflib import get_close_matches


class SynthDBError(Exception):
    """Base exception for SynthDB with enhanced error messages."""
    
    def __init__(self, message: str, suggestions: List[str] | None = None, context: Dict[str, Any] | None = None):
        self.message = message
        self.suggestions = suggestions or []
        self.context = context or {}
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        """Format the error message with suggestions."""
        formatted = self.message
        
        if self.suggestions:
            formatted += "\n\nSuggestions:"
            for suggestion in self.suggestions:
                formatted += f"\n  • {suggestion}"
        
        if self.context:
            formatted += "\n\nContext:"
            for key, value in self.context.items():
                formatted += f"\n  • {key}: {value}"
        
        return formatted


class TableNotFoundError(SynthDBError):
    """Exception for when a table is not found."""
    
    def __init__(self, table_name: str, available_tables: List[str] | None = None):
        suggestions = []
        
        if available_tables:
            # Find similar table names
            similar = get_close_matches(table_name, available_tables, n=3, cutoff=0.6)
            if similar:
                suggestions.append(f"Did you mean: {', '.join(similar)}?")
            
            suggestions.append(f"Available tables: {', '.join(available_tables)}")
            suggestions.append(f"Create the table with: sdb table create {table_name}")
        else:
            suggestions.append("No tables exist yet. Create one with: sdb table create <name>")
        
        super().__init__(
            f"Table '{table_name}' not found",
            suggestions,
            {'table_name': table_name, 'available_tables': available_tables}
        )


class ColumnNotFoundError(SynthDBError):
    """Exception for when a column is not found."""
    
    def __init__(self, column_name: str, table_name: str, available_columns: List[str] | None = None):
        suggestions = []
        
        if available_columns:
            # Find similar column names
            similar = get_close_matches(column_name, available_columns, n=3, cutoff=0.6)
            if similar:
                suggestions.append(f"Did you mean: {', '.join(similar)}?")
            
            suggestions.append(f"Available columns in '{table_name}': {', '.join(available_columns)}")
            suggestions.append(f"Add the column with: sdb table add column {table_name} {column_name} <type>")
        else:
            suggestions.append(f"Table '{table_name}' has no columns yet")
            suggestions.append(f"Add the column with: sdb table add column {table_name} {column_name} <type>")
        
        super().__init__(
            f"Column '{column_name}' not found in table '{table_name}'",
            suggestions,
            {'column_name': column_name, 'table_name': table_name, 'available_columns': available_columns}
        )


class InvalidDataTypeError(SynthDBError):
    """Exception for invalid data types."""
    
    def __init__(self, data_type: str, valid_types: List[str] | None = None):
        valid_types = valid_types or ["text", "integer", "real", "timestamp"]
        
        suggestions = []
        
        # Find similar types
        similar = get_close_matches(data_type, valid_types, n=2, cutoff=0.6)
        if similar:
            suggestions.append(f"Did you mean: {', '.join(similar)}?")
        
        suggestions.append(f"Valid types: {', '.join(valid_types)}")
        suggestions.append("Use --auto flag to automatically infer the type")
        
        super().__init__(
            f"Invalid data type '{data_type}'",
            suggestions,
            {'data_type': data_type, 'valid_types': valid_types}
        )


class ConnectionError(SynthDBError):
    """Exception for database connection issues."""
    
    def __init__(self, backend: str, connection_info: Any, original_error: Exception | None = None):
        suggestions = []
        
        if backend in ("sqlite", "libsql"):
            suggestions.extend([
                "Check that the file path is accessible",
                "Verify you have write permissions to the directory",
                "Make sure the parent directory exists"
            ])
            
            if backend == "libsql":
                suggestions.append("For remote libSQL, ensure the URL is correct")
                suggestions.append("For local libSQL, check file permissions")
        
        error_msg = f"Failed to connect to {backend} database"
        if original_error:
            error_msg += f": {original_error}"
        
        super().__init__(
            error_msg,
            suggestions,
            {'backend': backend, 'connection_info': str(connection_info)}
        )


class TypeConversionError(SynthDBError):
    """Exception for type conversion failures."""
    
    def __init__(self, value: Any, target_type: str, original_error: Exception | None = None):
        suggestions = []
        
        if target_type == "integer":
            suggestions.extend([
                "Ensure the value is a whole number",
                "Remove any decimal points for integers",
                "Check for non-numeric characters"
            ])
        elif target_type == "real":
            suggestions.extend([
                "Use decimal notation (e.g., 3.14)",
                "Scientific notation is supported (e.g., 1.5e-10)",
                "Check for non-numeric characters"
            ])
        elif target_type == "timestamp":
            suggestions.extend([
                "Use ISO format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS",
                "Common formats: 2023-12-25, 2023-12-25 15:30:00",
                "Check for valid date ranges"
            ])
        
        suggestions.append("Consider using --auto to automatically infer the correct type")
        
        error_msg = f"Cannot convert '{value}' to {target_type}"
        if original_error:
            error_msg += f": {original_error}"
        
        super().__init__(
            error_msg,
            suggestions,
            {'value': str(value), 'target_type': target_type}
        )


class FileNotFoundError(SynthDBError):
    """Exception for file-related errors."""
    
    def __init__(self, file_path: str, operation: str = "access"):
        suggestions = [
            "Check that the file path is correct",
            "Verify the file exists and is readable",
            "Use absolute path if relative path isn't working",
            "Check file permissions"
        ]
        
        if operation == "csv":
            suggestions.extend([
                "Ensure the file has CSV format with headers",
                "Check the delimiter (use --delimiter option if needed)",
                "Verify the file encoding (UTF-8 is recommended)"
            ])
        elif operation == "json":
            suggestions.extend([
                "Ensure the file contains valid JSON",
                "For nested data, use --key option to specify array location",
                "Check for syntax errors in the JSON file"
            ])
        
        super().__init__(
            f"File not found or inaccessible: {file_path}",
            suggestions,
            {'file_path': file_path, 'operation': operation}
        )


def suggest_similar_command(command: str, available_commands: List[str]) -> List[str]:
    """Suggest similar commands for typos."""
    suggestions = []
    
    # Find similar commands
    similar = get_close_matches(command, available_commands, n=3, cutoff=0.6)
    if similar:
        suggestions.append(f"Did you mean: {', '.join(similar)}?")
    
    # Common command corrections
    common_corrections = {
        'ls': 'table list',
        'list': 'table list',
        'show': 'table show',
        'desc': 'table show',
        'describe': 'table show',
        'create': 'table create',
        'add': 'table add column',
        'insert': 'insert',
        'select': 'query',
        'export': 'export-csv or export-json',
        'import': 'load-csv or load-json',
        'load': 'load-csv or load-json'
    }
    
    if command.lower() in common_corrections:
        suggestions.append(f"Try: sdb {common_corrections[command.lower()]}")
    
    return suggestions


def enhance_cli_error(error: Exception, command_context: Dict[str, Any] | None = None) -> str:
    """Enhance CLI errors with helpful suggestions."""
    if isinstance(error, SynthDBError):
        return str(error)
    
    # Convert common errors to enhanced errors
    error_msg = str(error).lower()
    
    if "table" in error_msg and "not found" in error_msg:
        # Extract table name from error
        table_match = re.search(r"table '([^']+)' not found", str(error), re.IGNORECASE)
        if table_match:
            table_name = table_match.group(1)
            return str(TableNotFoundError(table_name))
    
    elif "column" in error_msg and "not found" in error_msg:
        # Extract column and table names
        column_match = re.search(r"column '([^']+)' not found in table '([^']+)'", str(error), re.IGNORECASE)
        if column_match:
            column_name, table_name = column_match.groups()
            return str(ColumnNotFoundError(column_name, table_name))
    
    elif "invalid data type" in error_msg:
        type_match = re.search(r"invalid data type '([^']+)'", str(error), re.IGNORECASE)
        if type_match:
            data_type = type_match.group(1)
            return str(InvalidDataTypeError(data_type))
    
    elif "connection" in error_msg or "connect" in error_msg:
        backend = command_context.get('backend', 'unknown') if command_context else 'unknown'
        connection_info = command_context.get('connection_info', 'unknown') if command_context else 'unknown'
        return str(ConnectionError(backend, connection_info, error))
    
    # Default enhancement
    enhanced_msg = f"Error: {error}"
    
    # Add general suggestions based on error type
    if "permission" in error_msg or "access" in error_msg:
        enhanced_msg += "\n\nSuggestions:\n  • Check file/directory permissions\n  • Try running with appropriate privileges"
    elif "syntax" in error_msg:
        enhanced_msg += "\n\nSuggestions:\n  • Check command syntax with --help\n  • Verify parameter values and types"
    elif "file" in error_msg and "not found" in error_msg:
        enhanced_msg += "\n\nSuggestions:\n  • Check the file path\n  • Verify the file exists and is readable"
    
    return enhanced_msg


def format_validation_errors(errors: List[str]) -> str:
    """Format multiple validation errors with helpful context."""
    if not errors:
        return ""
    
    if len(errors) == 1:
        return f"Validation error: {errors[0]}"
    
    formatted = "Multiple validation errors found:\n"
    for i, error in enumerate(errors, 1):
        formatted += f"  {i}. {error}\n"
    
    formatted += "\nTip: Fix these issues and try again"
    return formatted.strip()
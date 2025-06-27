"""Tests for the CLI interface."""

import tempfile
import os
from typer.testing import CliRunner
from synthdb.cli import app

runner = CliRunner()


def test_cli_workflow():
    """Test a complete CLI workflow."""
    # Use temporary database path (don't create the file)
    with tempfile.NamedTemporaryFile(suffix='.db', delete=True) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database
        result = runner.invoke(app, ["db", "init", "--path", db_path])
        assert result.exit_code == 0
        assert "Successfully initialized" in result.stdout
        
        # Create table
        result = runner.invoke(app, ["table", "create", "products", "--path", db_path])
        assert result.exit_code == 0
        assert "Created table 'products'" in result.stdout
        
        # Add column
        result = runner.invoke(app, ["table", "add", "column", "products", "name", "text", "--path", db_path])
        assert result.exit_code == 0
        assert "Added column 'name'" in result.stdout
        
        # List tables
        result = runner.invoke(app, ["table", "list", "--path", db_path])
        assert result.exit_code == 0
        assert "products" in result.stdout
        
        # Show table details
        result = runner.invoke(app, ["table", "show", "products", "--path", db_path])
        assert result.exit_code == 0
        assert "Table: products" in result.stdout
        
        # List columns
        result = runner.invoke(app, ["table", "list", "products", "--path", db_path])
        assert result.exit_code == 0
        assert "name" in result.stdout
        
        # Insert data
        result = runner.invoke(app, ["insert", "products", "0", "name", "Widget", "text", "--path", db_path])
        assert result.exit_code == 0
        assert "Inserted value 'Widget'" in result.stdout
        
        # Query data
        result = runner.invoke(app, ["query", "products", "--path", db_path])
        assert result.exit_code == 0
        assert "Widget" in result.stdout
        
        # Export table
        result = runner.invoke(app, ["table", "export", "products", "--path", db_path])
        assert result.exit_code == 0
        assert "CREATE TABLE products" in result.stdout
        
        # Database info
        result = runner.invoke(app, ["db", "info", "--path", db_path])
        assert result.exit_code == 0
        assert "Database:" in result.stdout
        assert "products" in result.stdout
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_error_handling():
    """Test CLI error handling."""
    # Use temporary database path (don't create the file)
    with tempfile.NamedTemporaryFile(suffix='.db', delete=True) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database
        result = runner.invoke(app, ["db", "init", "--path", db_path])
        assert result.exit_code == 0
        
        # Try to add column to non-existent table
        result = runner.invoke(app, ["table", "add", "column", "nonexistent", "name", "text", "--path", db_path])
        assert result.exit_code == 1
        assert "not found" in result.stdout
        
        # Try to show non-existent table
        result = runner.invoke(app, ["table", "show", "nonexistent", "--path", db_path])
        assert result.exit_code == 1
        assert "not found" in result.stdout
        
        # Try invalid data type
        result = runner.invoke(app, ["table", "create", "test", "--path", db_path])
        assert result.exit_code == 0
        
        result = runner.invoke(app, ["table", "add", "column", "test", "col", "invalid_type", "--path", db_path])
        assert result.exit_code == 1
        assert "Invalid data type" in result.stdout
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)
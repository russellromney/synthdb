"""CLI interface for SynthDB using Typer with noun-first structure."""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from pathlib import Path

from . import (
    make_db, create_table, add_column, insert_typed_value,
    query_view, export_table_structure, list_tables, list_columns
)

app = typer.Typer(
    name="synthdb",
    help="SynthDB - A synthetic database system using Entity-Attribute-Value (EAV) model",
    add_completion=False,
)
console = Console()

# Create noun-based subcommands
database_app = typer.Typer(name="database", help="Database operations")
table_app = typer.Typer(name="table", help="Table operations")

app.add_typer(database_app)
app.add_typer(table_app)

# Database commands
@database_app.command("init")
def database_init(
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing database"),
):
    """Initialize a new SynthDB database."""
    db_file = Path(path)
    
    if db_file.exists() and not force:
        console.print(f"[red]Database file '{path}' already exists. Use --force to overwrite.[/red]")
        raise typer.Exit(1)
    
    try:
        make_db(path)
        console.print(f"[green]Successfully initialized database at '{path}'[/green]")
    except Exception as e:
        console.print(f"[red]Error initializing database: {e}[/red]")
        raise typer.Exit(1)


@database_app.command("info")
def database_info(
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
):
    """Show database information."""
    try:
        tables = list_tables(path)
        
        console.print(f"[bold]Database:[/bold] {path}")
        console.print(f"[bold]Tables:[/bold] {len(tables)}")
        
        if tables:
            table_display = Table(title="Tables Overview")
            table_display.add_column("Name", style="green")
            table_display.add_column("Columns", style="cyan")
            table_display.add_column("Created At", style="yellow")
            
            for table in tables:
                columns = list_columns(table['name'], path)
                table_display.add_row(
                    table['name'],
                    str(len(columns)),
                    str(table['created_at'])
                )
            
            console.print(table_display)
        else:
            console.print("[yellow]No tables found[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error getting database info: {e}[/red]")
        raise typer.Exit(1)


# Table commands
@table_app.command("create")
def table_create(
    name: str = typer.Argument(..., help="Table name"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
):
    """Create a new table."""
    try:
        table_id = create_table(name, path)
        console.print(f"[green]Created table '{name}' with ID {table_id}[/green]")
    except Exception as e:
        console.print(f"[red]Error creating table: {e}[/red]")
        raise typer.Exit(1)


@table_app.command("list")
def table_list(
    columns: Optional[str] = typer.Argument(None, help="Show columns for specific table"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
):
    """List all tables or columns in a specific table."""
    try:
        if columns:
            # List columns for specific table
            table_columns = list_columns(columns, path)
            
            if not table_columns:
                console.print(f"[yellow]No columns found in table '{columns}'[/yellow]")
                return
            
            table_display = Table(title=f"Columns in '{columns}'")
            table_display.add_column("ID", style="cyan")
            table_display.add_column("Name", style="green")
            table_display.add_column("Type", style="magenta")
            table_display.add_column("Created At", style="yellow")
            
            for column in table_columns:
                table_display.add_row(
                    str(column['id']),
                    column['name'],
                    column['data_type'],
                    str(column['created_at'])
                )
            
            console.print(table_display)
        else:
            # List all tables
            tables = list_tables(path)
            
            if not tables:
                console.print("[yellow]No tables found[/yellow]")
                return
            
            table_display = Table(title="Tables")
            table_display.add_column("ID", style="cyan")
            table_display.add_column("Name", style="green")
            table_display.add_column("Columns", style="magenta")
            table_display.add_column("Created At", style="yellow")
            
            for table in tables:
                columns_count = len(list_columns(table['name'], path))
                table_display.add_row(
                    str(table['id']),
                    table['name'],
                    str(columns_count),
                    str(table['created_at'])
                )
            
            console.print(table_display)
            
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error listing: {e}[/red]")
        raise typer.Exit(1)


@table_app.command("show")
def table_show(
    name: str = typer.Argument(..., help="Table name"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
):
    """Show detailed table information."""
    try:
        # Get table info
        tables = list_tables(path)
        table_info = next((t for t in tables if t['name'] == name), None)
        if not table_info:
            console.print(f"[red]Table '{name}' not found[/red]")
            raise typer.Exit(1)
        
        # Get columns
        columns = list_columns(name, path)
        
        console.print(f"[bold]Table:[/bold] {name}")
        console.print(f"[bold]ID:[/bold] {table_info['id']}")
        console.print(f"[bold]Created:[/bold] {table_info['created_at']}")
        console.print(f"[bold]Columns:[/bold] {len(columns)}")
        
        if columns:
            table_display = Table(title=f"Columns in '{name}'")
            table_display.add_column("Name", style="green")
            table_display.add_column("Type", style="magenta")
            table_display.add_column("Created At", style="yellow")
            
            for column in columns:
                table_display.add_row(
                    column['name'],
                    column['data_type'],
                    str(column['created_at'])
                )
            
            console.print(table_display)
        
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error showing table: {e}[/red]")
        raise typer.Exit(1)


@table_app.command("export")
def table_export(
    name: str = typer.Argument(..., help="Table name"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
):
    """Export table structure as CREATE TABLE SQL."""
    try:
        sql = export_table_structure(name, path)
        
        # Display with syntax highlighting
        syntax = Syntax(sql, "sql", theme="monokai", line_numbers=False)
        console.print(syntax)
        
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error exporting table: {e}[/red]")
        raise typer.Exit(1)


# Table sub-commands for complex operations
table_add_app = typer.Typer(name="add", help="Add things to tables")
table_app.add_typer(table_add_app)

@table_add_app.command("column")
def table_add_column(
    table: str = typer.Argument(..., help="Table name"),
    name: str = typer.Argument(..., help="Column name"),
    data_type: str = typer.Argument(..., help="Data type (text, integer, real, boolean, json, timestamp)"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
):
    """Add a column to an existing table."""
    valid_types = ["text", "integer", "real", "boolean", "json", "timestamp"]
    if data_type not in valid_types:
        console.print(f"[red]Invalid data type '{data_type}'. Valid types: {', '.join(valid_types)}[/red]")
        raise typer.Exit(1)
    
    try:
        column_id = add_column(table, name, data_type, path)
        console.print(f"[green]Added column '{name}' ({data_type}) to table '{table}' with ID {column_id}[/green]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error adding column: {e}[/red]")
        raise typer.Exit(1)


# Data commands (moved to main app level)
@app.command("insert")
def insert_cmd(
    table: str = typer.Argument(..., help="Table name"),
    row_id: int = typer.Argument(..., help="Row ID"),
    column: str = typer.Argument(..., help="Column name"),
    value: str = typer.Argument(..., help="Value to insert"),
    data_type: str = typer.Argument(..., help="Data type (text, integer, real, boolean, json, timestamp)"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
):
    """Insert a value into a specific table/row/column."""
    valid_types = ["text", "integer", "real", "boolean", "json", "timestamp"]
    if data_type not in valid_types:
        console.print(f"[red]Invalid data type '{data_type}'. Valid types: {', '.join(valid_types)}[/red]")
        raise typer.Exit(1)
    
    try:
        # Convert value based on type
        if data_type == "integer":
            converted_value = int(value)
        elif data_type == "real":
            converted_value = float(value)
        elif data_type == "boolean":
            converted_value = value.lower() in ("true", "1", "yes", "on")
        else:
            converted_value = value
        
        # Get table and column IDs
        tables = list_tables(path)
        table_info = next((t for t in tables if t['name'] == table), None)
        if not table_info:
            console.print(f"[red]Table '{table}' not found[/red]")
            raise typer.Exit(1)
        
        columns = list_columns(table, path)
        column_info = next((c for c in columns if c['name'] == column), None)
        if not column_info:
            console.print(f"[red]Column '{column}' not found in table '{table}'[/red]")
            raise typer.Exit(1)
        
        insert_typed_value(row_id, table_info['id'], column_info['id'], converted_value, data_type, path)
        console.print(f"[green]Inserted value '{value}' into {table}.{column} for row {row_id}[/green]")
        
    except ValueError as e:
        console.print(f"[red]Invalid value for type {data_type}: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error inserting value: {e}[/red]")
        raise typer.Exit(1)


@app.command("query")
def query_cmd(
    table: str = typer.Argument(..., help="Table name to query"),
    where: Optional[str] = typer.Option(None, "--where", "-w", help="WHERE clause"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
):
    """Query data from a table."""
    try:
        results = query_view(table, where, path)
        
        if not results:
            console.print(f"[yellow]No results found in table '{table}'[/yellow]")
            return
        
        if format == "json":
            import json
            console.print(json.dumps(results, indent=2, default=str))
        else:
            # Create a rich table
            table_display = Table(title=f"Data from '{table}'")
            
            # Add columns
            for column in results[0].keys():
                table_display.add_column(column, style="cyan")
            
            # Add rows
            for row in results:
                table_display.add_row(*[str(value) for value in row.values()])
            
            console.print(table_display)
            
    except Exception as e:
        console.print(f"[red]Error querying table: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
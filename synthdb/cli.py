"""CLI interface for SynthDB using Typer."""

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


@app.command()
def init(
    db_path: str = typer.Option("db.db", "--db", "-d", help="Database file path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing database"),
):
    """Initialize a new SynthDB database."""
    db_file = Path(db_path)
    
    if db_file.exists() and not force:
        console.print(f"[red]Database file '{db_path}' already exists. Use --force to overwrite.[/red]")
        raise typer.Exit(1)
    
    try:
        make_db(db_path)
        console.print(f"[green]Successfully initialized database at '{db_path}'[/green]")
    except Exception as e:
        console.print(f"[red]Error initializing database: {e}[/red]")
        raise typer.Exit(1)


@app.command("create-table")
def create_table_cmd(
    name: str = typer.Argument(..., help="Table name"),
    db_path: str = typer.Option("db.db", "--db", "-d", help="Database file path"),
):
    """Create a new table."""
    try:
        table_id = create_table(name, db_path)
        console.print(f"[green]Created table '{name}' with ID {table_id}[/green]")
    except Exception as e:
        console.print(f"[red]Error creating table: {e}[/red]")
        raise typer.Exit(1)


@app.command("add-column")
def add_column_cmd(
    table: str = typer.Argument(..., help="Table name"),
    column: str = typer.Argument(..., help="Column name"),
    data_type: str = typer.Argument(..., help="Data type (text, integer, real, boolean, json, timestamp)"),
    db_path: str = typer.Option("db.db", "--db", "-d", help="Database file path"),
):
    """Add a column to an existing table."""
    valid_types = ["text", "integer", "real", "boolean", "json", "timestamp"]
    if data_type not in valid_types:
        console.print(f"[red]Invalid data type '{data_type}'. Valid types: {', '.join(valid_types)}[/red]")
        raise typer.Exit(1)
    
    try:
        column_id = add_column(table, column, data_type, db_path)
        console.print(f"[green]Added column '{column}' ({data_type}) to table '{table}' with ID {column_id}[/green]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error adding column: {e}[/red]")
        raise typer.Exit(1)


@app.command("query")
def query_cmd(
    table: str = typer.Argument(..., help="Table name to query"),
    where: Optional[str] = typer.Option(None, "--where", "-w", help="WHERE clause"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
    db_path: str = typer.Option("db.db", "--db", "-d", help="Database file path"),
):
    """Query a table view."""
    try:
        results = query_view(table, where, db_path)
        
        if not results:
            console.print(f"[yellow]No results found in table '{table}'[/yellow]")
            return
        
        if format == "json":
            import json
            console.print(json.dumps(results, indent=2, default=str))
        else:
            # Create a rich table
            table_display = Table(title=f"Table: {table}")
            
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


@app.command("export")
def export_cmd(
    table: str = typer.Argument(..., help="Table name to export"),
    db_path: str = typer.Option("db.db", "--db", "-d", help="Database file path"),
):
    """Export table structure as CREATE TABLE SQL."""
    try:
        sql = export_table_structure(table, db_path)
        
        # Display with syntax highlighting
        syntax = Syntax(sql, "sql", theme="monokai", line_numbers=False)
        console.print(syntax)
        
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error exporting table: {e}[/red]")
        raise typer.Exit(1)


@app.command("list-tables")
def list_tables_cmd(
    db_path: str = typer.Option("db.db", "--db", "-d", help="Database file path"),
):
    """List all tables in the database."""
    try:
        tables = list_tables(db_path)
        
        if not tables:
            console.print("[yellow]No tables found[/yellow]")
            return
        
        table_display = Table(title="Tables")
        table_display.add_column("ID", style="cyan")
        table_display.add_column("Name", style="green")
        table_display.add_column("Created At", style="yellow")
        
        for table in tables:
            table_display.add_row(
                str(table['id']),
                table['name'],
                str(table['created_at'])
            )
        
        console.print(table_display)
        
    except Exception as e:
        console.print(f"[red]Error listing tables: {e}[/red]")
        raise typer.Exit(1)


@app.command("list-columns")
def list_columns_cmd(
    table: str = typer.Argument(..., help="Table name"),
    db_path: str = typer.Option("db.db", "--db", "-d", help="Database file path"),
):
    """List all columns in a table."""
    try:
        columns = list_columns(table, db_path)
        
        if not columns:
            console.print(f"[yellow]No columns found in table '{table}'[/yellow]")
            return
        
        table_display = Table(title=f"Columns in '{table}'")
        table_display.add_column("ID", style="cyan")
        table_display.add_column("Name", style="green")
        table_display.add_column("Type", style="magenta")
        table_display.add_column("Created At", style="yellow")
        
        for column in columns:
            table_display.add_row(
                str(column['id']),
                column['name'],
                column['data_type'],
                str(column['created_at'])
            )
        
        console.print(table_display)
        
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error listing columns: {e}[/red]")
        raise typer.Exit(1)


@app.command("insert")
def insert_cmd(
    table: str = typer.Argument(..., help="Table name"),
    row_id: int = typer.Argument(..., help="Row ID"),
    column: str = typer.Argument(..., help="Column name"),
    value: str = typer.Argument(..., help="Value to insert"),
    data_type: str = typer.Argument(..., help="Data type (text, integer, real, boolean, json, timestamp)"),
    db_path: str = typer.Option("db.db", "--db", "-d", help="Database file path"),
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
        tables = list_tables(db_path)
        table_info = next((t for t in tables if t['name'] == table), None)
        if not table_info:
            console.print(f"[red]Table '{table}' not found[/red]")
            raise typer.Exit(1)
        
        columns = list_columns(table, db_path)
        column_info = next((c for c in columns if c['name'] == column), None)
        if not column_info:
            console.print(f"[red]Column '{column}' not found in table '{table}'[/red]")
            raise typer.Exit(1)
        
        insert_typed_value(row_id, table_info['id'], column_info['id'], converted_value, data_type, db_path)
        console.print(f"[green]Inserted value '{value}' into {table}.{column} for row {row_id}[/green]")
        
    except ValueError as e:
        console.print(f"[red]Invalid value for type {data_type}: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error inserting value: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
"""CLI interface for SynthDB using Typer with noun-first structure."""

import typer
from typing import Optional, Dict, Any, Union
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from pathlib import Path

from . import connect
from .inference import smart_insert
from .bulk import load_csv, load_json, export_csv, export_json
from .errors import TableNotFoundError, ColumnNotFoundError
from .config_file import config_manager, get_connection_info
from .completion import (
    get_table_names, get_column_names, get_data_types, get_backends,
    get_config_formats, get_connection_names, get_csv_files, get_json_files,
    get_config_files, complete_file_path, get_output_formats
)


def build_connection_info(path: str, backend: Optional[str] = None, connection_name: Optional[str] = None) -> Union[str, Dict[str, Any]]:
    """Build connection info from CLI parameters."""
    # Check for named connection first
    if connection_name:
        try:
            return get_connection_info(connection_name)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load connection '{connection_name}': {e}[/yellow]")
    
    # File path (check config for defaults)
    try:
        config = config_manager.get_config()
        if path == "db.db":  # Default value
            path = config['database']['default_path']
        if backend is None:
            backend = config['database']['default_backend']
    except Exception:
        pass  # Use provided values if config fails
    
    return path

app = typer.Typer(
    name="synthdb",
    help="SynthDB - A flexible database system with schema-on-write capabilities",
    add_completion=True,
    invoke_without_command=True,
)
console = Console()

# Main app callback to show help when no command is provided
@app.callback()
def main_callback(ctx: typer.Context) -> None:
    """SynthDB - A flexible database system with schema-on-write capabilities"""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

# Create noun-based subcommands
# invoke_without_command=True allows showing help without error exit codes
database_app = typer.Typer(
    name="database", 
    help="Database operations",
    invoke_without_command=True
)
table_app = typer.Typer(
    name="table", 
    help="Table operations",
    invoke_without_command=True
)
config_app = typer.Typer(
    name="config", 
    help="Configuration management",
    invoke_without_command=True
)

# Add callback functions to show help when no subcommand is provided
@database_app.callback()
def database_callback(ctx: typer.Context) -> None:
    """Database operations"""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

@table_app.callback()
def table_callback(ctx: typer.Context) -> None:
    """Table operations"""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

@config_app.callback()
def config_callback(ctx: typer.Context) -> None:
    """Configuration management"""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

# Add main commands
app.add_typer(database_app, name="db", help="Database operations")
app.add_typer(table_app, name="table", help="Table operations")
app.add_typer(config_app, name="config")

# Database commands
@database_app.command("init")
def database_init(
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path or connection string"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing database"),
    backend: str = typer.Option("sqlite", "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
) -> None:
    """Initialize a new SynthDB database."""
    
    # Validate backend
    if backend not in ("sqlite", "libsql"):
        console.print(f"[red]Invalid backend '{backend}'. Supported: libsql, sqlite[/red]")
        raise typer.Exit(1)
    
    # Build connection info
    connection_info = build_connection_info(path, backend)
    
    # Check file overwrite for file-based backends
    from pathlib import Path
    db_file = Path(path)
    
    if db_file.exists() and not force:
        console.print(f"[red]Database file '{path}' already exists. Use --force to overwrite.[/red]")
        raise typer.Exit(1)
    
    try:
        connect(connection_info, backend=backend)
        
        location = path
        
        console.print(f"[green]Successfully initialized database at '{location}' using {backend} backend[/green]")
    except Exception as e:
        console.print(f"[red]Error initializing database: {e}[/red]")
        raise typer.Exit(1)


@database_app.command("info")
def database_info(
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
) -> None:
    """Show database information."""
    try:
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        tables = db.list_tables()
        
        console.print(f"[bold]Database:[/bold] {path}")
        console.print(f"[bold]Tables:[/bold] {len(tables)}")
        
        if tables:
            table_display = Table(title="Tables Overview")
            table_display.add_column("Name", style="green")
            table_display.add_column("Columns", style="cyan")
            table_display.add_column("Created At", style="yellow")
            
            for table in tables:
                columns = db.list_columns(table['name'])
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
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
) -> None:
    """Create a new table."""
    try:
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        table_id = db.create_table(name)
        console.print(f"[green]Created table '{name}' with ID {table_id}[/green]")
    except Exception as e:
        console.print(f"[red]Error creating table: {e}[/red]")
        raise typer.Exit(1)


@table_app.command("list")
def table_list(
    columns: Optional[str] = typer.Argument(None, help="Show columns for specific table", autocompletion=get_table_names),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
    include_deleted: bool = typer.Option(False, "--include-deleted", "-d", help="Include soft-deleted columns"),
) -> None:
    """List all tables or columns in a specific table."""
    _list_implementation(columns, path, backend, include_deleted)



def _list_implementation(columns: Optional[str], path: str, backend: str, include_deleted: bool = False) -> None:
    """Implementation for list commands."""
    try:
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        
        if columns:
            # List columns for specific table
            table_columns = db.list_columns(columns, include_deleted=include_deleted)
            
            if not table_columns:
                console.print(f"[yellow]No columns found in table '{columns}'[/yellow]")
                return
            
            title = f"Columns in '{columns}'" + (" (including deleted)" if include_deleted else "")
            table_display = Table(title=title)
            table_display.add_column("ID", style="cyan")
            table_display.add_column("Name", style="green")
            table_display.add_column("Type", style="magenta")
            table_display.add_column("Created At", style="yellow")
            if include_deleted:
                table_display.add_column("Deleted At", style="red")
            
            for column in table_columns:
                row_data = [
                    str(column['id']),
                    column['name'],
                    column['data_type'],
                    str(column['created_at'])
                ]
                if include_deleted:
                    deleted_at = column.get('deleted_at', None)
                    row_data.append(str(deleted_at) if deleted_at else "")
                table_display.add_row(*row_data)
            
            console.print(table_display)
        else:
            # List all tables
            tables = db.list_tables()
            
            if not tables:
                console.print("[yellow]No tables found[/yellow]")
                return
            
            table_display = Table(title="Tables")
            table_display.add_column("ID", style="cyan")
            table_display.add_column("Name", style="green")
            table_display.add_column("Columns", style="magenta")
            table_display.add_column("Created At", style="yellow")
            
            for table in tables:
                columns_count = len(db.list_columns(table['name']))
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
    name: str = typer.Argument(..., help="Table name", autocompletion=get_table_names),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
) -> None:
    """Show detailed table information."""
    try:
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        
        # Get table info
        tables = db.list_tables()
        table_info = next((t for t in tables if t['name'] == name), None)
        if not table_info:
            console.print(f"[red]Table '{name}' not found[/red]")
            raise typer.Exit(1)
        
        # Get columns
        columns = db.list_columns(name)
        
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
    name: str = typer.Argument(..., help="Table name", autocompletion=get_table_names),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
) -> None:
    """Export table structure as CREATE TABLE SQL."""
    try:
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        
        sql = _export_table_structure(db, name)
        
        # Display with syntax highlighting
        syntax = Syntax(sql, "sql", theme="monokai", line_numbers=False)
        console.print(syntax)
        
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error exporting table: {e}[/red]")
        raise typer.Exit(1)


@table_app.command("copy")
def table_copy(
    source: str = typer.Argument(..., help="Source table name", autocompletion=get_table_names),
    target: str = typer.Argument(..., help="Target table name"),
    with_data: bool = typer.Option(False, "--with-data", help="Copy data along with structure"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
) -> None:
    """Copy a table's structure and optionally its data."""
    try:
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        
        # Perform the copy
        new_table_id = db.copy_table(source, target, copy_data=with_data)
        
        if with_data:
            console.print(f"[green]Copied table '{source}' to '{target}' (including data) with ID {new_table_id}[/green]")
        else:
            console.print(f"[green]Copied table structure from '{source}' to '{target}' with ID {new_table_id}[/green]")
            
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error copying table: {e}[/red]")
        raise typer.Exit(1)


@table_app.command("rename-column")
def table_rename_column(
    table: str = typer.Argument(..., help="Table name", autocompletion=get_table_names),
    old_name: str = typer.Argument(..., help="Current column name", autocompletion=get_column_names),
    new_name: str = typer.Argument(..., help="New column name"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
):
    """Rename a column in a table."""
    try:
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        
        db.rename_column(table, old_name, new_name)
        console.print(f"[green]Renamed column '{old_name}' to '{new_name}' in table '{table}'[/green]")
        
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error renaming column: {e}[/red]")
        raise typer.Exit(1)


@table_app.command("delete-column")
def table_delete_column(
    table: str = typer.Argument(..., help="Table name", autocompletion=get_table_names),
    column: str = typer.Argument(..., help="Column name to delete", autocompletion=get_column_names),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
    hard: bool = typer.Option(False, "--hard", help="Permanently delete all column data (cannot be recovered)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a column from a table."""
    delete_type = "permanently delete" if hard else "soft delete"
    
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to {delete_type} column '{column}' from table '{table}'?")
        if not confirm:
            console.print("[yellow]Operation cancelled[/yellow]")
            raise typer.Exit(0)
    
    try:
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        
        db.delete_column(table, column, hard_delete=hard)
        
        if hard:
            console.print(f"[green]Permanently deleted column '{column}' from table '{table}' and all its data[/green]")
        else:
            console.print(f"[green]Soft deleted column '{column}' from table '{table}' (data preserved)[/green]")
        
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error deleting column: {e}[/red]")
        raise typer.Exit(1)


@table_app.command("delete")
def table_delete(
    name: str = typer.Argument(..., help="Table name to delete", autocompletion=get_table_names),
    hard: bool = typer.Option(False, "--hard", help="Permanently delete all data (cannot be recovered)"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a table and all its data."""
    delete_type = "permanently delete" if hard else "soft delete"
    
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to {delete_type} table '{name}'?")
        if not confirm:
            console.print("[yellow]Operation cancelled[/yellow]")
            raise typer.Exit(0)
    
    try:
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        
        db.delete_table(name, hard_delete=hard)
        
        if hard:
            console.print(f"[green]Permanently deleted table '{name}' and all its data[/green]")
        else:
            console.print(f"[green]Soft deleted table '{name}' (can be recovered)[/green]")
        
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error deleting table: {e}[/red]")
        raise typer.Exit(1)


# Table sub-commands for complex operations
table_add_app = typer.Typer(
    name="add", 
    help="Add things to tables",
    invoke_without_command=True
)

# Add callback for table add help
@table_add_app.callback()
def table_add_callback(ctx: typer.Context) -> None:
    """Add things to tables"""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

table_app.add_typer(table_add_app)

@table_add_app.command("column")
def table_add_column(
    table: str = typer.Argument(..., help="Table name", autocompletion=get_table_names),
    name: str = typer.Argument(..., help="Column name"),
    data_type: str = typer.Argument(..., help="Data type (text, integer, real, timestamp)", autocompletion=get_data_types),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
):
    """Add a column to an existing table."""
    valid_types = ["text", "integer", "real", "timestamp"]
    if data_type not in valid_types:
        console.print(f"[red]Invalid data type '{data_type}'. Valid types: {', '.join(valid_types)}[/red]")
        raise typer.Exit(1)
    
    try:
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        column_ids = db.add_columns(table, {name: data_type})
        column_id = column_ids[name]
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
    table: str = typer.Argument(..., help="Table name", autocompletion=get_table_names),
    row_id: str = typer.Argument(..., help="Row ID"),
    column: str = typer.Argument(..., help="Column name", autocompletion=get_column_names),
    value: str = typer.Argument(..., help="Value to insert"),
    data_type: str = typer.Argument(None, help="Data type (text, integer, real, timestamp). If not provided, type will be inferred.", autocompletion=get_data_types),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    auto: bool = typer.Option(False, "--auto", "-a", help="Automatically infer data type"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
):
    """Insert a value into a specific table/row/column.
    
    For bulk operations with auto-generated IDs, use the Python API:
    
        import synthdb
        db = synthdb.connect('db.db')
        row_id = db.insert('table', {'col1': 'val1', 'col2': 'val2'})
    
    Or use the 'add' command for JSON input with auto-generated IDs.
    """
    # Build connection info
    connection_info = build_connection_info(path, backend)
    
    # Use smart insert if auto flag is set or no data_type provided
    if auto or data_type is None:
        try:
            inferred_type, converted_value = smart_insert(
                table, row_id, column, value, connection_info, backend
            )
            console.print(f"[green]Inserted value '{value}' into {table}.{column} for row {row_id}[/green]")
            console.print(f"[blue]Inferred type: {inferred_type}[/blue]")
            return
        except Exception as e:
            console.print(f"[red]Error with smart insert: {e}[/red]")
            raise typer.Exit(1)
    
    # Validate explicit data type
    valid_types = ["text", "integer", "real", "timestamp"]
    if data_type not in valid_types:
        console.print(f"[red]Invalid data type '{data_type}'. Valid types: {', '.join(valid_types)}[/red]")
        console.print("[yellow]Tip: Use --auto to automatically infer the type[/yellow]")
        raise typer.Exit(1)
    
    try:
        # Convert value based on type
        if data_type == "integer":
            converted_value = int(value)
        elif data_type == "real":
            converted_value = float(value)
        else:
            converted_value = value
        
        # Get table and column IDs with enhanced error handling
        try:
            db = connect(connection_info, backend)
            tables = db.list_tables()
            table_info = next((t for t in tables if t['name'] == table), None)
            if not table_info:
                available_tables = [t['name'] for t in tables]
                raise TableNotFoundError(table, available_tables)
            
            columns = db.list_columns(table)
            column_info = next((c for c in columns if c['name'] == column), None)
            if not column_info:
                available_columns = [c['name'] for c in columns]
                raise ColumnNotFoundError(column, table, available_columns)
        
        except (TableNotFoundError, ColumnNotFoundError) as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)
        
        # Use connection API for single column insert
        db = connect(connection_info, backend)
        db.insert(table, column, converted_value, row_id=row_id, force_type=data_type)
        console.print(f"[green]Inserted value '{value}' into {table}.{column} for row {row_id}[/green]")
        
    except ValueError as e:
        console.print(f"[red]Invalid value for type {data_type}: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error inserting value: {e}[/red]")
        raise typer.Exit(1)


@app.command("query")
def query_cmd(
    table: str = typer.Argument(..., help="Table name to query", autocompletion=get_table_names),
    where: Optional[str] = typer.Option(None, "--where", "-w", help="WHERE clause"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json", autocompletion=get_output_formats),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)", autocompletion=get_backends),
):
    """Query data from a table."""
    _query_implementation(table, where, format, path, backend)




def _query_implementation(table: str, where: Optional[str], format: str, path: str, backend: str) -> None:
    """Query data from a table."""
    try:
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        results = db.query(table, where)
        
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


# Load/Export commands
@app.command("load-csv")
def load_csv_cmd(
    file_path: str = typer.Argument(..., help="Path to CSV file", autocompletion=get_csv_files),
    table: str = typer.Option(None, "--table", "-t", help="Table name (defaults to filename)", autocompletion=get_table_names),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend", autocompletion=get_backends),
    create_table: bool = typer.Option(True, "--create-table/--no-create-table", help="Create table if it doesn't exist"),
    delimiter: str = typer.Option(",", "--delimiter", "-d", help="CSV delimiter"),
):
    """Load data from CSV file into a table."""
    try:
        connection_info = build_connection_info(path, backend)
        
        with console.status("[bold green]Loading CSV file..."):
            stats = load_csv(
                file_path, table, connection_info, backend, 
                create_table, delimiter
            )
        
        console.print("[green]Successfully loaded CSV file![/green]")
        console.print(f"[blue]Table: {stats['table_name']}[/blue]")
        console.print(f"[blue]Rows processed: {stats['rows_processed']}[/blue]")
        console.print(f"[blue]Rows inserted: {stats['inserted']}[/blue]")
        if stats['errors'] > 0:
            console.print(f"[yellow]Errors: {stats['errors']}[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error loading CSV: {e}[/red]")
        raise typer.Exit(1)


@app.command("load-json")
def load_json_cmd(
    file_path: str = typer.Argument(..., help="Path to JSON file", autocompletion=get_json_files),
    table: str = typer.Option(None, "--table", "-t", help="Table name (defaults to filename)", autocompletion=get_table_names),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend", autocompletion=get_backends),
    create_table: bool = typer.Option(True, "--create-table/--no-create-table", help="Create table if it doesn't exist"),
    json_key: str = typer.Option(None, "--key", "-k", help="JSON key containing array data"),
):
    """Load data from JSON file into a table."""
    try:
        connection_info = build_connection_info(path, backend)
        
        with console.status("[bold green]Loading JSON file..."):
            stats = load_json(
                file_path, table, connection_info, backend, 
                create_table, json_key
            )
        
        console.print("[green]Successfully loaded JSON file![/green]")
        console.print(f"[blue]Table: {stats['table_name']}[/blue]")
        console.print(f"[blue]Rows processed: {stats['rows_processed']}[/blue]")
        console.print(f"[blue]Rows inserted: {stats['inserted']}[/blue]")
        if stats['errors'] > 0:
            console.print(f"[yellow]Errors: {stats['errors']}[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error loading JSON: {e}[/red]")
        raise typer.Exit(1)


@app.command("export-csv")
def export_csv_cmd(
    table: str = typer.Argument(..., help="Table name to export", autocompletion=get_table_names),
    file_path: str = typer.Argument(..., help="Output CSV file path", autocompletion=complete_file_path),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend", autocompletion=get_backends),
    where: str = typer.Option(None, "--where", "-w", help="WHERE clause for filtering"),
    delimiter: str = typer.Option(",", "--delimiter", "-d", help="CSV delimiter"),
):
    """Export table data to CSV file."""
    try:
        connection_info = build_connection_info(path, backend)
        
        with console.status("[bold green]Exporting to CSV..."):
            stats = export_csv(
                table, file_path, connection_info, backend, where, delimiter
            )
        
        console.print("[green]Successfully exported to CSV![/green]")
        console.print(f"[blue]Table: {stats['table_name']}[/blue]")
        console.print(f"[blue]File: {stats['file_path']}[/blue]")
        console.print(f"[blue]Rows exported: {stats['rows_exported']}[/blue]")
            
    except Exception as e:
        console.print(f"[red]Error exporting CSV: {e}[/red]")
        raise typer.Exit(1)


@app.command("export-json")
def export_json_cmd(
    table: str = typer.Argument(..., help="Table name to export", autocompletion=get_table_names),
    file_path: str = typer.Argument(..., help="Output JSON file path", autocompletion=complete_file_path),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend", autocompletion=get_backends),
    where: str = typer.Option(None, "--where", "-w", help="WHERE clause for filtering"),
    indent: int = typer.Option(2, "--indent", help="JSON indentation"),
):
    """Export table data to JSON file."""
    try:
        connection_info = build_connection_info(path, backend)
        
        with console.status("[bold green]Exporting to JSON..."):
            stats = export_json(
                table, file_path, connection_info, backend, where, indent
            )
        
        console.print("[green]Successfully exported to JSON![/green]")
        console.print(f"[blue]Table: {stats['table_name']}[/blue]")
        console.print(f"[blue]File: {stats['file_path']}[/blue]")
        console.print(f"[blue]Rows exported: {stats['rows_exported']}[/blue]")
            
    except Exception as e:
        console.print(f"[red]Error exporting JSON: {e}[/red]")
        raise typer.Exit(1)


# Config commands
@config_app.command("init")
def config_init(
    path: str = typer.Option(".synthdb.json", "--path", "-p", help="Config file path", autocompletion=complete_file_path),
    format: str = typer.Option("json", "--format", "-f", help="Config format (json, yaml, toml)", autocompletion=get_config_formats),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config"),
):
    """Create a sample configuration file."""
    try:
        config_path = Path(path)
        if config_path.exists() and not force:
            console.print(f"[red]Config file '{path}' already exists. Use --force to overwrite.[/red]")
            raise typer.Exit(1)
        
        config_manager.create_sample_config(config_path, format)
        console.print(f"[green]Created sample config file: {config_path}[/green]")
        console.print("[blue]Edit the file to customize your settings[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error creating config: {e}[/red]")
        raise typer.Exit(1)


@config_app.command("show")
def config_show(
    config_path: str = typer.Option(None, "--config", "-c", help="Specific config file to show", autocompletion=get_config_files),
):
    """Show current configuration."""
    try:
        if config_path:
            config = config_manager.load_config(config_path)
            console.print(f"[blue]Configuration from: {config_path}[/blue]")
        else:
            config = config_manager.get_config()
            config_file = config_manager.find_config_file()
            if config_file:
                console.print(f"[blue]Configuration from: {config_file}[/blue]")
            else:
                console.print("[blue]Using default configuration (no config file found)[/blue]")
        
        # Display config in a nice format
        import json
        config_json = json.dumps(config, indent=2, default=str)
        syntax = Syntax(config_json, "json", theme="monokai", line_numbers=False)
        console.print(syntax)
        
    except Exception as e:
        console.print(f"[red]Error showing config: {e}[/red]")
        raise typer.Exit(1)


@config_app.command("connections")
def config_connections() -> None:
    """List available named connections."""
    try:
        config = config_manager.get_config()
        connections = config.get('connections', {})
        
        if not connections:
            console.print("[yellow]No named connections configured[/yellow]")
            console.print("[blue]Use 'sdb config init' to create a sample config with example connections[/blue]")
            return
        
        table_display = Table(title="Named Connections")
        table_display.add_column("Name", style="green")
        table_display.add_column("Backend", style="cyan")
        table_display.add_column("Details", style="yellow")
        
        for name, conn_info in connections.items():
            backend = conn_info.get('backend', 'unknown')
            
            # Only local file backends are supported
            details = conn_info.get('path', 'N/A')
            
            table_display.add_row(name, backend, details)
        
        console.print(table_display)
        
    except Exception as e:
        console.print(f"[red]Error listing connections: {e}[/red]")
        raise typer.Exit(1)


@config_app.command("test")
def config_test(
    connection: str = typer.Argument(None, help="Connection name to test (tests default if not specified)", autocompletion=get_connection_names),
):
    """Test a database connection."""
    try:
        if connection:
            connection_info = get_connection_info(connection)
            console.print(f"[blue]Testing connection '{connection}'...[/blue]")
        else:
            connection_info = get_connection_info()
            console.print("[blue]Testing default connection...[/blue]")
        
        # Try to connect
        from .backends import get_backend, detect_backend_from_connection
        
        backend_name = connection_info.get('backend')
        if not backend_name:
            backend_name = detect_backend_from_connection(connection_info)
        
        backend = get_backend(backend_name)
        
        with console.status("[bold green]Connecting..."):
            connection_obj = backend.connect(connection_info)
            backend.close(connection_obj)
        
        console.print("[green]✓ Connection successful![/green]")
        console.print(f"[blue]Backend: {backend_name}[/blue]")
        
    except Exception as e:
        console.print(f"[red]✗ Connection failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("add")
def add_cmd(
    table: str = typer.Argument(..., help="Table name", autocompletion=get_table_names),
    data: str = typer.Argument(..., help="JSON data to insert (e.g., '{\"name\": \"Widget\", \"price\": 19.99}')"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path", autocompletion=complete_file_path),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend", autocompletion=get_backends),
    row_id: str = typer.Option(None, "--id", help="Explicit row ID (auto-generated if not provided)"),
):
    """Add data using the modern API (auto-generated IDs, type inference)."""
    _add_implementation(table, data, path, backend, row_id)




def _export_table_structure(db, table_name: str) -> str:
    """Export table structure using connection API."""
    # Check if table exists
    tables = db.list_tables()
    table_info = next((t for t in tables if t['name'] == table_name), None)
    if not table_info:
        raise ValueError(f"Table '{table_name}' not found")
    
    # Get columns for this table
    columns = db.list_columns(table_name)
    
    if not columns:
        return f"-- Table '{table_name}' has no columns"
    
    # Build CREATE TABLE statement
    column_defs = []
    for col in columns:
        col_name = col['name']
        data_type = col['data_type']
        # Map our internal types to SQLite types
        sqlite_type = {
            'text': 'TEXT',
            'integer': 'INTEGER', 
            'real': 'REAL',
            'timestamp': 'TIMESTAMP'
        }.get(data_type, 'TEXT')
        
        column_defs.append(f"    {col_name} {sqlite_type}")
    
    create_statement = f"CREATE TABLE {table_name} (\n" + ",\n".join(column_defs) + "\n);"
    return create_statement


def _add_implementation(table: str, data: str, path: str, backend: str, row_id: str) -> None:
    """Implementation for add/insert commands."""
    import json
    
    try:
        # Parse JSON data
        try:
            data_dict = json.loads(data)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON data: {e}[/red]")
            console.print("[blue]Example: '{\"name\": \"Widget\", \"price\": 19.99}'[/blue]")
            raise typer.Exit(1)
        
        # Build connection info
        connection_info = build_connection_info(path, backend)
        
        # Use new API
        from .api import insert
        
        result_id = insert(
            table, data_dict, 
            connection_info=connection_info, 
            backend_name=backend,
            row_id=row_id
        )
        
        if row_id is not None:
            console.print(f"[green]Added data to row {result_id} in table '{table}'[/green]")
        else:
            console.print(f"[green]Added data with auto-generated ID {result_id} in table '{table}'[/green]")
            
    except Exception as e:
        console.print(f"[red]Error adding data: {e}[/red]")
        raise typer.Exit(1)


@app.command("completion")
def completion_cmd(
    shell: str = typer.Option(None, "--shell", help="Shell type (bash, zsh, fish)"),
    install: bool = typer.Option(False, "--install", help="Install completion for your shell"),
):
    """Set up shell completion for SynthDB CLI."""
    from .completion import setup_completion, install_completion
    
    if install:
        console.print("[blue]Installing shell completion...[/blue]")
        success = install_completion(shell)
        if success:
            console.print("[green]✓ Completion installed successfully![/green]")
        else:
            console.print("[red]✗ Failed to install completion[/red]")
            raise typer.Exit(1)
    else:
        # Show setup instructions
        setup_script = setup_completion()
        console.print("[bold]Shell Completion Setup[/bold]")
        syntax = Syntax(setup_script, "bash", theme="monokai", line_numbers=False)
        console.print(syntax)
        console.print("\n[blue]Tip: Use --install to automatically add completion to your shell configuration[/blue]")


if __name__ == "__main__":
    app()
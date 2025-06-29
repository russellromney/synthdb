"""CLI interface for SynthDB using Typer with noun-first structure."""

import typer
from typing import Optional, Dict, Any, Union, List
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from pathlib import Path

from . import connect
from .inference import smart_insert
from .bulk import load_csv, load_json, export_csv, export_json
from .errors import TableNotFoundError, ColumnNotFoundError
from .config_file import config_manager, get_connection_info
from .local_config import get_local_config, init_local_project


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
    invoke_without_command=True,
    add_completion=False,
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
project_app = typer.Typer(
    name="project",
    help="Project management",
    invoke_without_command=True
)
branch_app = typer.Typer(
    name="branch",
    help="Branch management",
    invoke_without_command=True
)
query_app = typer.Typer(
    name="query", 
    help="Saved query management",
    invoke_without_command=True
)
api_app = typer.Typer(
    name="api",
    help="API server management",
    invoke_without_command=True
)
models_app = typer.Typer(
    name="models",
    help="Type-safe model generation",
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

@project_app.callback()
def project_callback(ctx: typer.Context) -> None:
    """Project management"""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

@branch_app.callback()
def branch_callback(ctx: typer.Context) -> None:
    """Branch management"""
    if ctx.invoked_subcommand is None:
        # Default to list if no subcommand
        branch_list()

@query_app.callback()
def query_callback(ctx: typer.Context) -> None:
    """Saved query management"""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

@api_app.callback()
def api_callback(ctx: typer.Context) -> None:
    """API server management"""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

@models_app.callback()
def models_callback(ctx: typer.Context) -> None:
    """Type-safe model generation"""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

# Add main commands
app.add_typer(database_app, name="db", help="Database operations")
app.add_typer(table_app, name="table", help="Table operations")
app.add_typer(config_app, name="config")
app.add_typer(project_app, name="project", help="Project management")
app.add_typer(branch_app, name="branch", help="Branch management")
app.add_typer(query_app, name="query", help="Saved query management")
app.add_typer(api_app, name="api", help="API server management")
app.add_typer(models_app, name="models", help="Type-safe model generation")

# Database commands
@database_app.command("init")
def database_init(
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path or connection string"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing database"),
    backend: str = typer.Option("sqlite", "--backend", "-b", help="Database backend (sqlite, libsql)"),
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
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
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
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
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
    columns: Optional[str] = typer.Argument(None, help="Show columns for specific table"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
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
    name: str = typer.Argument(..., help="Table name"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
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
    name: str = typer.Argument(..., help="Table name"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
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
    source: str = typer.Argument(..., help="Source table name"),
    target: str = typer.Argument(..., help="Target table name"),
    with_data: bool = typer.Option(False, "--with-data", help="Copy data along with structure"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
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
    table: str = typer.Argument(..., help="Table name"),
    old_name: str = typer.Argument(..., help="Current column name"),
    new_name: str = typer.Argument(..., help="New column name"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
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
    table: str = typer.Argument(..., help="Table name"),
    column: str = typer.Argument(..., help="Column name to delete"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
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
    name: str = typer.Argument(..., help="Table name to delete"),
    hard: bool = typer.Option(False, "--hard", help="Permanently delete all data (cannot be recovered)"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
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
    table: str = typer.Argument(..., help="Table name"),
    name: str = typer.Argument(..., help="Column name"),
    data_type: str = typer.Argument(..., help="Data type (text, integer, real, timestamp)"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
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
    table: str = typer.Argument(..., help="Table name"),
    id: str = typer.Argument(..., help="Row ID"),
    column: str = typer.Argument(..., help="Column name"),
    value: str = typer.Argument(..., help="Value to insert"),
    data_type: str = typer.Argument(None, help="Data type (text, integer, real, timestamp). If not provided, type will be inferred."),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    auto: bool = typer.Option(False, "--auto", "-a", help="Automatically infer data type"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
):
    """Insert a value into a specific table/row/column.
    
    For bulk operations with auto-generated IDs, use the Python API:
    
        import synthdb
        db = synthdb.connect('db.db')
        id = db.insert('table', {'col1': 'val1', 'col2': 'val2'})
    
    Or use the 'add' command for JSON input with auto-generated IDs.
    """
    # Build connection info
    connection_info = build_connection_info(path, backend)
    
    # Use smart insert if auto flag is set or no data_type provided
    if auto or data_type is None:
        try:
            inferred_type, converted_value = smart_insert(
                table, id, column, value, connection_info, backend
            )
            console.print(f"[green]Inserted value '{value}' into {table}.{column} for id {id}[/green]")
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
        db.insert(table, column, converted_value, id=id, force_type=data_type)
        console.print(f"[green]Inserted value '{value}' into {table}.{column} for id {id}[/green]")
        
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
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
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


@app.command("sql")
def sql_cmd(
    query: str = typer.Argument(..., help="SQL query to execute (SELECT only)"),
    params: Optional[str] = typer.Option(None, "--params", "-p", help="Query parameters as JSON array"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json, csv"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    path: str = typer.Option("db.db", "--path", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend (sqlite, libsql)"),
):
    """Execute a safe SQL query (SELECT only).
    
    Examples:
        sdb sql "SELECT * FROM users WHERE age > 25"
        sdb sql "SELECT * FROM users WHERE age > ?" --params "[25]"
        sdb sql "SELECT name, COUNT(*) FROM users GROUP BY name" --format json
    """
    try:
        import json
        
        # Parse parameters if provided
        query_params = None
        if params:
            try:
                query_params = json.loads(params)
                if not isinstance(query_params, list):
                    console.print("[red]Error: --params must be a JSON array[/red]")
                    raise typer.Exit(1)
            except json.JSONDecodeError:
                console.print("[red]Error: Invalid JSON in --params[/red]")
                raise typer.Exit(1)
        
        # Connect and execute
        connection_info = build_connection_info(path, backend)
        db = connect(connection_info, backend)
        
        try:
            results = db.execute_sql(query, query_params)
        except ValueError as e:
            console.print(f"[red]Query validation error: {e}[/red]")
            raise typer.Exit(1)
        
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return
        
        # Format output
        if format == "json":
            output_text = json.dumps(results, indent=2, default=str)
            if output:
                with open(output, 'w') as f:
                    f.write(output_text)
                console.print(f"[green]Results written to {output}[/green]")
            else:
                console.print(output_text)
                
        elif format == "csv":
            import csv
            import io
            
            if results:
                output_buffer = io.StringIO()
                writer = csv.DictWriter(output_buffer, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
                output_text = output_buffer.getvalue()
                
                if output:
                    with open(output, 'w') as f:
                        f.write(output_text)
                    console.print(f"[green]Results written to {output}[/green]")
                else:
                    console.print(output_text)
                    
        else:  # table format
            # Create a rich table
            table_display = Table(title="Query Results")
            
            # Add columns
            for column in results[0].keys():
                table_display.add_column(column, style="cyan")
            
            # Add rows
            for row in results:
                table_display.add_row(*[str(value) for value in row.values()])
            
            console.print(table_display)
            console.print(f"\n[dim]Returned {len(results)} row(s)[/dim]")
            
    except Exception as e:
        console.print(f"[red]Error executing SQL: {e}[/red]")
        raise typer.Exit(1)


# Load/Export commands
@app.command("load-csv")
def load_csv_cmd(
    file_path: str = typer.Argument(..., help="Path to CSV file"),
    table: str = typer.Option(None, "--table", "-t", help="Table name (defaults to filename)"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend"),
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
    file_path: str = typer.Argument(..., help="Path to JSON file"),
    table: str = typer.Option(None, "--table", "-t", help="Table name (defaults to filename)"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend"),
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
    table: str = typer.Argument(..., help="Table name to export"),
    file_path: str = typer.Argument(..., help="Output CSV file path"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend"),
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
    table: str = typer.Argument(..., help="Table name to export"),
    file_path: str = typer.Argument(..., help="Output JSON file path"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend"),
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
    path: str = typer.Option(".synthdb.json", "--path", "-p", help="Config file path"),
    format: str = typer.Option("json", "--format", "-f", help="Config format (json, yaml, toml)"),
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
    config_path: str = typer.Option(None, "--config", "-c", help="Specific config file to show"),
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
    connection: str = typer.Argument(None, help="Connection name to test (tests default if not specified)"),
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


# Project commands
@project_app.command("init")
def project_init(
    directory: str = typer.Option(".", "--directory", "-d", help="Directory to initialize project in"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing .synthdb directory"),
):
    """Initialize a new SynthDB project with .synthdb directory."""
    try:
        target_dir = Path(directory)
        synthdb_dir = target_dir / ".synthdb"
        
        if synthdb_dir.exists() and not force:
            console.print(f"[red].synthdb directory already exists in '{directory}'. Use --force to overwrite.[/red]")
            raise typer.Exit(1)
        
        # Initialize the project
        project_path = init_local_project(target_dir)
        console.print(f"[green]✓ Initialized SynthDB project in {project_path}[/green]")
        console.print("[blue]Created .synthdb/config with default database at .synthdb/databases/main.db[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error initializing project: {e}[/red]")
        raise typer.Exit(1)


@project_app.command("status")
def project_status():
    """Show project status and active branch."""
    try:
        local_config = get_local_config()
        
        if not local_config.synthdb_dir:
            console.print("[yellow]No .synthdb directory found in current directory or parent directories[/yellow]")
            console.print("[blue]Use 'sdb project init' to initialize a new project[/blue]")
            raise typer.Exit(1)
        
        console.print(f"[bold]Project Directory:[/bold] {local_config.synthdb_dir.parent}")
        console.print(f"[bold]SynthDB Directory:[/bold] {local_config.synthdb_dir}")
        
        # Show active branch
        active_branch = local_config.get_active_branch()
        console.print(f"[bold]Active Branch:[/bold] [green]{active_branch}[/green]")
        
        # Show database path
        db_path = local_config.get_database_path()
        if db_path:
            console.print(f"[bold]Database Path:[/bold] {db_path}")
            if Path(db_path).exists():
                console.print("[green]✓ Database file exists[/green]")
            else:
                console.print("[yellow]⚠ Database file does not exist yet[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error getting project status: {e}[/red]")
        raise typer.Exit(1)


# Branch commands (moved to top-level)


@branch_app.command("list")
def branch_list():
    """List all branches in the project."""
    try:
        local_config = get_local_config()
        
        if not local_config.synthdb_dir:
            console.print("[red]No .synthdb directory found[/red]")
            console.print("[blue]Use 'sdb project init' to initialize a project[/blue]")
            raise typer.Exit(1)
        
        branches = local_config.list_branches()
        active_branch = local_config.get_active_branch()
        
        if not branches:
            console.print("[yellow]No branches found[/yellow]")
            return
        
        table_display = Table(title="Project Branches")
        table_display.add_column("Branch", style="green")
        table_display.add_column("Status", style="magenta")
        table_display.add_column("Database", style="cyan")
        table_display.add_column("Created", style="yellow")
        
        for branch_name, info in branches.items():
            status = "● active" if branch_name == active_branch else "○"
            table_display.add_row(
                branch_name,
                status,
                info.get('database', 'N/A'),
                info.get('created', 'N/A')
            )
        
        console.print(table_display)
        
    except Exception as e:
        console.print(f"[red]Error listing branches: {e}[/red]")
        raise typer.Exit(1)


@branch_app.command("create")
def branch_create(
    name: str = typer.Argument(..., help="Name for the new branch"),
    from_branch: str = typer.Option(None, "--from", "-f", help="Source branch to copy from (default: current branch)"),
    switch: bool = typer.Option(True, "--switch/--no-switch", help="Switch to the new branch after creation"),
):
    """Create a new branch with a copy of the database."""
    try:
        local_config = get_local_config()
        
        if not local_config.synthdb_dir:
            console.print("[red]No .synthdb directory found[/red]")
            console.print("[blue]Use 'sdb project init' to initialize a project[/blue]")
            raise typer.Exit(1)
        
        # Check if branch already exists
        branches = local_config.list_branches()
        if name in branches:
            console.print(f"[red]Branch '{name}' already exists[/red]")
            raise typer.Exit(1)
        
        # Show source branch
        if from_branch:
            console.print(f"[blue]Creating branch '{name}' from '{from_branch}'...[/blue]")
        else:
            current = local_config.get_active_branch()
            console.print(f"[blue]Creating branch '{name}' from current branch '{current}'...[/blue]")
        
        # Create the branch
        db_path = local_config.create_branch(name, from_branch)
        console.print(f"[green]✓ Created branch '{name}'[/green]")
        console.print(f"[blue]  Database: {db_path}[/blue]")
        
        # Switch if requested
        if switch:
            local_config.set_active_branch(name)
            console.print(f"[green]✓ Switched to branch '{name}'[/green]")
        
    except Exception as e:
        console.print(f"[red]Error creating branch: {e}[/red]")
        raise typer.Exit(1)


@branch_app.command("switch")
def branch_switch(
    name: str = typer.Argument(..., help="Branch name to switch to"),
):
    """Switch to a different branch."""
    try:
        local_config = get_local_config()
        
        if not local_config.synthdb_dir:
            console.print("[red]No .synthdb directory found[/red]")
            raise typer.Exit(1)
        
        # Check if branch exists
        branches = local_config.list_branches()
        if name not in branches:
            console.print(f"[red]Branch '{name}' does not exist[/red]")
            console.print("[blue]Available branches:[/blue]")
            for branch in branches:
                console.print(f"  - {branch}")
            raise typer.Exit(1)
        
        # Check if already on this branch
        current = local_config.get_active_branch()
        if current == name:
            console.print(f"[yellow]Already on branch '{name}'[/yellow]")
            return
        
        # Switch branch
        local_config.set_active_branch(name)
        console.print(f"[green]✓ Switched to branch '{name}'[/green]")
        
        # Show database info
        db_path = local_config.get_database_path(name)
        if db_path:
            console.print(f"[blue]Database: {db_path}[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error switching branch: {e}[/red]")
        raise typer.Exit(1)


@branch_app.command("current")
def branch_current():
    """Show the current active branch."""
    try:
        local_config = get_local_config()
        
        if not local_config.synthdb_dir:
            console.print("[red]No .synthdb directory found[/red]")
            raise typer.Exit(1)
        
        current = local_config.get_active_branch()
        console.print(f"[green]Current branch: {current}[/green]")
        
        # Show database path
        db_path = local_config.get_database_path()
        if db_path:
            console.print(f"[blue]Database: {db_path}[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error getting current branch: {e}[/red]")
        raise typer.Exit(1)


@branch_app.command("delete")
def branch_delete(
    name: str = typer.Argument(..., help="Branch name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation"),
):
    """Delete a branch and its database."""
    try:
        local_config = get_local_config()
        
        if not local_config.synthdb_dir:
            console.print("[red]No .synthdb directory found[/red]")
            raise typer.Exit(1)
        
        # Check if branch exists
        branches = local_config.list_branches()
        if name not in branches:
            console.print(f"[red]Branch '{name}' does not exist[/red]")
            raise typer.Exit(1)
        
        # Can't delete active branch
        current = local_config.get_active_branch()
        if current == name:
            console.print(f"[red]Cannot delete the active branch '{name}'[/red]")
            console.print("[blue]Switch to a different branch first[/blue]")
            raise typer.Exit(1)
        
        # Get database path before deletion
        branch_info = branches[name]
        db_path = branch_info.get('database', 'N/A')
        
        # Confirm deletion
        if not force:
            confirm = typer.confirm(f"Delete branch '{name}' and its database? This cannot be undone.")
            if not confirm:
                console.print("[yellow]Deletion cancelled[/yellow]")
                raise typer.Exit(0)
        
        # Delete the database file
        if db_path != 'N/A':
            full_path = local_config.synthdb_dir.parent / db_path
            if full_path.exists():
                full_path.unlink()
                console.print(f"[blue]Deleted database: {db_path}[/blue]")
        
        # Remove from config
        config = local_config.config
        branch_section = f'branch.{name}'
        if branch_section in config:
            config.remove_section(branch_section)
            local_config._write_config(config)
            local_config._config = None  # Invalidate cache
        
        console.print(f"[green]✓ Deleted branch '{name}'[/green]")
        
    except Exception as e:
        console.print(f"[red]Error deleting branch: {e}[/red]")
        raise typer.Exit(1)


@branch_app.command("merge")
def branch_merge(
    source: str = typer.Argument(..., help="Source branch to merge from"),
    target: str = typer.Option(None, "--into", "-i", help="Target branch to merge into (default: current branch)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be merged without making changes"),
):
    """Merge table structure changes from one branch to another.
    
    This command merges new tables and columns from the source branch into the target branch.
    It does NOT merge data, only structure. Existing columns are never modified.
    
    Type conflicts (where a column exists in both branches with different types) are reported
    but not merged.
    """
    try:
        local_config = get_local_config()
        
        if not local_config.synthdb_dir:
            console.print("[red]No .synthdb directory found[/red]")
            raise typer.Exit(1)
        
        # Validate branches exist
        branches = local_config.list_branches()
        if source not in branches:
            console.print(f"[red]Source branch '{source}' does not exist[/red]")
            raise typer.Exit(1)
        
        # Determine target branch
        if target is None:
            target = local_config.get_active_branch()
            console.print(f"[blue]Merging into current branch: {target}[/blue]")
        elif target not in branches:
            console.print(f"[red]Target branch '{target}' does not exist[/red]")
            raise typer.Exit(1)
        
        # Can't merge branch into itself
        if source == target:
            console.print(f"[red]Cannot merge branch '{source}' into itself[/red]")
            raise typer.Exit(1)
        
        # Show what we're doing
        if dry_run:
            console.print(f"[yellow]DRY RUN: Showing what would be merged from '{source}' into '{target}'[/yellow]")
        else:
            console.print(f"[blue]Merging structure from '{source}' into '{target}'...[/blue]")
        
        # Perform the merge
        results = local_config.merge_structure(source, target, dry_run=dry_run)
        
        # Display results
        if not results['new_tables'] and not results['new_columns'] and not results['type_conflicts']:
            console.print(f"[green]No structure changes to merge from '{source}' to '{target}'[/green]")
            return
        
        # Show new tables
        if results['new_tables']:
            console.print("\n[bold]New Tables:[/bold]")
            for table in results['new_tables']:
                if dry_run:
                    console.print(f"  [yellow]+ {table}[/yellow] (would be created)")
                else:
                    console.print(f"  [green]+ {table}[/green] (created)")
        
        # Show new columns
        if results['new_columns']:
            console.print("\n[bold]New Columns:[/bold]")
            for table, columns in results['new_columns'].items():
                console.print(f"  Table: {table}")
                for column in columns:
                    if dry_run:
                        console.print(f"    [yellow]+ {column}[/yellow] (would be added)")
                    else:
                        console.print(f"    [green]+ {column}[/green] (added)")
        
        # Show type conflicts
        if results['type_conflicts']:
            console.print("\n[bold red]Type Conflicts (not merged):[/bold red]")
            for conflict in results['type_conflicts']:
                console.print(f"  Table: {conflict['table']}")
                console.print(f"    Column: {conflict['column']}")
                console.print(f"    Source type: {conflict['source_type']}")
                console.print(f"    Target type: {conflict['target_type']}")
        
        # Summary
        if dry_run:
            console.print("\n[yellow]DRY RUN completed. No changes were made.[/yellow]")
            console.print("[blue]Run without --dry-run to apply these changes.[/blue]")
        else:
            console.print("\n[green]✓ Structure merge completed successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Error merging branches: {e}[/red]")
        raise typer.Exit(1)


@app.command("add")
def add_cmd(
    table: str = typer.Argument(..., help="Table name"),
    data: str = typer.Argument(..., help="JSON data to insert (e.g., '{\"name\": \"Widget\", \"price\": 19.99}')"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: str = typer.Option(None, "--backend", "-b", help="Database backend"),
    id: str = typer.Option(None, "--id", help="Explicit row ID (auto-generated if not provided)"),
):
    """Add data using the modern API (auto-generated IDs, type inference)."""
    _add_implementation(table, data, path, backend, id)




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


def _add_implementation(table: str, data: str, path: str, backend: str, id: str) -> None:
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
            id=id
        )
        
        if id is not None:
            console.print(f"[green]Added data to id {result_id} in table '{table}'[/green]")
        else:
            console.print(f"[green]Added data with auto-generated ID {result_id} in table '{table}'[/green]")
            
    except Exception as e:
        console.print(f"[red]Error adding data: {e}[/red]")
        raise typer.Exit(1)


# Query commands
@query_app.command("create")
def query_create(
    name: str = typer.Argument(..., help="Query name"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="SQL query text"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File containing SQL query"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Query description"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="Database backend"),
    connection_name: Optional[str] = typer.Option(None, "--connection", "-c", help="Named connection")
) -> None:
    """Create a new saved query."""
    try:
        # Get query text
        if file:
            if not file.exists():
                console.print(f"[red]Query file '{file}' not found[/red]")
                raise typer.Exit(1)
            query_text = file.read_text().strip()
        elif query:
            query_text = query
        else:
            console.print("[red]Either --query or --file must be provided[/red]")
            raise typer.Exit(1)
        
        if not query_text:
            console.print("[red]Query text cannot be empty[/red]")
            raise typer.Exit(1)
        
        # Build connection
        connection_info = build_connection_info(path, backend, connection_name)
        db = connect(connection_info, backend)
        
        # Create the query
        saved_query = db.queries.create_query(
            name=name,
            query_text=query_text,
            description=description
        )
        
        console.print(f"[green]Created saved query '{name}' with ID {saved_query.id}[/green]")
        if description:
            console.print(f"[blue]Description: {description}[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error creating query: {e}[/red]")
        raise typer.Exit(1)


@query_app.command("list")
def query_list(
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="Database backend"),
    connection_name: Optional[str] = typer.Option(None, "--connection", "-c", help="Named connection"),
    include_deleted: bool = typer.Option(False, "--include-deleted", help="Include soft-deleted queries")
) -> None:
    """List all saved queries."""
    try:
        # Build connection
        connection_info = build_connection_info(path, backend, connection_name)
        db = connect(connection_info, backend)
        
        # Get queries
        queries = db.queries.list_queries(include_deleted=include_deleted)
        
        if not queries:
            console.print("[yellow]No saved queries found[/yellow]")
            return
        
        # Display queries in a table
        table = Table(title="Saved Queries")
        table.add_column("Name", style="green")
        table.add_column("Description", style="cyan")
        table.add_column("Parameters", style="yellow")
        table.add_column("Created", style="blue")
        if include_deleted:
            table.add_column("Status", style="red")
        
        for query in queries:
            param_names = [p.name for p in query.parameters] if query.parameters else []
            param_str = ", ".join(param_names) if param_names else "None"
            
            row = [
                query.name,
                query.description or "",
                param_str,
                query.created_at or ""
            ]
            
            if include_deleted:
                status = "Deleted" if query.deleted_at else "Active"
                row.append(status)
            
            table.add_row(*row)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error listing queries: {e}[/red]")
        raise typer.Exit(1)


@query_app.command("show")
def query_show(
    name: str = typer.Argument(..., help="Query name"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="Database backend"),
    connection_name: Optional[str] = typer.Option(None, "--connection", "-c", help="Named connection")
) -> None:
    """Show details of a specific saved query."""
    try:
        # Build connection
        connection_info = build_connection_info(path, backend, connection_name)
        db = connect(connection_info, backend)
        
        # Get the query
        query = db.queries.get_query(name)
        if not query:
            console.print(f"[red]Query '{name}' not found[/red]")
            raise typer.Exit(1)
        
        # Display query details
        console.print(f"[bold green]Query: {query.name}[/bold green]")
        console.print(f"[bold]ID:[/bold] {query.id}")
        if query.description:
            console.print(f"[bold]Description:[/bold] {query.description}")
        console.print(f"[bold]Created:[/bold] {query.created_at}")
        console.print(f"[bold]Updated:[/bold] {query.updated_at}")
        
        # Show parameters
        if query.parameters:
            console.print(f"\n[bold yellow]Parameters:[/bold yellow]")
            param_table = Table()
            param_table.add_column("Name", style="green")
            param_table.add_column("Type", style="cyan")
            param_table.add_column("Required", style="yellow")
            param_table.add_column("Default", style="blue")
            param_table.add_column("Description", style="white")
            
            for param in query.parameters:
                param_table.add_row(
                    param.name,
                    param.data_type,
                    "Yes" if param.is_required else "No",
                    param.default_value or "",
                    param.description or ""
                )
            console.print(param_table)
        
        # Show query text
        console.print(f"\n[bold yellow]Query Text:[/bold yellow]")
        syntax = Syntax(query.query_text, "sql", theme="monokai", line_numbers=True)
        console.print(syntax)
        
    except Exception as e:
        console.print(f"[red]Error showing query: {e}[/red]")
        raise typer.Exit(1)


@query_app.command("exec")
def query_exec(
    name: str = typer.Argument(..., help="Query name"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="Database backend"),
    connection_name: Optional[str] = typer.Option(None, "--connection", "-c", help="Named connection"),
    param: Optional[List[str]] = typer.Option(None, "--param", help="Parameter as name=value")
) -> None:
    """Execute a saved query with parameters."""
    try:
        # Build connection
        connection_info = build_connection_info(path, backend, connection_name)
        db = connect(connection_info, backend)
        
        # Parse parameters
        params = {}
        if param:
            for p in param:
                if "=" not in p:
                    console.print(f"[red]Invalid parameter format: '{p}'. Use name=value[/red]")
                    raise typer.Exit(1)
                key, value = p.split("=", 1)
                params[key.strip()] = value.strip()
        
        # Execute the query
        results = db.queries.execute_query(name, **params)
        
        if not results:
            console.print("[yellow]Query returned no results[/yellow]")
            return
        
        # Display results in a table
        if results:
            keys = list(results[0].keys())
            table = Table(title=f"Results for '{name}'")
            
            for key in keys:
                table.add_column(key, style="green")
            
            for row in results:
                table.add_row(*[str(row.get(key, "")) for key in keys])
            
            console.print(table)
            console.print(f"\n[blue]Returned {len(results)} rows[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error executing query: {e}[/red]")
        raise typer.Exit(1)


@query_app.command("delete")
def query_delete(
    name: str = typer.Argument(..., help="Query name"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="Database backend"),
    connection_name: Optional[str] = typer.Option(None, "--connection", "-c", help="Named connection"),
    hard: bool = typer.Option(False, "--hard", help="Permanently delete (cannot be undone)")
) -> None:
    """Delete a saved query."""
    try:
        # Build connection
        connection_info = build_connection_info(path, backend, connection_name)
        db = connect(connection_info, backend)
        
        # Confirm deletion
        delete_type = "permanently delete" if hard else "soft delete"
        if not typer.confirm(f"Are you sure you want to {delete_type} query '{name}'?"):
            console.print("[yellow]Deletion cancelled[/yellow]")
            return
        
        # Delete the query
        deleted = db.queries.delete_query(name, hard_delete=hard)
        
        if deleted:
            action = "permanently deleted" if hard else "soft deleted"
            console.print(f"[green]Query '{name}' {action}[/green]")
        else:
            console.print(f"[red]Query '{name}' not found[/red]")
            raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]Error deleting query: {e}[/red]")
        raise typer.Exit(1)


# API commands
@api_app.command("serve")
def api_serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload for development"),
) -> None:
    """Start the SynthDB API server."""
    try:
        from .api_server import start_server
        console.print(f"[green]Starting SynthDB API server on {host}:{port}[/green]")
        if reload:
            console.print("[yellow]Auto-reload enabled (development mode)[/yellow]")
        start_server(host=host, port=port, reload=reload)
    except ImportError:
        console.print("[red]API server dependencies not installed. Install with: pip install synthdb[api][/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error starting API server: {e}[/red]")
        raise typer.Exit(1)


@api_app.command("test")
def api_test(
    url: str = typer.Option("http://localhost:8000", "--url", "-u", help="API server URL"),
    database: str = typer.Option("test.db", "--database", "-d", help="Database name to test"),
) -> None:
    """Test connection to SynthDB API server."""
    try:
        from .api_client import connect_remote
        
        console.print(f"[blue]Testing connection to {url}[/blue]")
        
        with connect_remote(url, database) as client:
            # Test basic functionality
            try:
                client.init_db(force=True)
                console.print("[green]✓ Database initialization successful[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠ Database init: {e}[/yellow]")
            
            info = client.get_info()
            console.print(f"[green]✓ Connection successful[/green]")
            console.print(f"[blue]Database: {database}[/blue]")
            console.print(f"[blue]Tables: {info.get('tables_count', 0)}[/blue]")
            
    except ImportError:
        console.print("[red]API client dependencies not installed. Install with: pip install synthdb[api][/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error connecting to API server: {e}[/red]")
        raise typer.Exit(1)


# Models commands
@models_app.command("generate")
def models_generate(
    output: str = typer.Argument(..., help="Output file path"),
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="Database backend"),
    connection_name: Optional[str] = typer.Option(None, "--connection", "-c", help="Named connection"),
    template: str = typer.Option("pydantic", "--template", "-t", help="Model template (pydantic, dataclass)"),
    include_queries: bool = typer.Option(False, "--include-queries", help="Include saved query models"),
) -> None:
    """Generate type-safe models from database schema."""
    try:
        # Build connection
        connection_info = build_connection_info(path, backend, connection_name)
        db = connect(connection_info, backend)
        
        console.print(f"[blue]Generating models from database: {path}[/blue]")
        
        # Generate code
        from .models import ModelGenerator
        generator = ModelGenerator(db)
        
        # Get all tables
        tables = db.list_tables()
        console.print(f"[blue]Found {len(tables)} tables[/blue]")
        
        # Generate Python code
        code_lines = [
            '"""Auto-generated models for SynthDB."""',
            '',
            'from datetime import datetime',
            'from typing import Optional, List',
            'from pydantic import BaseModel, Field',
            '',
            'from synthdb.models import SynthDBModel',
            '',
        ]
        
        # Generate model for each table
        for table in tables:
            table_name = table['name']
            console.print(f"[blue]  - Generating model for '{table_name}'[/blue]")
            
            # Get columns
            columns = db.list_columns(table_name)
            
            # Generate base class with 'Base' suffix
            class_name = generator._table_name_to_class_name(table_name)
            base_class_name = f"{class_name}Base"
            
            code_lines.extend([
                f'class {base_class_name}(SynthDBModel):',
                f'    """Base model for {table_name} table (auto-generated)."""',
                f'    __table_name__ = "{table_name}"',
                '',
            ])
            
            # Add fields for each column (excluding base fields)
            for col in columns:
                if col['name'] in ('id', 'created_at', 'updated_at'):
                    continue
                
                python_type = generator._map_synthdb_type(col['data_type'])
                type_name = python_type.__name__
                if type_name == 'datetime':
                    type_name = 'datetime'
                
                code_lines.append(f'    {col["name"]}: Optional[{type_name}] = Field(None, description="Column from {table_name} table")')
            
            code_lines.extend(['', ''])
        
        # Include saved queries if requested
        if include_queries:
            try:
                queries = db.queries.list_queries()
                console.print(f"[blue]Found {len(queries)} saved queries[/blue]")
                
                for query in queries:
                    console.print(f"[blue]  - Generating model for query '{query.name}'[/blue]")
                    
                    class_name = generator._query_name_to_class_name(query.name)
                    code_lines.extend([
                        f'class {class_name}(SynthDBModel):',
                        f'    """Model for saved query \'{query.name}\'."""',
                        f'    __query_name__ = "{query.name}"',
                        f'    # Note: Fields will be validated at runtime based on query results',
                        '',
                        ''
                    ])
            except Exception as e:
                console.print(f"[yellow]Warning: Could not process saved queries: {e}[/yellow]")
        
        # Add usage example at the end
        code_lines.extend([
            '',
            '# Example: Extending base models with relationships',
            '# Create a separate file (e.g., models.py) with your customizations:',
            '#',
            '# from .generated_models import UserBase, PostBase',
            '# ',
            '# class User(UserBase):',
            '#     @property',
            '#     def posts(self):',
            '#         """Get all posts by this user."""',
            '#         from . import Post',
            '#         if not self.id:',
            '#             return []',
            '#         return Post.find_all(f"user_id = \'{self.id}\'")',
            '# ',
            '# class Post(PostBase):',
            '#     @property',
            '#     def user(self):',
            '#         """Get the author of this post."""',
            '#         from . import User',
            '#         if not self.user_id:',
            '#             return None',
            '#         return User.find_by_id(self.user_id)',
        ])
        
        # Write to file
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(code_lines))
        
        console.print(f"[green]Models generated successfully: {output}[/green]")
        console.print(f"[blue]Generated {len(tables)} table models[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error generating models: {e}[/red]")
        raise typer.Exit(1)


@models_app.command("test")
def models_test(
    path: str = typer.Option("db.db", "--path", "-p", help="Database file path"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="Database backend"),
    connection_name: Optional[str] = typer.Option(None, "--connection", "-c", help="Named connection"),
) -> None:
    """Test type-safe models functionality."""
    try:
        # Build connection with models enabled
        connection_info = build_connection_info(path, backend, connection_name)
        db = connect(connection_info, backend, models=True)
        
        console.print(f"[blue]Testing models functionality with database: {path}[/blue]")
        
        # Generate models
        models = db.generate_models()
        console.print(f"[green]✓ Generated {len(models)} models[/green]")
        
        # Show available models
        table = Table(title="Generated Models")
        table.add_column("Model Class", style="green")
        table.add_column("Table Name", style="cyan")
        
        for model_name, model_class in models.items():
            table_name = model_class.get_table_name()
            table.add_row(model_name, table_name)
        
        console.print(table)
        
        console.print("[green]✓ Models functionality working correctly[/green]")
        
    except Exception as e:
        console.print(f"[red]Error testing models: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
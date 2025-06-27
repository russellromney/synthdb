"""View creation and management for SynthDB."""

from .types import get_type_table_name
from .backends import get_backend
from .config import config


def create_table_views(db_path: str = 'db.db', backend_name: str = None, backend=None, connection=None):
    """Create SQLite views for each table using versioned storage with soft deletes."""
    # Use provided backend and connection, or create new ones
    if backend is not None and connection is not None:
        db = connection
        own_connection = False
    else:
        # Get the appropriate backend
        backend_to_use = backend_name or config.get_backend_for_path(db_path)
        backend = get_backend(backend_to_use)
        db = backend.connect(db_path)
        own_connection = True
    
    try:
        # Get all active tables
        tables_query = """
            SELECT id, name FROM table_definitions 
            WHERE deleted_at IS NULL
        """
        cur = backend.execute(db, tables_query)
        tables = backend.fetchall(cur)
    
        for table in tables:
            table_id = table['id']
            table_name = table['name']
            # Get columns for this table
            columns_query = """
                SELECT id, name, data_type FROM column_definitions 
                WHERE table_id = ? AND deleted_at IS NULL
                ORDER BY id
            """
            cur = backend.execute(db, columns_query, (table_id,))
            columns = backend.fetchall(cur)
        
            # Build the view SQL
            view_name = table_name
            
            # Drop existing view
            drop_view_sql = f"DROP VIEW IF EXISTS {view_name}"
            
            if not columns:
                # Create a basic view with just row_id for tables with no columns
                create_view_sql = f"""
                    CREATE VIEW {view_name} AS
                    SELECT 
                        NULL as row_id,
                        NULL as created_at,
                        NULL as updated_at
                    WHERE 1=0
                """
                print(f"Creating empty view for table: {table_name}")
                backend.execute(db, drop_view_sql)
                backend.execute(db, create_view_sql)
                continue
        
            # Generate optimized view SQL with row_metadata JOINs
            column_selects = []
            table_joins = []
            
            for col in columns:
                type_table = get_type_table_name(col['data_type'])
                alias = f"{type_table}_{col['id']}"
                
                # LEFT JOIN to value tables for current values only (no delete filtering needed)
                table_joins.append(f"""
                    LEFT JOIN {type_table} {alias} ON 
                        rm.row_id = {alias}.row_id AND 
                        {alias}.table_id = {table_id} AND 
                        {alias}.column_id = {col['id']} AND
                        {alias}.is_current = 1
                """)
                
                # All types are now simplified - no special boolean handling needed
                column_selects.append(f'{alias}.value AS \"{col["name"]}\"')
            
            create_view_sql = f"""
                CREATE VIEW {view_name} AS
                SELECT 
                    rm.row_id,
                    {', '.join(column_selects) if column_selects else 'NULL as placeholder'},
                    rm.created_at,
                    rm.updated_at
                FROM row_metadata rm
                {' '.join(table_joins)}
                WHERE rm.table_id = {table_id} AND rm.is_deleted = 0
            """
            
            print(f"Creating view for table: {table_name}")
            backend.execute(db, drop_view_sql)
            backend.execute(db, create_view_sql)
        
        backend.commit(db)
    finally:
        if own_connection:
            backend.close(db)
"""View creation and management for SynthDB."""

import sqlite3
from .types import get_type_table_name
from .backends import get_backend
from .config import config


def create_table_views(db_path: str = 'db.db', backend_name: str = None):
    """Create SQLite views for each table using versioned storage with soft deletes."""
    # Get the appropriate backend
    backend_to_use = backend_name or config.get_backend_for_path(db_path)
    backend = get_backend(backend_to_use)
    
    db = backend.connect(db_path)
    
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
        
            # Generate optimized view SQL for versioned storage with soft delete support
            column_selects = []
            table_joins = []
            
            for col in columns:
                type_table = get_type_table_name(col['data_type'])
                alias = f"{type_table}_{col['id']}"
                
                # Only include non-deleted current values
                table_joins.append(f"""
                    LEFT JOIN {type_table} {alias} ON 
                        all_rows.row_id = {alias}.row_id AND 
                        {alias}.table_id = {table_id} AND 
                        {alias}.column_id = {col['id']} AND
                        {alias}.is_current = 1 AND 
                        {alias}.is_deleted = 0
                """)
                
                # Handle boolean display conversion
                if col['data_type'] == 'boolean':
                    column_selects.append(f"""
                        CASE WHEN {alias}.value = 1 THEN 'true' 
                             WHEN {alias}.value = 0 THEN 'false' 
                             ELSE NULL END AS \"{col['name']}\"
                    """)
                else:
                    column_selects.append(f'{alias}.value AS \"{col["name"]}\"')
            
            # Get all unique row_ids that have any current, non-deleted values
            union_queries = []
            for col in columns:
                type_table = get_type_table_name(col['data_type'])
                union_queries.append(f"""
                    SELECT DISTINCT row_id FROM {type_table} 
                    WHERE table_id = {table_id} AND is_current = 1 AND is_deleted = 0
                """)
            
            # Metadata columns - get earliest created_at and latest updated_at
            metadata_selects = []
            for col in columns:
                type_table = get_type_table_name(col['data_type'])
                alias = f"{type_table}_{col['id']}"
                metadata_selects.append(f"{alias}.created_at")
            
            create_view_sql = f"""
                CREATE VIEW {view_name} AS
                SELECT 
                    all_rows.row_id,
                    {', '.join(column_selects)},
                    MIN({', '.join(metadata_selects)}) as created_at,
                    MAX({', '.join(metadata_selects)}) as updated_at
                FROM (
                    {' UNION '.join(union_queries)}
                ) all_rows
                {' '.join(table_joins)}
                GROUP BY all_rows.row_id
                HAVING COUNT(*) > 0
            """
            
            print(f"Creating view for table: {table_name}")
            backend.execute(db, drop_view_sql)
            backend.execute(db, create_view_sql)
        
        backend.commit(db)
    finally:
        backend.close(db)
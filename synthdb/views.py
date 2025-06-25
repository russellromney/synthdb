"""View creation and management for SynthDB."""

import sqlite3
from .types import get_type_table_name
from .backends import get_backend
from .config import config


def create_table_views(db_path: str = 'db.db', backend_name: str = None):
    """Create SQLite views for each table in table_definitions"""
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
        
            # Create UNION query only for data types actually used by this table
            used_types = set(col['data_type'] for col in columns)
            union_parts = []
            for data_type in used_types:
                table_name_for_type = get_type_table_name(data_type)
                union_parts.append(f"""
                    SELECT row_id, column_id, value, '{data_type}' as value_type, created_at, updated_at
                    FROM {table_name_for_type}
                    WHERE table_id = {table_id} AND deleted_at IS NULL
                """)
            
            # Create pivot-style view that transforms type-specific data to columnar format
            select_parts = []
            for col in columns:
                col_id = col['id']
                col_name = col['name']
                data_type = col['data_type']
                # Cast values appropriately based on their original type
                if data_type == 'boolean':
                    select_parts.append(f"""
                        MAX(CASE WHEN cd.name = '{col_name}' THEN 
                            CASE WHEN uv.value = '1' THEN 'true' ELSE 'false' END 
                        END) AS {col_name}""")
                else:
                    select_parts.append(f"""
                        MAX(CASE WHEN cd.name = '{col_name}' THEN uv.value END) AS {col_name}""")
        
            create_view_sql = f"""
                CREATE VIEW {view_name} AS
                SELECT 
                    uv.row_id,
                    MIN(uv.created_at) as created_at,
                    MAX(uv.updated_at) as updated_at,{','.join(select_parts)}
                FROM (
                    {' UNION ALL '.join(union_parts)}
                ) uv
                JOIN table_definitions td ON uv.row_id IS NOT NULL
                JOIN column_definitions cd ON uv.column_id = cd.id
                WHERE td.id = {table_id}
                    AND td.deleted_at IS NULL
                    AND cd.deleted_at IS NULL
                    AND cd.table_id = {table_id}
                GROUP BY uv.row_id
            """
            
            print(f"Creating view for table: {table_name}")
            backend.execute(db, drop_view_sql)
            backend.execute(db, create_view_sql)
        
        backend.commit(db)
    finally:
        backend.close(db)
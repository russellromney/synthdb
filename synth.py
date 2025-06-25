import sqlite3
import json

def get_type_table_name(data_type, is_history=False):
    """Get the appropriate table name for a given data type"""
    type_map = {
        'text': 'text_values',
        'boolean': 'boolean_values', 
        'real': 'real_values',
        'integer': 'integer_values',
        'json': 'json_values',
        'timestamp': 'timestamp_values'
    }
    
    if is_history:
        return type_map[data_type].replace('_values', '_value_history')
    return type_map[data_type]

def insert_typed_value(row_id, table_id, column_id, value, data_type):
    """Insert a value into the appropriate type-specific table"""
    table_name = get_type_table_name(data_type)
    history_table_name = get_type_table_name(data_type, is_history=True)
    
    # Convert value to appropriate type
    if data_type == 'boolean':
        value = 1 if value else 0
    elif data_type == 'json':
        value = json.dumps(value) if not isinstance(value, str) else value
    
    # Insert into main table
    statement = f"""
        INSERT INTO {table_name} (row_id, table_id, column_id, value)
        VALUES (?, ?, ?, ?)
    """
    db = sqlite3.connect('db.db')
    db.cursor().execute(statement, (row_id, table_id, column_id, value))
    db.commit()
    
    # Insert into history table
    history_statement = f"""
        INSERT INTO {history_table_name} (row_id, table_id, column_id, value)
        VALUES (?, ?, ?, ?)
    """
    db.cursor().execute(history_statement, (row_id, table_id, column_id, value))
    db.commit()
    db.close()

def do_statement(s: str,many: bool = False):
    db = sqlite3.connect('db.db')
    print(s)
    if many:
        db.cursor().executescript(s)
    else: 
        db.cursor().execute(s)
    db.commit()
    db.close()


def make_db():
    statement = '''
        drop table if exists table_definitions
    '''
    do_statement(statement)
    statement = '''
        create table table_definitions(
            id int primary key, 
            version int,
            created_at timestamp default current_timestamp, 
            deleted_at timestamp,
            name text
        )
    '''
    do_statement(statement)

    statement = '''
        drop table if exists column_definitions
    '''
    do_statement(statement)
    statement = '''
        create table column_definitions(
            id int primary key,
            table_id int,
            version int,
            created_at int default current_timestamp, 
            deleted_at int,
            name text,
            data_type text
        )
    '''
    do_statement(statement)
    
    # Create type-specific history tables
    history_type_tables = [
        ('text_value_history', 'text'),
        ('boolean_value_history', 'boolean'),
        ('real_value_history', 'real'),
        ('integer_value_history', 'integer'),
        ('json_value_history', 'json'),
        ('timestamp_value_history', 'timestamp')
    ]
    
    for table_name, data_type in history_type_tables:
        statement = f'''
            drop table if exists {table_name}
        '''
        do_statement(statement)
        
        statement = f'''
            create table {table_name}(
                row_id int,
                table_id int,
                column_id int,
                created_at timestamp default current_timestamp,
                value {data_type}
            )
        '''
        do_statement(statement)

    # Create type-specific value tables
    type_tables = [
        ('text_values', 'text'),
        ('boolean_values', 'boolean'),
        ('real_values', 'real'),
        ('integer_values', 'integer'),
        ('json_values', 'json'),
        ('timestamp_values', 'timestamp')
    ]
    
    for table_name, data_type in type_tables:
        statement = f'''
            drop table if exists {table_name}
        '''
        do_statement(statement)
        
        statement = f'''
            create table {table_name}(
                row_id int,
                table_id int,
                column_id int,
                created_at timestamp default current_timestamp,
                updated_at timestamp default current_timestamp, 
                deleted_at timestamp,
                value {data_type}
            )
        '''
        do_statement(statement)


def create_table_views():
    """Create SQLite views for each table in table_definitions"""
    db = sqlite3.connect('db.db')
    cur = db.cursor()
    
    # Get all active tables
    tables_query = """
        SELECT id, name FROM table_definitions 
        WHERE deleted_at IS NULL
    """
    tables = cur.execute(tables_query).fetchall()
    
    for table_id, table_name in tables:
        # Get columns for this table
        columns_query = """
            SELECT id, name, data_type FROM column_definitions 
            WHERE table_id = ? AND deleted_at IS NULL
            ORDER BY id
        """
        columns = cur.execute(columns_query, (table_id,)).fetchall()
        
        if not columns:
            continue
            
        # Build the view SQL
        view_name = table_name
        
        # Drop existing view
        drop_view_sql = f"DROP VIEW IF EXISTS {view_name}"
        
        # Create UNION query only for data types actually used by this table
        used_types = set(data_type for _, _, data_type in columns)
        union_parts = []
        for data_type in used_types:
            table_name_for_type = get_type_table_name(data_type)
            union_parts.append(f"""
                SELECT row_id, column_id, value, '{data_type}' as value_type
                FROM {table_name_for_type}
                WHERE table_id = {table_id} AND deleted_at IS NULL
            """)
        
        # Create pivot-style view that transforms type-specific EAV to columnar format
        select_parts = []
        for col_id, col_name, data_type in columns:
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
                uv.row_id,{','.join(select_parts)}
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
        cur.execute(drop_view_sql)
        cur.execute(create_view_sql)
    
    db.commit()
    db.close()


def make_values():
    # add a couple tables
    statement = """
        insert into table_definitions (id, version, name)
        values
            (0, 0, 'users'),
            (1, 0, 'pets')
    """
    do_statement(statement)

    # add some columns to the tables with different data types
    statement = """
        insert into column_definitions (id, table_id, version, name, data_type)
        values
            (0, 0, 0, 'first_name', 'text'),
            (1, 0, 0, 'last_name', 'text'),
            (2, 0, 0, 'age', 'integer'),
            (3, 0, 0, 'active', 'boolean'),
            (4, 1, 0, 'name', 'text'),
            (5, 1, 0, 'species', 'text'),
            (6, 1, 0, 'weight', 'real'),
            (7, 1, 0, 'vaccinated', 'boolean')
    """
    do_statement(statement)

    # Insert typed values using the helper function
    # Users data
    insert_typed_value(0, 0, 0, 'John', 'text')
    insert_typed_value(0, 0, 1, 'Smith', 'text') 
    insert_typed_value(0, 0, 2, 30, 'integer')
    insert_typed_value(0, 0, 3, True, 'boolean')
    
    insert_typed_value(1, 0, 0, 'Jane', 'text')
    insert_typed_value(1, 0, 1, 'Jones', 'text')
    insert_typed_value(1, 0, 2, 25, 'integer')
    insert_typed_value(1, 0, 3, False, 'boolean')
    
    # Pets data
    insert_typed_value(0, 1, 4, 'Doggo', 'text')
    insert_typed_value(0, 1, 5, 'dog', 'text')
    insert_typed_value(0, 1, 6, 25.5, 'real')
    insert_typed_value(0, 1, 7, True, 'boolean')
    
    insert_typed_value(1, 1, 4, 'Catsy', 'text')
    insert_typed_value(1, 1, 5, 'cat', 'text')
    insert_typed_value(1, 1, 6, 4.2, 'real')
    insert_typed_value(1, 1, 7, False, 'boolean')

    
def ask():
    db = sqlite3.connect('db.db')
    cur = db.cursor()
    
    # Show data from type-specific tables
    print("=== Type-specific table data ===")
    for data_type in ['text', 'boolean', 'real', 'integer']:
        table_name = get_type_table_name(data_type)
        s = f"SELECT * FROM {table_name}"
        print(f"\n--- {table_name} ---")
        print(s)
        try:
            out = cur.execute(s).fetchall()
            for x in out:
                print(dict(zip([c[0] for c in cur.description], x)))
        except Exception as e:
            print(f"Error querying {table_name}: {e}")
    
    # Show joined data with type information
    print("\n=== Joined data with types ===")
    s = """
        SELECT 
            'text' as type, tv.row_id, tv.table_id, tv.column_id, tv.value,
            td.name as table_name, cd.name as column_name, cd.data_type
        FROM text_values tv
        JOIN table_definitions td ON tv.table_id = td.id
        JOIN column_definitions cd ON tv.column_id = cd.id
        WHERE td.deleted_at IS NULL AND cd.deleted_at IS NULL AND tv.deleted_at IS NULL
        
        UNION ALL
        
        SELECT 
            'integer' as type, iv.row_id, iv.table_id, iv.column_id, 
            CAST(iv.value AS TEXT) as value,
            td.name as table_name, cd.name as column_name, cd.data_type
        FROM integer_values iv
        JOIN table_definitions td ON iv.table_id = td.id
        JOIN column_definitions cd ON iv.column_id = cd.id
        WHERE td.deleted_at IS NULL AND cd.deleted_at IS NULL AND iv.deleted_at IS NULL
        
        UNION ALL
        
        SELECT 
            'boolean' as type, bv.row_id, bv.table_id, bv.column_id,
            CASE WHEN bv.value = 1 THEN 'true' ELSE 'false' END as value,
            td.name as table_name, cd.name as column_name, cd.data_type
        FROM boolean_values bv
        JOIN table_definitions td ON bv.table_id = td.id
        JOIN column_definitions cd ON bv.column_id = cd.id
        WHERE td.deleted_at IS NULL AND cd.deleted_at IS NULL AND bv.deleted_at IS NULL
        
        UNION ALL
        
        SELECT 
            'real' as type, rv.row_id, rv.table_id, rv.column_id,
            CAST(rv.value AS TEXT) as value,
            td.name as table_name, cd.name as column_name, cd.data_type
        FROM real_values rv
        JOIN table_definitions td ON rv.table_id = td.id
        JOIN column_definitions cd ON rv.column_id = cd.id
        WHERE td.deleted_at IS NULL AND cd.deleted_at IS NULL AND rv.deleted_at IS NULL
        
        ORDER BY table_name, row_id, column_name
    """
    print(s)
    out = cur.execute(s).fetchall()
    for x in out:
        print(dict(zip([c[0] for c in cur.description], x)))


    # Show column definitions with their types
    print("\n=== Column Definitions ===")
    s = """
        SELECT 
            c.id as column_id,
            c.name as column_name, 
            c.data_type,
            t.name as table_name
        FROM column_definitions c
        JOIN table_definitions t on c.table_id = t.id 
        ORDER BY t.name, c.id
    """
    print(s)
    out = cur.execute(s).fetchall()
    for x in out:
        print(dict(zip([c[0] for c in cur.description], x)))

    # Test the created views
    print("\n=== Testing Type-Specific Views ===")
    
    # Get all view names (same as table names)
    views_query = """
        SELECT name FROM table_definitions 
        WHERE deleted_at IS NULL
    """
    views = cur.execute(views_query).fetchall()
    
    for (view_name,) in views:
        print(f"\n--- {view_name} view ---")
        view_query = f"SELECT * FROM {view_name}"
        print(view_query)
        try:
            view_results = cur.execute(view_query).fetchall()
            for row in view_results:
                print(dict(zip([c[0] for c in cur.description], row)))
        except Exception as e:
            print(f"Error querying view {view_name}: {e}")
    
    db.close()


def create_table(table_name):
    """Create a new table definition"""
    db = sqlite3.connect('db.db')
    cur = db.cursor()
    
    # Get the next table ID
    cur.execute("SELECT COALESCE(MAX(id), -1) + 1 FROM table_definitions")
    table_id = cur.fetchone()[0]
    
    # Insert the new table
    cur.execute("""
        INSERT INTO table_definitions (id, version, name)
        VALUES (?, 0, ?)
    """, (table_id, table_name))
    
    db.commit()
    db.close()
    return table_id


def add_column(table_name, column_name, data_type):
    """Add a column to an existing table"""
    db = sqlite3.connect('db.db')
    cur = db.cursor()
    
    # Get table ID
    cur.execute("SELECT id FROM table_definitions WHERE name = ? AND deleted_at IS NULL", (table_name,))
    result = cur.fetchone()
    if not result:
        raise ValueError(f"Table '{table_name}' not found")
    table_id = result[0]
    
    # Get next column ID
    cur.execute("SELECT COALESCE(MAX(id), -1) + 1 FROM column_definitions")
    column_id = cur.fetchone()[0]
    
    # Insert the new column
    cur.execute("""
        INSERT INTO column_definitions (id, table_id, version, name, data_type)
        VALUES (?, ?, 0, ?, ?)
    """, (column_id, table_id, column_name, data_type))
    
    db.commit()
    db.close()
    
    # Recreate views to include the new column
    create_table_views()
    return column_id


def query_view(view_name, where_clause=None):
    """Run a query on a view with optional WHERE clause"""
    db = sqlite3.connect('db.db')
    cur = db.cursor()
    
    # Build the query
    query = f"SELECT * FROM {view_name}"
    if where_clause:
        query += f" WHERE {where_clause}"
    
    try:
        results = cur.execute(query).fetchall()
        columns = [desc[0] for desc in cur.description]
        db.close()
        return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        db.close()
        raise e


def export_table_structure(table_name):
    """Export the structure of a table in SQLite CREATE TABLE format"""
    db = sqlite3.connect('db.db')
    cur = db.cursor()
    
    # Get table ID
    cur.execute("SELECT id FROM table_definitions WHERE name = ? AND deleted_at IS NULL", (table_name,))
    result = cur.fetchone()
    if not result:
        raise ValueError(f"Table '{table_name}' not found")
    table_id = result[0]
    
    # Get columns for this table
    cur.execute("""
        SELECT name, data_type FROM column_definitions 
        WHERE table_id = ? AND deleted_at IS NULL
        ORDER BY id
    """, (table_id,))
    columns = cur.fetchall()
    
    db.close()
    
    if not columns:
        return f"-- Table '{table_name}' has no columns"
    
    # Build CREATE TABLE statement
    column_defs = []
    for col_name, data_type in columns:
        # Map our internal types to SQLite types
        sqlite_type = {
            'text': 'TEXT',
            'integer': 'INTEGER', 
            'real': 'REAL',
            'boolean': 'INTEGER',  # SQLite doesn't have native boolean
            'json': 'TEXT',
            'timestamp': 'TIMESTAMP'
        }.get(data_type, 'TEXT')
        
        column_defs.append(f"    {col_name} {sqlite_type}")
    
    create_statement = f"CREATE TABLE {table_name} (\n" + ",\n".join(column_defs) + "\n);"
    return create_statement


    
if __name__ == "__main__": 
    make_db()
    make_values()
    create_table_views()
    ask()
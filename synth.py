import sqlite3

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
    
    statement = '''
        drop table if exists column_value_history
    '''
    do_statement(statement)
    statement = '''
        create table column_value_history(
            row_id int,
            table_id int,
            column_id int,
            created_at int default current_timestamp,
            value text
        )
    '''
    do_statement(statement)

    statement = '''
        drop table if exists column_values
    '''
    do_statement(statement)
    statement = '''
        create table column_values(
            row_id int,
            table_id int,
            column_id int,
            created_at int default current_timestamp,
            updated_at int default current_timestamp, 
            deleted_at int,
            value text
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
        
        # Create pivot-style view that transforms EAV to columnar format
        select_parts = []
        for col_id, col_name, data_type in columns:
            select_parts.append(f"""
                MAX(CASE WHEN cd.name = '{col_name}' THEN cv.value END) AS {col_name}""")
        
        create_view_sql = f"""
            CREATE VIEW {view_name} AS
            SELECT 
                cv.row_id,{','.join(select_parts)}
            FROM column_values cv
            JOIN table_definitions td ON cv.table_id = td.id
            JOIN column_definitions cd ON cv.column_id = cd.id
            WHERE td.id = {table_id}
                AND td.deleted_at IS NULL
                AND cd.deleted_at IS NULL
                AND cv.deleted_at IS NULL
            GROUP BY cv.row_id
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

    # add some columns to the tables
    statement = """
        insert into column_definitions (id, table_id, version, name, data_type)
        values
            (0, 0, 0, 'first_name', 'text'),
            (1, 0, 0, 'last_name', 'text'),
            (2, 1, 0, 'name', 'text'),
            (3, 1, 0, 'species', 'text')
    """
    do_statement(statement)

    # add some values for each column 
    statement = """
        begin transaction;
        insert into column_values (row_id, table_id, column_id, value)
        values
            (0, 0, 0, 'John'),
            (0, 0, 1, 'Smith'),
            (1, 0, 0, 'Jane'),
            (1, 0, 1, 'Jones'),
            (0, 1, 2, 'Doggo'),
            (0, 1, 3, 'dog'),
            (1, 1, 2, 'Catsy'),
            (1, 1, 3, 'cat')
        ;
        insert into column_value_history (row_id, table_id, column_id, value)
        values
            (0, 0, 0, 'John'),
            (0, 0, 1, 'Smith'),
            (1, 0, 0, 'Jane'),
            (1, 0, 1, 'Jones'),
            (0, 1, 2, 'Doggo'),
            (0, 1, 3, 'dog'),
            (1, 1, 2, 'Catsy'),
            (1, 1, 3, 'cat')
        ;
        commit;
    """
    do_statement(statement,True)

    
def ask():
    db = sqlite3.connect('db.db')
    s = """
        select * from column_values
    """
    print(s)
    cur = db.cursor()
    out = cur.execute(s).fetchall()
    for x in out:
        print(dict(zip([c[0] for c in cur.description],x)))
        
    s = """
        select * from column_values c 
        join table_definitions t on c.table_id = t.id 
        join column_definitions d on c.column_id = d.id
        where t.deleted_at is null
        and d.deleted_at is null
        and c.deleted_at is null
        and t.name = 'pets' 
    """
    print(s)
    cur = db.cursor()
    out = cur.execute(s).fetchall()
    for x in out:
        print(dict(zip([c[0] for c in cur.description],x)))


    # test out view
    s = """
        select 
            c.id as column_id,
            c.name as column_name, 
            c.data_type,
            t.name as table_name
        from column_definitions c
        join table_definitions t on c.table_id = t.id 
    """
    print(s)
    cur = db.cursor()
    out = cur.execute(s).fetchall()
    structure = dict(zip([c[0] for c in cur.description],x))

    col_str = ''.join([f""])
    s = """
        select 
            c.id as column_id,
            c.name as column_id, 
            c.data_type,
            t.name as table_name
        from column_definitions c
        join table_definitions t on c.table_id = t.id 
    """
    print(s)
    cur = db.cursor()
    out = cur.execute(s).fetchall()
    for x in out:
        print(dict(zip([c[0] for c in cur.description],x)))




    # s = """
    #     select d.name, d.data_type, c.* 
    #     from column_definitions c
    #     join table_definitions t on c.table_id = t.id 
    #     join column_definitions d on c.id = d.id
    #     where t.deleted_at is null
    #     and d.deleted_at is null
    #     and c.deleted_at is null
    #     and t.name = 'pets' 

    # """
    # print(s)
    # cur = db.cursor()
    # out = cur.execute(s).fetchall()
    # s = """
    #     select d.name, d.data_type, c.* 
    #     from column_values as c 
    #     join table_definitions t on c.table_id = t.id 
    #     join column_definitions d on c.column_id = d.id
    #     where t.deleted_at is null
    #     and d.deleted_at is null
    #     and c.deleted_at is null
    #     and t.name = 'pets' 
    # """
    # print(s)
    # out = db.cursor().execute(s).fetchall()
    # for x in out:
    #     print(dict(zip([c[0] for c in cur.description],x)))

    # Test the created views
    print("\n=== Testing Views ===")
    
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



    
if __name__ == "__main__": 
    make_db()
    make_values()
    create_table_views()
    ask()
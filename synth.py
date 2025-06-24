import sqlite3

def do_statement(s: str):
    db = sqlite3.connect('db.db')
    print(s)
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
            created_at timestamp, 
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
            created_at int, 
            deleted_at int,
            name text
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
            version int,
            created_at int, 
            deleted_at int,
            value text
        )
    '''
    do_statement(statement)


def make_values():
    # add a couple tables
    statement = """
        insert into table_definitions (id, version, created_at, name)
        values
            (0, 0, current_timestamp, 'users'),
            (1, 0, current_timestamp, 'pets')
    """
    do_statement(statement)

    # add some columns to the tables
    statement = """
        insert into column_definitions (id, table_id, version, created_at, name)
        values
            (0, 0, 0, current_timestamp, 'first_name'),
            (1, 0, 0, current_timestamp, 'last_name'),
            (2, 1, 0, current_timestamp, 'name'),
            (3, 1, 0, current_timestamp, 'species')
    """
    do_statement(statement)

    # add some values for each column 
    statement = """
        insert into column_values (row_id, table_id, column_id, version, created_at, value)
        values
            (0, 0, 0, 0, current_timestamp, 'John'),
            (1, 0, 1, 0, current_timestamp, 'Smith'),
            (2, 0, 0, 0, current_timestamp, 'Jane'),
            (3, 0, 1, 0, current_timestamp, 'Jones'),
            (4, 1, 0, 0, current_timestamp, 'Doggo'),
            (5, 1, 1, 0, current_timestamp, 'dog'),
            (6, 1, 0, 0, current_timestamp, 'Catsy'),
            (7, 1, 1, 0, current_timestamp, 'cat')
    """
    do_statement(statement)

    
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



    
if __name__ == "__main__": 
    make_db()
    make_values()
    ask()
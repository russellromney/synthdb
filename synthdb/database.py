"""Database setup and connection management for SynthDB."""

import sqlite3


def do_statement(s: str, many: bool = False, db_path: str = 'db.db'):
    """Execute a SQL statement on the database."""
    db = sqlite3.connect(db_path)
    print(s)
    if many:
        db.cursor().executescript(s)
    else: 
        db.cursor().execute(s)
    db.commit()
    db.close()


def make_db(db_path: str = 'db.db'):
    """Initialize the SynthDB database with all required tables."""
    
    # Create table_definitions table
    statement = '''
        drop table if exists table_definitions
    '''
    do_statement(statement, db_path=db_path)
    
    statement = '''
        create table table_definitions(
            id int primary key, 
            version int,
            created_at timestamp default current_timestamp, 
            deleted_at timestamp,
            name text
        )
    '''
    do_statement(statement, db_path=db_path)

    # Create column_definitions table
    statement = '''
        drop table if exists column_definitions
    '''
    do_statement(statement, db_path=db_path)
    
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
    do_statement(statement, db_path=db_path)
    
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
        do_statement(statement, db_path=db_path)
        
        statement = f'''
            create table {table_name}(
                row_id int,
                table_id int,
                column_id int,
                created_at timestamp default current_timestamp,
                value {data_type}
            )
        '''
        do_statement(statement, db_path=db_path)

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
        do_statement(statement, db_path=db_path)
        
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
        do_statement(statement, db_path=db_path)
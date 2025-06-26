"""Database schema creation for SynthDB."""

from typing import Dict, List
from .backends import DatabaseBackend


def get_schema_sql(backend: DatabaseBackend) -> Dict[str, List[str]]:
    """Get schema creation SQL for SQLite/Limbo backends."""
    return get_sqlite_schema()


def get_sqlite_schema() -> Dict[str, List[str]]:
    """SQLite/Limbo compatible schema."""
    return {
        "tables": [
            """
            CREATE TABLE IF NOT EXISTS table_definitions (
                id INTEGER PRIMARY KEY,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                name TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS column_definitions (
                id INTEGER PRIMARY KEY,
                table_id INTEGER,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                name TEXT NOT NULL,
                data_type TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS text_values (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                value TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS integer_values (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                value INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS real_values (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                value REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS boolean_values (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                value INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS json_values (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                value TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS timestamp_values (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                value TIMESTAMP
            )
            """,
        ],
        "history_tables": [
            """
            CREATE TABLE IF NOT EXISTS text_value_history (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS integer_value_history (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS real_value_history (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS boolean_value_history (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS json_value_history (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS timestamp_value_history (
                row_id TEXT,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value TIMESTAMP
            )
            """,
        ],
        "indexes": [
            # Performance indexes for efficient queries
            "CREATE INDEX IF NOT EXISTS idx_text_values_lookup ON text_values (table_id, column_id, row_id)",
            "CREATE INDEX IF NOT EXISTS idx_integer_values_lookup ON integer_values (table_id, column_id, row_id)",
            "CREATE INDEX IF NOT EXISTS idx_real_values_lookup ON real_values (table_id, column_id, row_id)",
            "CREATE INDEX IF NOT EXISTS idx_boolean_values_lookup ON boolean_values (table_id, column_id, row_id)",
            "CREATE INDEX IF NOT EXISTS idx_json_values_lookup ON json_values (table_id, column_id, row_id)",
            "CREATE INDEX IF NOT EXISTS idx_timestamp_values_lookup ON timestamp_values (table_id, column_id, row_id)",
            
            # Table and column lookup indexes
            "CREATE INDEX IF NOT EXISTS idx_table_definitions_name ON table_definitions (name)",
            "CREATE INDEX IF NOT EXISTS idx_column_definitions_lookup ON column_definitions (table_id, name)",
        ]
    }


def create_schema(backend: DatabaseBackend, connection) -> None:
    """Create the complete schema for the given backend."""
    schema = get_schema_sql(backend)
    
    # Create tables first
    for table_sql in schema["tables"]:
        backend.execute(connection, table_sql.strip())
    
    # Create history tables
    for history_sql in schema["history_tables"]:
        backend.execute(connection, history_sql.strip())
    
    # Create indexes
    for index_sql in schema["indexes"]:
        try:
            backend.execute(connection, index_sql.strip())
        except Exception as e:
            # Indexes might already exist, continue
            print(f"Warning: Could not create index: {e}")
    
    backend.commit(connection)
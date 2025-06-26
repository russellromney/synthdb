"""Database schema creation for SynthDB."""

from typing import Dict, List
from .backends import DatabaseBackend


def get_schema_sql(backend: DatabaseBackend) -> Dict[str, List[str]]:
    """Get schema creation SQL for SQLite/Limbo backends."""
    return get_sqlite_schema()


def get_sqlite_schema() -> Dict[str, List[str]]:
    """SQLite/Limbo compatible schema with versioned storage."""
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
                row_id TEXT NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value TEXT,
                is_current BOOLEAN DEFAULT 1,
                is_deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                PRIMARY KEY (row_id, table_id, column_id, version)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS integer_values (
                row_id TEXT NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value INTEGER,
                is_current BOOLEAN DEFAULT 1,
                is_deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                PRIMARY KEY (row_id, table_id, column_id, version)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS real_values (
                row_id TEXT NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value REAL,
                is_current BOOLEAN DEFAULT 1,
                is_deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                PRIMARY KEY (row_id, table_id, column_id, version)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS boolean_values (
                row_id TEXT NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value INTEGER,
                is_current BOOLEAN DEFAULT 1,
                is_deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                PRIMARY KEY (row_id, table_id, column_id, version)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS json_values (
                row_id TEXT NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value TEXT,
                is_current BOOLEAN DEFAULT 1,
                is_deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                PRIMARY KEY (row_id, table_id, column_id, version)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS timestamp_values (
                row_id TEXT NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value TIMESTAMP,
                is_current BOOLEAN DEFAULT 1,
                is_deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                PRIMARY KEY (row_id, table_id, column_id, version)
            )
            """,
        ],
        "indexes": [
            # Current value lookups (most common queries) - fast performance indexes only
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_text_current ON text_values (row_id, table_id, column_id) WHERE is_current = 1 AND is_deleted = 0",
            "CREATE INDEX IF NOT EXISTS idx_text_active ON text_values (table_id, column_id, row_id) WHERE is_current = 1 AND is_deleted = 0",
            
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_integer_current ON integer_values (row_id, table_id, column_id) WHERE is_current = 1 AND is_deleted = 0",
            "CREATE INDEX IF NOT EXISTS idx_integer_active ON integer_values (table_id, column_id, row_id) WHERE is_current = 1 AND is_deleted = 0",
            
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_real_current ON real_values (row_id, table_id, column_id) WHERE is_current = 1 AND is_deleted = 0",
            "CREATE INDEX IF NOT EXISTS idx_real_active ON real_values (table_id, column_id, row_id) WHERE is_current = 1 AND is_deleted = 0",
            
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_boolean_current ON boolean_values (row_id, table_id, column_id) WHERE is_current = 1 AND is_deleted = 0",
            "CREATE INDEX IF NOT EXISTS idx_boolean_active ON boolean_values (table_id, column_id, row_id) WHERE is_current = 1 AND is_deleted = 0",
            
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_json_current ON json_values (row_id, table_id, column_id) WHERE is_current = 1 AND is_deleted = 0",
            "CREATE INDEX IF NOT EXISTS idx_json_active ON json_values (table_id, column_id, row_id) WHERE is_current = 1 AND is_deleted = 0",
            
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_timestamp_current ON timestamp_values (row_id, table_id, column_id) WHERE is_current = 1 AND is_deleted = 0",
            "CREATE INDEX IF NOT EXISTS idx_timestamp_active ON timestamp_values (table_id, column_id, row_id) WHERE is_current = 1 AND is_deleted = 0",
            
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
    
    # Create indexes
    for index_sql in schema["indexes"]:
        try:
            backend.execute(connection, index_sql.strip())
        except Exception as e:
            # Indexes might already exist, continue
            print(f"Warning: Could not create index: {e}")
    
    backend.commit(connection)
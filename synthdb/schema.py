"""Database schema creation for SynthDB."""

from typing import Dict, List
from .backends import DatabaseBackend


def get_schema_sql(backend: DatabaseBackend) -> Dict[str, List[str]]:
    """Get schema creation SQL for SQLite backend."""
    return get_sqlite_schema()


def get_sqlite_schema() -> Dict[str, List[str]]:
    """SQLite schema with versioned storage."""
    return {
        "tables": [
            """
            CREATE TABLE IF NOT EXISTS table_definitions (
                id INTEGER PRIMARY KEY,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                deleted_at TEXT,
                name TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS column_definitions (
                id INTEGER PRIMARY KEY,
                table_id INTEGER,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                deleted_at TEXT,
                name TEXT NOT NULL,
                data_type TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS row_metadata (
                row_id TEXT PRIMARY KEY,
                table_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                deleted_at TEXT,
                is_deleted BOOLEAN DEFAULT 0,
                version INTEGER DEFAULT 1,
                FOREIGN KEY (table_id) REFERENCES table_definitions(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS text_values (
                row_id TEXT NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                value TEXT,
                is_current BOOLEAN DEFAULT 1,
                PRIMARY KEY (row_id, table_id, column_id, version)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS integer_values (
                row_id TEXT NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                value INTEGER,
                is_current BOOLEAN DEFAULT 1,
                PRIMARY KEY (row_id, table_id, column_id, version)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS real_values (
                row_id TEXT NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                value REAL,
                is_current BOOLEAN DEFAULT 1,
                PRIMARY KEY (row_id, table_id, column_id, version)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS timestamp_values (
                row_id TEXT NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
                value TEXT,
                is_current BOOLEAN DEFAULT 1,
                PRIMARY KEY (row_id, table_id, column_id, version)
            )
            """,
        ],
        "indexes": [
            # Row metadata indexes for efficient row lookups
            "CREATE INDEX IF NOT EXISTS idx_row_metadata_active ON row_metadata (table_id) WHERE is_deleted = 0",
            "CREATE INDEX IF NOT EXISTS idx_row_metadata_table_active ON row_metadata (table_id, row_id) WHERE is_deleted = 0",
            "CREATE INDEX IF NOT EXISTS idx_row_metadata_deleted ON row_metadata (deleted_at) WHERE is_deleted = 1",
            
            # Current value lookups (simplified without delete filtering)
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_text_current ON text_values (row_id, table_id, column_id) WHERE is_current = 1",
            "CREATE INDEX IF NOT EXISTS idx_text_active ON text_values (table_id, column_id, row_id) WHERE is_current = 1",
            
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_integer_current ON integer_values (row_id, table_id, column_id) WHERE is_current = 1",
            "CREATE INDEX IF NOT EXISTS idx_integer_active ON integer_values (table_id, column_id, row_id) WHERE is_current = 1",
            
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_real_current ON real_values (row_id, table_id, column_id) WHERE is_current = 1",
            "CREATE INDEX IF NOT EXISTS idx_real_active ON real_values (table_id, column_id, row_id) WHERE is_current = 1",
            
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_timestamp_current ON timestamp_values (row_id, table_id, column_id) WHERE is_current = 1",
            "CREATE INDEX IF NOT EXISTS idx_timestamp_active ON timestamp_values (table_id, column_id, row_id) WHERE is_current = 1",
            
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
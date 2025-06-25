"""Database schema creation optimized for different backends."""

from typing import Dict, List
from .backends import DatabaseBackend


def get_schema_sql(backend: DatabaseBackend) -> Dict[str, List[str]]:
    """Get schema creation SQL optimized for the specific backend."""
    
    # Base schema with backend-specific optimizations
    backend_name = backend.get_name()
    
    if backend_name == "postgresql":
        return get_postgresql_schema()
    elif backend_name == "mysql":
        return get_mysql_schema()
    else:
        # SQLite/Limbo compatible schema
        return get_sqlite_schema()


def get_postgresql_schema() -> Dict[str, List[str]]:
    """PostgreSQL-optimized schema with JSONB, indexes, and constraints."""
    return {
        "tables": [
            """
            CREATE TABLE IF NOT EXISTS table_definitions (
                id SERIAL PRIMARY KEY,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP WITH TIME ZONE,
                name TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS column_definitions (
                id SERIAL PRIMARY KEY,
                table_id INTEGER REFERENCES table_definitions(id),
                version INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP WITH TIME ZONE,
                name TEXT NOT NULL,
                data_type TEXT NOT NULL
            )
            """,
            # Type-specific value tables with JSONB for JSON type
            """
            CREATE TABLE IF NOT EXISTS text_values (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL REFERENCES table_definitions(id),
                column_id INTEGER NOT NULL REFERENCES column_definitions(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP WITH TIME ZONE,
                value TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS integer_values (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL REFERENCES table_definitions(id),
                column_id INTEGER NOT NULL REFERENCES column_definitions(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP WITH TIME ZONE,
                value INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS real_values (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL REFERENCES table_definitions(id),
                column_id INTEGER NOT NULL REFERENCES column_definitions(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP WITH TIME ZONE,
                value REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS boolean_values (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL REFERENCES table_definitions(id),
                column_id INTEGER NOT NULL REFERENCES column_definitions(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP WITH TIME ZONE,
                value BOOLEAN
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS json_values (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL REFERENCES table_definitions(id),
                column_id INTEGER NOT NULL REFERENCES column_definitions(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP WITH TIME ZONE,
                value JSONB
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS timestamp_values (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL REFERENCES table_definitions(id),
                column_id INTEGER NOT NULL REFERENCES column_definitions(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP WITH TIME ZONE,
                value TIMESTAMP WITH TIME ZONE
            )
            """,
        ],
        "history_tables": [
            """
            CREATE TABLE IF NOT EXISTS text_value_history (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                value TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS integer_value_history (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                value INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS real_value_history (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                value REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS boolean_value_history (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                value BOOLEAN
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS json_value_history (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                value JSONB
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS timestamp_value_history (
                row_id INTEGER NOT NULL,
                table_id INTEGER NOT NULL,
                column_id INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                value TIMESTAMP WITH TIME ZONE
            )
            """,
        ],
        "indexes": [
            # Performance indexes for efficient queries
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_text_values_lookup ON text_values (table_id, column_id, row_id) WHERE deleted_at IS NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_integer_values_lookup ON integer_values (table_id, column_id, row_id) WHERE deleted_at IS NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_real_values_lookup ON real_values (table_id, column_id, row_id) WHERE deleted_at IS NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boolean_values_lookup ON boolean_values (table_id, column_id, row_id) WHERE deleted_at IS NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_json_values_lookup ON json_values (table_id, column_id, row_id) WHERE deleted_at IS NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_timestamp_values_lookup ON timestamp_values (table_id, column_id, row_id) WHERE deleted_at IS NULL",
            
            # GIN indexes for JSONB
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_json_values_gin ON json_values USING GIN (value)",
            
            # Table and column lookup indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_table_definitions_name ON table_definitions (name) WHERE deleted_at IS NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_column_definitions_lookup ON column_definitions (table_id, name) WHERE deleted_at IS NULL",
        ]
    }


def get_mysql_schema() -> Dict[str, List[str]]:
    """MySQL-optimized schema with JSON type and InnoDB indexes."""
    return {
        "tables": [
            """
            CREATE TABLE IF NOT EXISTS table_definitions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                version INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                name TEXT NOT NULL
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS column_definitions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                table_id INT NOT NULL,
                version INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                FOREIGN KEY (table_id) REFERENCES table_definitions(id)
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS text_values (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                value TEXT,
                FOREIGN KEY (table_id) REFERENCES table_definitions(id),
                FOREIGN KEY (column_id) REFERENCES column_definitions(id)
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS integer_values (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                value INT,
                FOREIGN KEY (table_id) REFERENCES table_definitions(id),
                FOREIGN KEY (column_id) REFERENCES column_definitions(id)
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS real_values (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                value DOUBLE,
                FOREIGN KEY (table_id) REFERENCES table_definitions(id),
                FOREIGN KEY (column_id) REFERENCES column_definitions(id)
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS boolean_values (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                value BOOLEAN,
                FOREIGN KEY (table_id) REFERENCES table_definitions(id),
                FOREIGN KEY (column_id) REFERENCES column_definitions(id)
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS json_values (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                value JSON,
                FOREIGN KEY (table_id) REFERENCES table_definitions(id),
                FOREIGN KEY (column_id) REFERENCES column_definitions(id)
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS timestamp_values (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                value TIMESTAMP,
                FOREIGN KEY (table_id) REFERENCES table_definitions(id),
                FOREIGN KEY (column_id) REFERENCES column_definitions(id)
            ) ENGINE=InnoDB
            """,
        ],
        "history_tables": [
            """
            CREATE TABLE IF NOT EXISTS text_value_history (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value TEXT
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS integer_value_history (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value INT
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS real_value_history (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value DOUBLE
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS boolean_value_history (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value BOOLEAN
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS json_value_history (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value JSON
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS timestamp_value_history (
                row_id INT NOT NULL,
                table_id INT NOT NULL,
                column_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value TIMESTAMP
            ) ENGINE=InnoDB
            """,
        ],
        "indexes": [
            # Performance indexes for efficient queries
            "CREATE INDEX idx_text_values_lookup ON text_values (table_id, column_id, row_id)",
            "CREATE INDEX idx_integer_values_lookup ON integer_values (table_id, column_id, row_id)",
            "CREATE INDEX idx_real_values_lookup ON real_values (table_id, column_id, row_id)",
            "CREATE INDEX idx_boolean_values_lookup ON boolean_values (table_id, column_id, row_id)",
            "CREATE INDEX idx_json_values_lookup ON json_values (table_id, column_id, row_id)",
            "CREATE INDEX idx_timestamp_values_lookup ON timestamp_values (table_id, column_id, row_id)",
            
            # Table and column lookup indexes
            "CREATE INDEX idx_table_definitions_name ON table_definitions (name)",
            "CREATE INDEX idx_column_definitions_lookup ON column_definitions (table_id, name)",
        ]
    }


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
                row_id INTEGER,
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
                row_id INTEGER,
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
                row_id INTEGER,
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
                row_id INTEGER,
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
                row_id INTEGER,
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
                row_id INTEGER,
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
                row_id INTEGER,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS integer_value_history (
                row_id INTEGER,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS real_value_history (
                row_id INTEGER,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS boolean_value_history (
                row_id INTEGER,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS json_value_history (
                row_id INTEGER,
                table_id INTEGER,
                column_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS timestamp_value_history (
                row_id INTEGER,
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
    
    # Create indexes (skip CONCURRENTLY for non-PostgreSQL)
    for index_sql in schema["indexes"]:
        try:
            # For non-PostgreSQL, remove CONCURRENTLY
            if backend.get_name() != "postgresql":
                index_sql = index_sql.replace("CONCURRENTLY ", "")
            backend.execute(connection, index_sql.strip())
        except Exception as e:
            # Indexes might already exist, continue
            print(f"Warning: Could not create index: {e}")
    
    backend.commit(connection)
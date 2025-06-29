# SynthDB API Server Feature Request

## Overview

This proposal outlines a REST API server implementation for SynthDB that exposes all database functionality through HTTP endpoints. The API will allow remote clients to perform all SynthDB operations including database management, table operations, data manipulation, and bulk import/export.

## Goals

- Provide complete remote access to all SynthDB features
- Maintain feature parity with the Python API and CLI
- Support multiple concurrent database connections
- Enable cross-platform and cross-language integration
- Simple deployment and configuration

## Architecture

### Server Design

The API server will be built using FastAPI for the following reasons:
- Automatic OpenAPI/Swagger documentation generation
- Built-in request/response validation with Pydantic
- Async support for concurrent operations
- Easy integration with existing Python codebase
- WebSocket support for future streaming features

### Database Connection Management

- Server maintains a pool of database connections
- Each API request specifies the database to operate on
- Connection caching with configurable TTL
- Support for both SQLite (local files) and LibSQL (remote) backends

### API Structure

All endpoints follow RESTful conventions with a base path of `/api/v1/`.

## API Endpoints

### Database Operations

```
POST   /api/v1/databases/init
GET    /api/v1/databases/{db_name}/info
GET    /api/v1/databases/{db_name}/stats
POST   /api/v1/databases/{db_name}/refresh-views
```

### Table Operations

```
GET    /api/v1/databases/{db_name}/tables
POST   /api/v1/databases/{db_name}/tables
GET    /api/v1/databases/{db_name}/tables/{table_name}
DELETE /api/v1/databases/{db_name}/tables/{table_name}
POST   /api/v1/databases/{db_name}/tables/{table_name}/copy
GET    /api/v1/databases/{db_name}/tables/{table_name}/export
GET    /api/v1/databases/{db_name}/tables/{table_name}/history
```

### Column Operations

```
GET    /api/v1/databases/{db_name}/tables/{table_name}/columns
POST   /api/v1/databases/{db_name}/tables/{table_name}/columns
POST   /api/v1/databases/{db_name}/tables/{table_name}/columns/bulk
PUT    /api/v1/databases/{db_name}/tables/{table_name}/columns/{column_name}
DELETE /api/v1/databases/{db_name}/tables/{table_name}/columns/{column_name}
POST   /api/v1/databases/{db_name}/tables/{table_name}/columns/{column_name}/copy
```

### Data Operations

```
GET    /api/v1/databases/{db_name}/tables/{table_name}/rows
POST   /api/v1/databases/{db_name}/tables/{table_name}/rows
PUT    /api/v1/databases/{db_name}/tables/{table_name}/rows
DELETE /api/v1/databases/{db_name}/tables/{table_name}/rows/{row_id}
GET    /api/v1/databases/{db_name}/tables/{table_name}/rows/{row_id}
GET    /api/v1/databases/{db_name}/tables/{table_name}/rows/{row_id}/status
```

### Bulk Operations

```
POST   /api/v1/databases/{db_name}/tables/{table_name}/import/csv
POST   /api/v1/databases/{db_name}/tables/{table_name}/import/json
GET    /api/v1/databases/{db_name}/tables/{table_name}/export/csv
GET    /api/v1/databases/{db_name}/tables/{table_name}/export/json
POST   /api/v1/databases/{db_name}/tables/{table_name}/rows/bulk
```

### Utility Operations

```
POST   /api/v1/utilities/infer-types
POST   /api/v1/utilities/test-connection
```

## Request/Response Formats

### Standard Response Structure

```json
{
  "success": true,
  "data": {...},
  "error": null,
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "database": "app.db",
    "version": "1.0.0"
  }
}
```

### Error Response Structure

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "TABLE_NOT_FOUND",
    "message": "Table 'users' does not exist",
    "details": {...}
  },
  "metadata": {...}
}
```

### Example Request/Response Pairs

#### Create Table
```http
POST /api/v1/databases/app.db/tables
Content-Type: application/json

{
  "table_name": "users",
  "columns": [
    {"name": "email", "type": "text"},
    {"name": "age", "type": "integer"}
  ]
}
```

Response:
```json
{
  "success": true,
  "data": {
    "table_name": "users",
    "columns": [
      {"name": "id", "type": "text", "is_primary": true},
      {"name": "email", "type": "text"},
      {"name": "age", "type": "integer"}
    ],
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

#### Query Data
```http
GET /api/v1/databases/app.db/tables/users/rows?where=age>18&limit=10&offset=0
```

Response:
```json
{
  "success": true,
  "data": {
    "rows": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "age": 25,
        "_created_at": "2024-01-01T00:00:00Z",
        "_updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total_count": 42,
    "has_more": true
  }
}
```

#### Bulk Insert with Type Inference
```http
POST /api/v1/databases/app.db/tables/products/rows/bulk
Content-Type: application/json

{
  "data": [
    {"name": "Widget", "price": "19.99", "in_stock": "true"},
    {"name": "Gadget", "price": "29.99", "in_stock": "false"}
  ],
  "infer_types": true,
  "sample_size": 100
}
```

## Implementation Plan

### Phase 1: Core API Server
1. Set up FastAPI application structure
2. Implement database connection management
3. Create error handling and response formatting
4. Add request validation with Pydantic models

### Phase 2: Basic Operations
1. Implement database initialization and info endpoints
2. Add table CRUD operations
3. Implement column management endpoints
4. Add basic row operations (insert, query, delete)

### Phase 3: Advanced Features
1. Implement bulk operations and import/export
2. Add type inference endpoints
3. Implement table/column copy operations
4. Add history and metadata endpoints

### Phase 4: Performance & Security
1. Add connection pooling and caching
2. Implement rate limiting
3. Add request logging and monitoring
4. Optimize query performance

### Phase 5: Documentation & Testing
1. Generate OpenAPI documentation
2. Create client SDK examples
3. Write comprehensive API tests
4. Add performance benchmarks

## Example Server Implementation

```python
# synthdb/api_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import synthdb

app = FastAPI(title="SynthDB API", version="1.0.0")

# Connection cache
connections: Dict[str, synthdb.Connection] = {}

class TableCreateRequest(BaseModel):
    table_name: str
    columns: List[Dict[str, Any]]

class RowInsertRequest(BaseModel):
    data: Dict[str, Any]
    explicit_id: Optional[str] = None

@app.post("/api/v1/databases/{db_name}/tables")
async def create_table(db_name: str, request: TableCreateRequest):
    try:
        db = get_or_create_connection(db_name)
        table = db.create_table(request.table_name)
        
        for col in request.columns:
            table.add_column(col["name"], col.get("type", "text"))
        
        return {
            "success": True,
            "data": {
                "table_name": request.table_name,
                "columns": table.list_columns()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/databases/{db_name}/tables/{table_name}/rows")
async def query_rows(
    db_name: str, 
    table_name: str,
    where: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    try:
        db = get_or_create_connection(db_name)
        table = db.table(table_name)
        
        rows = table.query(where=where)
        total = len(rows)
        
        # Apply pagination
        rows = rows[offset:offset + limit]
        
        return {
            "success": True,
            "data": {
                "rows": rows,
                "total_count": total,
                "has_more": offset + limit < total
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def get_or_create_connection(db_name: str) -> synthdb.Connection:
    if db_name not in connections:
        connections[db_name] = synthdb.connect(db_name)
    return connections[db_name]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Running the Server

```bash
# Install dependencies
pip install synthdb[api]

# Start the server
synthdb api serve --host 0.0.0.0 --port 8000

# Or use Python directly
python -m synthdb.api_server
```

## Client Usage Examples

### Python Client
```python
import requests

# Create a table
response = requests.post(
    "http://localhost:8000/api/v1/databases/app.db/tables",
    json={
        "table_name": "users",
        "columns": [
            {"name": "email", "type": "text"},
            {"name": "age", "type": "integer"}
        ]
    }
)

# Insert data
response = requests.post(
    "http://localhost:8000/api/v1/databases/app.db/tables/users/rows",
    json={
        "data": {"email": "user@example.com", "age": 25}
    }
)

# Query data
response = requests.get(
    "http://localhost:8000/api/v1/databases/app.db/tables/users/rows",
    params={"where": "age > 18", "limit": 10}
)
```

### JavaScript Client
```javascript
// Create table
const response = await fetch('http://localhost:8000/api/v1/databases/app.db/tables', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    table_name: 'users',
    columns: [
      {name: 'email', type: 'text'},
      {name: 'age', type: 'integer'}
    ]
  })
});

// Query data
const data = await fetch('http://localhost:8000/api/v1/databases/app.db/tables/users/rows?where=age>18')
  .then(r => r.json());
```

## Future Enhancements

1. **WebSocket Support** - Real-time subscriptions to table changes
2. **GraphQL Endpoint** - Alternative query interface
3. **Batch Operations** - Execute multiple operations in a single request
4. **Database Migrations** - API endpoints for schema evolution
5. **Query Builder** - Structured query format as alternative to SQL WHERE clauses
6. **Streaming Exports** - Stream large datasets without loading into memory
7. **API Keys & Authentication** - When security requirements are defined
8. **Multi-tenancy** - Database isolation and access control
9. **Metrics & Monitoring** - Prometheus/OpenTelemetry integration
10. **Client SDKs** - Auto-generated clients for popular languages
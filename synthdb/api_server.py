"""FastAPI server for SynthDB remote access."""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from fastapi import FastAPI, HTTPException, status, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from . import connect, Connection
from .errors import TableNotFoundError, ColumnNotFoundError


# Response models
class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response structure."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# Request models
class DatabaseInitRequest(BaseModel):
    """Request to initialize a database."""
    backend: str = Field("sqlite", description="Database backend (sqlite, libsql)")
    force: bool = Field(False, description="Overwrite existing database")


class TableCreateRequest(BaseModel):
    """Request to create a table."""
    table_name: str
    columns: Optional[List[Dict[str, Any]]] = Field(None, description="Initial columns to create")


class ColumnCreateRequest(BaseModel):
    """Request to create a column."""
    column_name: str
    data_type: str = Field(description="Column data type (text, integer, real, timestamp)")


class ColumnsBulkCreateRequest(BaseModel):
    """Request to create multiple columns."""
    columns: Dict[str, Union[str, Any]] = Field(description="Column name -> type/sample mappings")


class RowInsertRequest(BaseModel):
    """Request to insert a row."""
    data: Union[Dict[str, Any], str]
    value: Optional[Any] = None
    force_type: Optional[str] = None
    id: Optional[str] = None


class RowsBulkInsertRequest(BaseModel):
    """Request to insert multiple rows."""
    data: List[Dict[str, Any]]
    infer_types: bool = Field(True, description="Automatically infer and create column types")


class RowUpdateRequest(BaseModel):
    """Request to update/upsert a row."""
    data: Dict[str, Any]
    id: str


class QueryRequest(BaseModel):
    """Request to query data."""
    where: Optional[str] = None
    limit: int = Field(100, le=10000, description="Maximum number of rows to return")
    offset: int = Field(0, ge=0, description="Number of rows to skip")


class SQLQueryRequest(BaseModel):
    """Request to execute SQL query."""
    sql: str
    params: Optional[List[Any]] = None


class SavedQueryCreateRequest(BaseModel):
    """Request to create a saved query."""
    name: str
    query_text: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Dict[str, Any]]] = None


class SavedQueryExecuteRequest(BaseModel):
    """Request to execute a saved query."""
    parameters: Dict[str, Any] = Field(default_factory=dict)


# Global connection pool
connections: Dict[str, Connection] = {}


def get_connection(db_name: str) -> Connection:
    """Get or create a database connection."""
    if db_name not in connections:
        # Support both file paths and connection strings
        if '://' in db_name:
            # Remote LibSQL connection
            connections[db_name] = connect(db_name, backend='libsql')
        else:
            # Local file connection
            connections[db_name] = connect(db_name, backend='sqlite')
    
    return connections[db_name]


def create_response(data: Any = None, error: Optional[str] = None, 
                   error_code: Optional[str] = None, **metadata) -> APIResponse:
    """Create a standardized API response."""
    response_metadata = {
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        **metadata
    }
    
    if error:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorResponse(
                code=error_code or "UNKNOWN_ERROR",
                message=error
            ).model_dump(),
            metadata=response_metadata
        )
    
    return APIResponse(
        success=True,
        data=data,
        error=None,
        metadata=response_metadata
    )


# FastAPI app
app = FastAPI(
    title="SynthDB API",
    description="REST API for SynthDB - A flexible database system with schema-on-write capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database operations
@app.post("/api/v1/databases/init")
async def init_database(request: DatabaseInitRequest, db_name: str = Query(..., description="Database name/path")):
    """Initialize a new database."""
    try:
        # Create connection which will initialize the database
        if request.force and os.path.exists(db_name) and not '://' in db_name:
            os.unlink(db_name)
        
        connection = connect(db_name, backend=request.backend)
        connections[db_name] = connection
        
        return create_response(
            data={"database": db_name, "backend": request.backend, "initialized": True},
            database=db_name
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/databases/{db_name}/info")
async def get_database_info(db_name: str):
    """Get database information."""
    try:
        db = get_connection(db_name)
        tables = db.list_tables()
        
        total_columns = 0
        for table in tables:
            columns = db.list_columns(table['name'])
            total_columns += len(columns)
        
        return create_response(
            data={
                "database": db_name,
                "tables_count": len(tables),
                "total_columns": total_columns,
                "tables": tables
            },
            database=db_name
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Table operations
@app.get("/api/v1/databases/{db_name}/tables")
async def list_tables(db_name: str):
    """List all tables in the database."""
    try:
        db = get_connection(db_name)
        tables = db.list_tables()
        return create_response(data={"tables": tables}, database=db_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/databases/{db_name}/tables")
async def create_table(db_name: str, request: TableCreateRequest):
    """Create a new table."""
    try:
        db = get_connection(db_name)
        table_id = db.create_table(request.table_name)
        
        # Add initial columns if provided
        if request.columns:
            for col in request.columns:
                db.add_column(request.table_name, col["name"], col.get("type", "text"))
        
        # Get final table structure
        columns = db.list_columns(request.table_name)
        
        return create_response(
            data={
                "table_id": table_id,
                "table_name": request.table_name,
                "columns": columns
            },
            database=db_name
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/databases/{db_name}/tables/{table_name}")
async def get_table_info(db_name: str, table_name: str):
    """Get detailed information about a table."""
    try:
        db = get_connection(db_name)
        columns = db.list_columns(table_name)
        
        # Get row count (simple query)
        try:
            row_count_result = db.execute_sql(f"SELECT COUNT(*) as count FROM {table_name}")
            row_count = row_count_result[0]['count'] if row_count_result else 0
        except:
            row_count = 0
        
        return create_response(
            data={
                "table_name": table_name,
                "columns": columns,
                "row_count": row_count
            },
            database=db_name
        )
    except TableNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/databases/{db_name}/tables/{table_name}")
async def delete_table(db_name: str, table_name: str, hard_delete: bool = Query(False)):
    """Delete a table."""
    try:
        db = get_connection(db_name)
        db.delete_table(table_name, hard_delete=hard_delete)
        
        return create_response(
            data={"table_name": table_name, "deleted": True, "hard_delete": hard_delete},
            database=db_name
        )
    except TableNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Column operations
@app.get("/api/v1/databases/{db_name}/tables/{table_name}/columns")
async def list_columns(db_name: str, table_name: str, include_deleted: bool = Query(False)):
    """List columns in a table."""
    try:
        db = get_connection(db_name)
        columns = db.list_columns(table_name, include_deleted=include_deleted)
        return create_response(data={"columns": columns}, database=db_name)
    except TableNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/databases/{db_name}/tables/{table_name}/columns")
async def create_column(db_name: str, table_name: str, request: ColumnCreateRequest):
    """Create a new column in a table."""
    try:
        db = get_connection(db_name)
        column_id = db.add_column(table_name, request.column_name, request.data_type)
        
        return create_response(
            data={
                "column_id": column_id,
                "column_name": request.column_name,
                "data_type": request.data_type,
                "table_name": table_name
            },
            database=db_name
        )
    except TableNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/databases/{db_name}/tables/{table_name}/columns/bulk")
async def create_columns_bulk(db_name: str, table_name: str, request: ColumnsBulkCreateRequest):
    """Create multiple columns in a table."""
    try:
        db = get_connection(db_name)
        column_ids = db.add_columns(table_name, request.columns)
        
        return create_response(
            data={
                "column_ids": column_ids,
                "table_name": table_name,
                "columns_created": len(column_ids)
            },
            database=db_name
        )
    except TableNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/databases/{db_name}/tables/{table_name}/columns/{column_name}")
async def delete_column(db_name: str, table_name: str, column_name: str, hard_delete: bool = Query(False)):
    """Delete a column from a table."""
    try:
        db = get_connection(db_name)
        db.delete_column(table_name, column_name, hard_delete=hard_delete)
        
        return create_response(
            data={
                "table_name": table_name,
                "column_name": column_name,
                "deleted": True,
                "hard_delete": hard_delete
            },
            database=db_name
        )
    except (TableNotFoundError, ColumnNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Data operations
@app.get("/api/v1/databases/{db_name}/tables/{table_name}/rows")
async def query_rows(db_name: str, table_name: str, request: QueryRequest = Depends()):
    """Query rows from a table."""
    try:
        db = get_connection(db_name)
        
        # Get all matching rows first
        all_rows = db.query(table_name, request.where)
        total_count = len(all_rows)
        
        # Apply pagination
        rows = all_rows[request.offset:request.offset + request.limit]
        has_more = request.offset + request.limit < total_count
        
        return create_response(
            data={
                "rows": rows,
                "total_count": total_count,
                "returned_count": len(rows),
                "has_more": has_more,
                "offset": request.offset,
                "limit": request.limit
            },
            database=db_name
        )
    except TableNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/databases/{db_name}/tables/{table_name}/rows")
async def insert_row(db_name: str, table_name: str, request: RowInsertRequest):
    """Insert a new row into a table."""
    try:
        db = get_connection(db_name)
        
        row_id = db.insert(
            table_name,
            request.data,
            value=request.value,
            force_type=request.force_type,
            id=request.id
        )
        
        return create_response(
            data={
                "id": row_id,
                "table_name": table_name,
                "inserted": True
            },
            database=db_name
        )
    except TableNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/databases/{db_name}/tables/{table_name}/rows/bulk")
async def insert_rows_bulk(db_name: str, table_name: str, request: RowsBulkInsertRequest):
    """Insert multiple rows into a table."""
    try:
        db = get_connection(db_name)
        inserted_ids = []
        
        # Insert each row
        for row_data in request.data:
            row_id = db.insert(table_name, row_data)
            inserted_ids.append(row_id)
        
        return create_response(
            data={
                "inserted_ids": inserted_ids,
                "table_name": table_name,
                "rows_inserted": len(inserted_ids)
            },
            database=db_name
        )
    except TableNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/v1/databases/{db_name}/tables/{table_name}/rows")
async def upsert_row(db_name: str, table_name: str, request: RowUpdateRequest):
    """Update/upsert a row in a table."""
    try:
        db = get_connection(db_name)
        row_id = db.upsert(table_name, request.data, request.id)
        
        return create_response(
            data={
                "id": row_id,
                "table_name": table_name,
                "upserted": True
            },
            database=db_name
        )
    except TableNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/databases/{db_name}/tables/{table_name}/rows/{row_id}")
async def get_row(db_name: str, table_name: str, row_id: str):
    """Get a specific row by ID."""
    try:
        db = get_connection(db_name)
        rows = db.query(table_name, f"id = '{row_id}'")
        
        if not rows:
            raise HTTPException(status_code=404, detail=f"Row with id '{row_id}' not found")
        
        return create_response(
            data={"row": rows[0]},
            database=db_name
        )
    except TableNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/databases/{db_name}/tables/{table_name}/rows/{row_id}")
async def delete_row(db_name: str, table_name: str, row_id: str):
    """Delete a specific row by ID."""
    try:
        db = get_connection(db_name)
        deleted = db.delete_row(table_name, row_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Row with id '{row_id}' not found")
        
        return create_response(
            data={
                "id": row_id,
                "table_name": table_name,
                "deleted": True
            },
            database=db_name
        )
    except TableNotFoundError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# SQL query execution
@app.post("/api/v1/databases/{db_name}/sql")
async def execute_sql(db_name: str, request: SQLQueryRequest):
    """Execute a safe SQL query."""
    try:
        db = get_connection(db_name)
        results = db.execute_sql(request.sql, request.params)
        
        return create_response(
            data={
                "results": results,
                "rows_returned": len(results)
            },
            database=db_name
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Saved queries operations
@app.get("/api/v1/databases/{db_name}/queries")
async def list_saved_queries(db_name: str, include_deleted: bool = Query(False)):
    """List all saved queries."""
    try:
        db = get_connection(db_name)
        queries = db.queries.list_queries(include_deleted=include_deleted)
        
        # Convert to dict format for JSON response
        query_list = []
        for query in queries:
            query_dict = {
                "id": query.id,
                "name": query.name,
                "description": query.description,
                "query_text": query.query_text,
                "created_at": query.created_at,
                "updated_at": query.updated_at,
                "deleted_at": query.deleted_at,
                "parameters": [
                    {
                        "name": p.name,
                        "data_type": p.data_type,
                        "default_value": p.default_value,
                        "is_required": p.is_required,
                        "description": p.description
                    }
                    for p in (query.parameters or [])
                ]
            }
            query_list.append(query_dict)
        
        return create_response(
            data={"queries": query_list},
            database=db_name
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/databases/{db_name}/queries")
async def create_saved_query(db_name: str, request: SavedQueryCreateRequest):
    """Create a new saved query."""
    try:
        db = get_connection(db_name)
        query = db.queries.create_query(
            name=request.name,
            query_text=request.query_text,
            description=request.description,
            parameters=request.parameters
        )
        
        return create_response(
            data={
                "id": query.id,
                "name": query.name,
                "description": query.description,
                "created": True
            },
            database=db_name
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/databases/{db_name}/queries/{query_name}")
async def get_saved_query(db_name: str, query_name: str):
    """Get details of a specific saved query."""
    try:
        db = get_connection(db_name)
        query = db.queries.get_query(query_name)
        
        if not query:
            raise HTTPException(status_code=404, detail=f"Saved query '{query_name}' not found")
        
        query_dict = {
            "id": query.id,
            "name": query.name,
            "description": query.description,
            "query_text": query.query_text,
            "created_at": query.created_at,
            "updated_at": query.updated_at,
            "parameters": [
                {
                    "name": p.name,
                    "data_type": p.data_type,
                    "default_value": p.default_value,
                    "is_required": p.is_required,
                    "description": p.description
                }
                for p in (query.parameters or [])
            ]
        }
        
        return create_response(data={"query": query_dict}, database=db_name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/databases/{db_name}/queries/{query_name}/execute")
async def execute_saved_query(db_name: str, query_name: str, request: SavedQueryExecuteRequest):
    """Execute a saved query with parameters."""
    try:
        db = get_connection(db_name)
        results = db.queries.execute_query(query_name, **request.parameters)
        
        return create_response(
            data={
                "results": results,
                "rows_returned": len(results),
                "query_name": query_name,
                "parameters": request.parameters
            },
            database=db_name
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/databases/{db_name}/queries/{query_name}")
async def delete_saved_query(db_name: str, query_name: str, hard_delete: bool = Query(False)):
    """Delete a saved query."""
    try:
        db = get_connection(db_name)
        deleted = db.queries.delete_query(query_name, hard_delete=hard_delete)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Saved query '{query_name}' not found")
        
        return create_response(
            data={
                "query_name": query_name,
                "deleted": True,
                "hard_delete": hard_delete
            },
            database=db_name
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return create_response(data={"status": "healthy", "service": "synthdb-api"})


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return create_response(
        data={
            "service": "SynthDB API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health"
        }
    )


# CLI command to start the server
def start_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """Start the API server."""
    uvicorn.run(
        "synthdb.api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    start_server()
"""Shared test fixtures for SynthDB tests."""

import os
import tempfile
import pytest
import synthdb


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    # Initialize the database using connection API
    db = synthdb.connect(db_path)
    
    yield db_path
    
    # Clean up
    if os.path.exists(db_path):
        os.unlink(db_path)
"""
Database schema definitions for the memory server.

This module contains all SQL statements and constants for creating
and managing the memory database schema.
"""

from enum import Enum
from typing import Final

# Table names
TABLE_MEMORIES: Final[str] = "memories"
TABLE_VEC_MEMORIES: Final[str] = "vec_memories"

# Column names for memories table
COL_ID: Final[str] = "id"
COL_CONTENT: Final[str] = "content"
COL_CONTENT_HASH: Final[str] = "content_hash"
COL_PRIORITY: Final[str] = "priority"
COL_CATEGORY: Final[str] = "category"
COL_TAGS: Final[str] = "tags"
COL_PROJECT_ID: Final[str] = "project_id"
COL_SOURCE: Final[str] = "source"
COL_CREATED_AT: Final[str] = "created_at"
COL_UPDATED_AT: Final[str] = "updated_at"
COL_EMBEDDING_MODEL: Final[str] = "embedding_model"
COL_EMBEDDING_MODEL_VERSION: Final[str] = "embedding_model_version"
COL_EMBEDDING_DIMENSION: Final[str] = "embedding_dimension"
COL_ACCESS_COUNT: Final[str] = "access_count"
COL_LAST_ACCESSED_AT: Final[str] = "last_accessed_at"
COL_USAGE_CONTEXTS: Final[str] = "usage_contexts"

# Column names for vec_memories table
COL_MEMORY_ID: Final[str] = "memory_id"
COL_EMBEDDING: Final[str] = "embedding"

# Index names
IDX_PRIORITY: Final[str] = "idx_priority"
IDX_PROJECT_ID: Final[str] = "idx_project_id"
IDX_CREATED_AT: Final[str] = "idx_created_at"
IDX_CONTENT_HASH: Final[str] = "idx_content_hash"


class Priority(str, Enum):
    """Memory priority levels."""
    CORE = "CORE"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


# SQL statement to create the memories table
SQL_CREATE_MEMORIES_TABLE: Final[str] = f"""
CREATE TABLE IF NOT EXISTS {TABLE_MEMORIES} (
    {COL_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
    {COL_CONTENT} TEXT NOT NULL,
    {COL_CONTENT_HASH} TEXT UNIQUE NOT NULL,
    {COL_PRIORITY} TEXT NOT NULL DEFAULT 'NORMAL',
    {COL_CATEGORY} TEXT,
    {COL_TAGS} TEXT,
    {COL_PROJECT_ID} TEXT,
    {COL_SOURCE} TEXT,
    {COL_CREATED_AT} TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    {COL_UPDATED_AT} TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    {COL_EMBEDDING_MODEL} TEXT NOT NULL,
    {COL_EMBEDDING_MODEL_VERSION} TEXT NOT NULL,
    {COL_EMBEDDING_DIMENSION} INTEGER NOT NULL,
    {COL_ACCESS_COUNT} INTEGER NOT NULL DEFAULT 0,
    {COL_LAST_ACCESSED_AT} TIMESTAMP,
    {COL_USAGE_CONTEXTS} TEXT
)
"""

# SQL statement to create the vec_memories virtual table
SQL_CREATE_VEC_MEMORIES_TABLE: Final[str] = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS {TABLE_VEC_MEMORIES}
USING vec0(
    {COL_MEMORY_ID} INTEGER PRIMARY KEY,
    {COL_EMBEDDING} FLOAT[384]
)
"""

# SQL statements to create indexes
SQL_CREATE_INDEX_PRIORITY: Final[str] = f"""
CREATE INDEX IF NOT EXISTS {IDX_PRIORITY}
ON {TABLE_MEMORIES}({COL_PRIORITY})
"""

SQL_CREATE_INDEX_PROJECT_ID: Final[str] = f"""
CREATE INDEX IF NOT EXISTS {IDX_PROJECT_ID}
ON {TABLE_MEMORIES}({COL_PROJECT_ID})
"""

SQL_CREATE_INDEX_CREATED_AT: Final[str] = f"""
CREATE INDEX IF NOT EXISTS {IDX_CREATED_AT}
ON {TABLE_MEMORIES}({COL_CREATED_AT})
"""

SQL_CREATE_INDEX_CONTENT_HASH: Final[str] = f"""
CREATE INDEX IF NOT EXISTS {IDX_CONTENT_HASH}
ON {TABLE_MEMORIES}({COL_CONTENT_HASH})
"""

# List of all index creation statements
SQL_CREATE_INDEXES: Final[list[str]] = [
    SQL_CREATE_INDEX_PRIORITY,
    SQL_CREATE_INDEX_PROJECT_ID,
    SQL_CREATE_INDEX_CREATED_AT,
    SQL_CREATE_INDEX_CONTENT_HASH,
]


def validate_priority(priority: str) -> bool:
    """
    Validate that a priority value is valid.

    Args:
        priority: The priority value to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_priority("HIGH")
        True
        >>> validate_priority("INVALID")
        False
    """
    try:
        Priority(priority)
        return True
    except ValueError:
        return False


def get_valid_priorities() -> list[str]:
    """
    Get a list of all valid priority values.

    Returns:
        List of valid priority strings

    Examples:
        >>> get_valid_priorities()
        ['CORE', 'HIGH', 'NORMAL', 'LOW']
    """
    return [p.value for p in Priority]


def validate_schema_version(conn) -> bool:
    """
    Validate that the database schema matches the expected version.

    Args:
        conn: SQLite database connection

    Returns:
        True if schema is valid, False otherwise
    """
    cursor = conn.cursor()

    # Check that memories table exists with expected columns
    cursor.execute(f"PRAGMA table_info({TABLE_MEMORIES})")
    columns = {row[1] for row in cursor.fetchall()}

    expected_columns = {
        COL_ID, COL_CONTENT, COL_CONTENT_HASH, COL_PRIORITY, COL_CATEGORY,
        COL_TAGS, COL_PROJECT_ID, COL_SOURCE, COL_CREATED_AT, COL_UPDATED_AT,
        COL_EMBEDDING_MODEL, COL_EMBEDDING_MODEL_VERSION, COL_EMBEDDING_DIMENSION,
        COL_ACCESS_COUNT, COL_LAST_ACCESSED_AT, COL_USAGE_CONTEXTS
    }

    if not expected_columns.issubset(columns):
        return False

    # Check that vec_memories table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE_VEC_MEMORIES,)
    )
    if not cursor.fetchone():
        return False

    return True

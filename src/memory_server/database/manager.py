"""
Database manager for memory storage and retrieval.

This module provides the DatabaseManager class which handles all database
operations including initialization, CRUD operations, and vector search.
"""

import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..utils.logger import get_logger
from .schema import (
    COL_ACCESS_COUNT,
    COL_CATEGORY,
    COL_CONTENT,
    COL_CONTENT_HASH,
    COL_CREATED_AT,
    COL_EMBEDDING,
    COL_EMBEDDING_DIMENSION,
    COL_EMBEDDING_MODEL,
    COL_EMBEDDING_MODEL_VERSION,
    COL_ID,
    COL_LAST_ACCESSED_AT,
    COL_MEMORY_ID,
    COL_PRIORITY,
    COL_PROJECT_ID,
    COL_SOURCE,
    COL_TAGS,
    COL_UPDATED_AT,
    COL_USAGE_CONTEXTS,
    SQL_CREATE_INDEXES,
    SQL_CREATE_MEMORIES_TABLE,
    SQL_CREATE_VEC_MEMORIES_TABLE,
    TABLE_MEMORIES,
    TABLE_VEC_MEMORIES,
    validate_priority,
)

logger = get_logger(__name__)


class DatabaseManager:
    """
    Manages all database operations for memory storage.

    This class handles:
    - Database initialization and schema creation
    - Memory CRUD operations
    - Vector similarity search
    - Duplicate detection
    - Access tracking

    Attributes:
        db_path: Path to the SQLite database file
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the DatabaseManager.

        Args:
            db_path: Path to database file. If None, defaults to ~/.memory/db
        """
        if db_path is None:
            db_path = Path.home() / ".memory" / "db"

        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None

        logger.info(f"DatabaseManager initialized with path: {self.db_path}")

    def initialize(self) -> None:
        """
        Initialize the database.

        Creates the database file, parent directories, loads sqlite-vec extension,
        and creates all tables and indexes if they don't exist.

        Raises:
            RuntimeError: If sqlite-vec extension cannot be loaded
            sqlite3.Error: If database initialization fails
        """
        # Create parent directories if they don't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Initializing database...")

        with self._get_connection() as conn:
            # Load sqlite-vec extension
            self._load_vec_extension(conn)

            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")

            # Create tables
            logger.debug("Creating memories table...")
            conn.execute(SQL_CREATE_MEMORIES_TABLE)

            logger.debug("Creating vec_memories virtual table...")
            conn.execute(SQL_CREATE_VEC_MEMORIES_TABLE)

            # Create indexes
            logger.debug("Creating indexes...")
            for index_sql in SQL_CREATE_INDEXES:
                conn.execute(index_sql)

            conn.commit()

        logger.info("Database initialized successfully")

    def _load_vec_extension(self, conn: sqlite3.Connection) -> None:
        """
        Load the sqlite-vec extension.

        Args:
            conn: SQLite connection

        Raises:
            RuntimeError: If extension cannot be loaded
        """
        try:
            # Enable extension loading
            conn.enable_load_extension(True)

            # Try common extension locations
            extension_paths = [
                "vec0",  # If in system path
                "libvec0.so",  # Linux
                "libvec0.dylib",  # macOS
                "vec0.dll",  # Windows
            ]

            loaded = False
            for ext_path in extension_paths:
                try:
                    conn.load_extension(ext_path)
                    logger.debug(f"Loaded sqlite-vec extension: {ext_path}")
                    loaded = True
                    break
                except sqlite3.OperationalError:
                    continue

            if not loaded:
                raise RuntimeError(
                    "Could not load sqlite-vec extension. "
                    "Please ensure sqlite-vec is installed."
                )

        except Exception as e:
            logger.error(f"Failed to load sqlite-vec extension: {e}")
            raise RuntimeError(f"Failed to load sqlite-vec extension: {e}") from e
        finally:
            conn.enable_load_extension(False)

    @contextmanager
    def _get_connection(self):
        """
        Get a database connection as a context manager.

        Yields:
            sqlite3.Connection: Database connection

        Example:
            >>> with manager._get_connection() as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT * FROM memories")
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            conn.close()

    def insert_memory(
        self,
        content: str,
        embedding: list[float],
        priority: str = "NORMAL",
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        project_id: Optional[str] = None,
        source: Optional[str] = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_model_version: str = "v2",
        embedding_dimension: int = 384,
    ) -> int:
        """
        Insert a new memory into the database.

        Args:
            content: Memory content text
            embedding: 384-dimensional embedding vector
            priority: Priority level (CORE, HIGH, NORMAL, LOW)
            category: Optional category
            tags: Optional list of tags
            project_id: Optional project identifier
            source: Optional source identifier
            embedding_model: Model used for embedding
            embedding_model_version: Version of embedding model
            embedding_dimension: Dimension of embedding vector

        Returns:
            int: ID of the inserted memory

        Raises:
            ValueError: If priority is invalid or embedding dimension is wrong
            sqlite3.IntegrityError: If content hash already exists
        """
        # Validate inputs
        if not validate_priority(priority):
            raise ValueError(f"Invalid priority: {priority}")

        if len(embedding) != embedding_dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {embedding_dimension}, "
                f"got {len(embedding)}"
            )

        # Generate content hash
        content_hash = self._generate_content_hash(content)

        # Convert tags to JSON
        tags_json = json.dumps(tags) if tags else None

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Insert into memories table
            cursor.execute(
                f"""
                INSERT INTO {TABLE_MEMORIES} (
                    {COL_CONTENT}, {COL_CONTENT_HASH}, {COL_PRIORITY},
                    {COL_CATEGORY}, {COL_TAGS}, {COL_PROJECT_ID}, {COL_SOURCE},
                    {COL_EMBEDDING_MODEL}, {COL_EMBEDDING_MODEL_VERSION},
                    {COL_EMBEDDING_DIMENSION}
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    content,
                    content_hash,
                    priority,
                    category,
                    tags_json,
                    project_id,
                    source,
                    embedding_model,
                    embedding_model_version,
                    embedding_dimension,
                ),
            )

            memory_id = cursor.lastrowid

            # Insert into vec_memories table
            cursor.execute(
                f"""
                INSERT INTO {TABLE_VEC_MEMORIES} ({COL_MEMORY_ID}, {COL_EMBEDDING})
                VALUES (?, ?)
                """,
                (memory_id, json.dumps(embedding)),
            )

            conn.commit()

        logger.info(f"Inserted memory with ID: {memory_id}")
        return memory_id

    def get_memory_by_id(self, memory_id: int) -> Optional[dict[str, Any]]:
        """
        Fetch a memory by its ID.

        Args:
            memory_id: Memory ID

        Returns:
            Dictionary containing memory data, or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {TABLE_MEMORIES} WHERE {COL_ID} = ?",
                (memory_id,),
            )

            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)

        return None

    def get_memory_by_hash(self, content_hash: str) -> Optional[dict[str, Any]]:
        """
        Fetch a memory by its content hash.

        Args:
            content_hash: Content hash

        Returns:
            Dictionary containing memory data, or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {TABLE_MEMORIES} WHERE {COL_CONTENT_HASH} = ?",
                (content_hash,),
            )

            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)

        return None

    def delete_memory(self, memory_id: int) -> bool:
        """
        Delete a memory from both tables.

        Args:
            memory_id: Memory ID to delete

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Delete from vec_memories first (foreign key constraint)
            cursor.execute(
                f"DELETE FROM {TABLE_VEC_MEMORIES} WHERE {COL_MEMORY_ID} = ?",
                (memory_id,),
            )

            # Delete from memories
            cursor.execute(
                f"DELETE FROM {TABLE_MEMORIES} WHERE {COL_ID} = ?",
                (memory_id,),
            )

            deleted = cursor.rowcount > 0
            conn.commit()

        if deleted:
            logger.info(f"Deleted memory with ID: {memory_id}")
        else:
            logger.warning(f"Memory not found for deletion: {memory_id}")

        return deleted

    def vector_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        similarity_threshold: float = 0.0,
    ) -> list[tuple[int, float]]:
        """
        Perform KNN vector similarity search.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of tuples (memory_id, similarity_score), sorted by similarity

        Note:
            Uses cosine similarity via sqlite-vec distance function.
            Similarity = 1 - distance (higher is more similar)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # sqlite-vec uses distance (lower is better)
            # We convert to similarity (higher is better) by: similarity = 1 - distance
            cursor.execute(
                f"""
                SELECT
                    {COL_MEMORY_ID},
                    1 - distance AS similarity
                FROM {TABLE_VEC_MEMORIES}
                WHERE {COL_EMBEDDING} MATCH ?
                    AND (1 - distance) >= ?
                ORDER BY distance
                LIMIT ?
                """,
                (json.dumps(query_embedding), similarity_threshold, limit),
            )

            results = [(row[0], row[1]) for row in cursor.fetchall()]

        logger.debug(f"Vector search returned {len(results)} results")
        return results

    def list_memories(
        self,
        filters: Optional[dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "DESC",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        List memories with filtering and pagination.

        Args:
            filters: Optional filters (priority, tags, project_id, date_range)
            sort_by: Column to sort by
            sort_order: Sort order (ASC or DESC)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of memory dictionaries

        Example filters:
            {
                "priority": "HIGH",
                "tags": ["architecture", "database"],
                "project_id": "my-project",
                "date_range": {"start": "2024-01-01", "end": "2024-12-31"}
            }
        """
        filters = filters or {}

        # Build WHERE clause
        where_clauses = []
        params = []

        if "priority" in filters:
            where_clauses.append(f"{COL_PRIORITY} = ?")
            params.append(filters["priority"])

        if "project_id" in filters:
            where_clauses.append(f"{COL_PROJECT_ID} = ?")
            params.append(filters["project_id"])

        if "tags" in filters and filters["tags"]:
            # Check if any of the provided tags exist in the tags JSON array
            tag_conditions = []
            for tag in filters["tags"]:
                tag_conditions.append(f"{COL_TAGS} LIKE ?")
                params.append(f'%"{tag}"%')
            where_clauses.append(f"({' OR '.join(tag_conditions)})")

        if "date_range" in filters:
            date_range = filters["date_range"]
            if "start" in date_range:
                where_clauses.append(f"{COL_CREATED_AT} >= ?")
                params.append(date_range["start"])
            if "end" in date_range:
                where_clauses.append(f"{COL_CREATED_AT} <= ?")
                params.append(date_range["end"])

        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Build query
        query = f"""
            SELECT * FROM {TABLE_MEMORIES}
            {where_clause}
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?
        """

        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            results = [self._row_to_dict(row) for row in cursor.fetchall()]

        logger.debug(f"list_memories returned {len(results)} results")
        return results

    def update_access_count(self, memory_id: int) -> None:
        """
        Increment access count and update last accessed timestamp.

        Args:
            memory_id: Memory ID to update
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                UPDATE {TABLE_MEMORIES}
                SET {COL_ACCESS_COUNT} = {COL_ACCESS_COUNT} + 1,
                    {COL_LAST_ACCESSED_AT} = CURRENT_TIMESTAMP
                WHERE {COL_ID} = ?
                """,
                (memory_id,),
            )
            conn.commit()

    def check_duplicate_hash(self, content_hash: str) -> Optional[int]:
        """
        Check if a content hash already exists.

        Args:
            content_hash: Hash to check

        Returns:
            Memory ID if exists, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {COL_ID} FROM {TABLE_MEMORIES} WHERE {COL_CONTENT_HASH} = ?",
                (content_hash,),
            )

            row = cursor.fetchone()
            if row:
                return row[0]

        return None

    @staticmethod
    def _generate_content_hash(content: str) -> str:
        """
        Generate SHA256 hash of content.

        Args:
            content: Content to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        """
        Convert a SQLite row to a dictionary.

        Args:
            row: SQLite row object

        Returns:
            Dictionary with column names as keys
        """
        result = dict(row)

        # Parse JSON fields
        if result.get(COL_TAGS):
            result[COL_TAGS] = json.loads(result[COL_TAGS])

        if result.get(COL_USAGE_CONTEXTS):
            result[COL_USAGE_CONTEXTS] = json.loads(result[COL_USAGE_CONTEXTS])

        return result

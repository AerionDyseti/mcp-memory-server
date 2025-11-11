"""
Memory service for storing and retrieving memories.

This module provides the MemoryService class which orchestrates database operations,
embedding generation, caching, and scoring to provide a unified interface for
memory management.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from memory_server.config import get_settings
from memory_server.database import DatabaseManager
from memory_server.embedding import EmbeddingCache, EmbeddingService
from memory_server.utils import get_logger
from memory_server.utils.scoring import score_memories

logger = get_logger(__name__)


class MemoryService:
    """
    Service for managing memories with semantic search.

    This service coordinates:
    - Database operations (storage, retrieval)
    - Embedding generation and caching
    - Duplicate detection (hash and vector similarity)
    - Multi-factor scoring for search results
    - Filtering and sorting

    Attributes:
        db_manager: Database manager instance
        embedding_service: Embedding service instance
        embedding_cache: Embedding cache instance
        settings: Application settings
    """

    def __init__(
        self,
        db_path: Optional[Path | str] = None,
        embedding_service: Optional[EmbeddingService] = None,
        embedding_cache: Optional[EmbeddingCache] = None,
    ):
        """
        Initialize the memory service.

        Args:
            db_path: Optional database path (defaults to settings.global_db_path)
            embedding_service: Optional embedding service (creates new if not provided)
            embedding_cache: Optional embedding cache (creates new if not provided)
        """
        self.settings = get_settings()

        # Initialize database manager
        if db_path is None:
            db_path = self.settings.global_db_path
        self.db_manager = DatabaseManager(db_path=db_path)
        self.db_manager.initialize()

        # Initialize embedding service and cache
        self.embedding_service = embedding_service or EmbeddingService()
        self.embedding_cache = embedding_cache or EmbeddingCache()

        logger.info("MemoryService initialized successfully")

    def store_memory(
        self,
        content: str,
        tags: Optional[list[str]] = None,
        priority: str = "NORMAL",
        category: Optional[str] = None,
        source: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Store a new memory.

        This method:
        1. Generates content hash for duplicate detection
        2. Checks for exact duplicates (hash match)
        3. Generates embedding (checks cache first)
        4. Checks for near-duplicates (vector similarity > threshold)
        5. Inserts into database
        6. Caches embedding

        Args:
            content: Memory content text
            tags: Optional list of tags
            priority: Priority level (CORE, HIGH, NORMAL, LOW)
            category: Optional category
            source: Optional source identifier
            project_id: Optional project identifier

        Returns:
            Dictionary with:
            - memory_id: ID of stored memory
            - duplicate: True if exact duplicate found
            - near_duplicate: Optional dict with near-duplicate info if found
            - success: True if stored successfully
        """
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

        # Generate content hash
        content_hash = self._generate_content_hash(content)

        # Check for exact duplicate (hash match)
        existing_id = self.db_manager.check_duplicate_hash(content_hash)
        if existing_id:
            logger.info(f"Exact duplicate found for hash {content_hash[:8]}..., returning existing memory_id: {existing_id}")
            return {
                "memory_id": existing_id,
                "duplicate": True,
                "near_duplicate": None,
                "success": True,
            }

        # Generate embedding (check cache first)
        embedding = self.embedding_cache.get(content_hash)
        if embedding is None:
            logger.debug(f"Generating embedding for content (hash: {content_hash[:8]}...)")
            embedding = self.embedding_service.generate_embedding(content)
            self.embedding_cache.set(content_hash, embedding)
        else:
            logger.debug(f"Using cached embedding for content (hash: {content_hash[:8]}...)")

        # Check for near-duplicates (vector similarity)
        near_duplicate = None
        if self.settings.deduplication.auto_check:
            near_duplicate = self._check_near_duplicate(embedding, content_hash)

        # Get model info
        model_info = self.embedding_service.get_model_info()
        dimension = self.embedding_service.get_dimension()

        # Insert into database
        try:
            memory_id = self.db_manager.insert_memory(
                content=content,
                embedding=embedding,
                priority=priority,
                category=category,
                tags=tags,
                project_id=project_id,
                source=source,
                embedding_model=model_info["model"],
                embedding_model_version=model_info["version"],
                embedding_dimension=dimension,
            )

            logger.info(f"Stored memory with ID: {memory_id}")

            return {
                "memory_id": memory_id,
                "duplicate": False,
                "near_duplicate": near_duplicate,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Failed to store memory: {e}", exc_info=True)
            raise RuntimeError(f"Failed to store memory: {e}") from e

    def search_memory(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Search memories using semantic similarity.

        This method:
        1. Generates query embedding
        2. Performs vector search (gets top N*2 candidates)
        3. Fetches full memory details
        4. Applies composite scoring
        5. Applies filters (tags, priority, date_range)
        6. Sorts by final score
        7. Returns top N results

        Args:
            query: Search query text
            limit: Maximum number of results to return
            filters: Optional filters (tags, priority, date_range)

        Returns:
            Dictionary with:
            - memories: List of scored memories
            - total: Total number of results
            - limit: Requested limit
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        filters = filters or {}

        # Generate query embedding
        logger.debug(f"Generating query embedding for: {query[:50]}...")
        query_embedding = self.embedding_service.generate_embedding(query)

        # Perform vector search (get more candidates than needed for filtering)
        search_limit = limit * 2
        similarity_threshold = self.settings.retrieval.similarity_threshold

        vector_results = self.db_manager.vector_search(
            query_embedding=query_embedding,
            limit=search_limit,
            similarity_threshold=similarity_threshold,
        )

        if not vector_results:
            logger.debug("No vector search results found")
            return {
                "memories": [],
                "total": 0,
                "limit": limit,
            }

        # Fetch full memory details
        memory_ids = [memory_id for memory_id, _ in vector_results]
        similarity_scores = {memory_id: score for memory_id, score in vector_results}

        memories = []
        for memory_id in memory_ids:
            memory = self.db_manager.get_memory_by_id(memory_id)
            if memory:
                memories.append(memory)

        # Apply composite scoring
        scored_memories = score_memories(memories, similarity_scores)

        # Apply filters
        filtered_memories = self._apply_filters(scored_memories, filters)

        # Sort by score (already sorted, but ensure it)
        filtered_memories.sort(key=lambda m: m["score"], reverse=True)

        # Return top N
        result_memories = filtered_memories[:limit]

        logger.info(f"Search returned {len(result_memories)} memories (from {len(memories)} candidates)")

        return {
            "memories": result_memories,
            "total": len(result_memories),
            "limit": limit,
        }

    def list_memories(
        self,
        filters: Optional[dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "DESC",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List memories with filtering and pagination.

        Args:
            filters: Optional filters (priority, tags, project_id, date_range)
            sort_by: Column to sort by
            sort_order: Sort order (ASC or DESC)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Dictionary with:
            - memories: List of memories
            - total: Total number of results
            - limit: Requested limit
            - offset: Requested offset
            - has_more: True if more results available
        """
        filters = filters or {}

        memories = self.db_manager.list_memories(
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit + 1,  # Get one extra to check if there are more
            offset=offset,
        )

        has_more = len(memories) > limit
        if has_more:
            memories = memories[:limit]

        return {
            "memories": memories,
            "total": len(memories),
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }

    def delete_memory(
        self,
        memory_id: Optional[int] = None,
        content_hash: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Delete a memory by ID or content hash.

        Args:
            memory_id: Memory ID to delete
            content_hash: Content hash to delete (alternative to memory_id)

        Returns:
            Dictionary with:
            - success: True if deleted
            - memory_id: ID of deleted memory (if found)

        Raises:
            ValueError: If neither memory_id nor content_hash provided
        """
        if memory_id is None and content_hash is None:
            raise ValueError("Either memory_id or content_hash must be provided")

        # If content_hash provided, find memory_id first
        if memory_id is None:
            memory = self.db_manager.get_memory_by_hash(content_hash)
            if memory:
                memory_id = memory["id"]
            else:
                logger.warning(f"Memory not found for hash: {content_hash[:8]}...")
                return {
                    "success": False,
                    "memory_id": None,
                }

        # Delete from database
        deleted = self.db_manager.delete_memory(memory_id)

        if deleted:
            logger.info(f"Deleted memory with ID: {memory_id}")
            # Note: We don't remove from cache - it will be evicted naturally

        return {
            "success": deleted,
            "memory_id": memory_id if deleted else None,
        }

    def get_memory(self, memory_id: int) -> Optional[dict[str, Any]]:
        """
        Get a memory by ID and increment access count.

        Args:
            memory_id: Memory ID

        Returns:
            Memory dictionary or None if not found
        """
        memory = self.db_manager.get_memory_by_id(memory_id)
        if memory:
            # Increment access count
            self.db_manager.update_access_count(memory_id)
            logger.debug(f"Retrieved memory {memory_id} and incremented access count")
        else:
            logger.warning(f"Memory not found: {memory_id}")

        return memory

    def _check_near_duplicate(
        self,
        embedding: list[float],
        content_hash: str,
    ) -> Optional[dict[str, Any]]:
        """
        Check for near-duplicate memories using vector similarity.

        Args:
            embedding: Embedding vector to check
            content_hash: Content hash (to exclude from search)

        Returns:
            Dictionary with near-duplicate info if found, None otherwise
        """
        threshold = self.settings.deduplication.similarity_threshold

        # Search for similar memories
        similar_results = self.db_manager.vector_search(
            query_embedding=embedding,
            limit=5,  # Check top 5 similar
            similarity_threshold=threshold,
        )

        if not similar_results:
            return None

        # Get the most similar (first result)
        similar_id, similarity = similar_results[0]

        # Exclude exact match (same content hash)
        similar_memory = self.db_manager.get_memory_by_id(similar_id)
        if similar_memory and similar_memory.get("content_hash") == content_hash:
            return None

        logger.info(
            f"Near-duplicate found: memory_id={similar_id}, similarity={similarity:.3f}"
        )

        return {
            "memory_id": similar_id,
            "similarity": similarity,
            "suggestion": "Consider merging with existing memory",
        }

    def _apply_filters(
        self,
        memories: list[dict[str, Any]],
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Apply filters to a list of memories.

        Args:
            memories: List of memory dictionaries
            filters: Filter dictionary (tags, priority, date_range)

        Returns:
            Filtered list of memories
        """
        if not filters:
            return memories

        filtered = []

        for memory in memories:
            # Filter by priority
            if "priority" in filters:
                if memory.get("priority") != filters["priority"]:
                    continue

            # Filter by tags
            if "tags" in filters and filters["tags"]:
                memory_tags = memory.get("tags", [])
                if not isinstance(memory_tags, list):
                    memory_tags = []
                filter_tags = filters["tags"]
                if not isinstance(filter_tags, list):
                    filter_tags = [filter_tags]

                # Check if any filter tag is in memory tags
                if not any(tag in memory_tags for tag in filter_tags):
                    continue

            # Filter by date range
            if "date_range" in filters:
                date_range = filters["date_range"]
                created_at = memory.get("created_at")

                if created_at:
                    # Parse if string
                    if isinstance(created_at, str):
                        try:
                            created_at = datetime.fromisoformat(
                                created_at.replace("Z", "+00:00")
                            )
                        except ValueError:
                            logger.warning(f"Could not parse created_at: {created_at}")
                            continue

                    if "start" in date_range:
                        start_date = date_range["start"]
                        if isinstance(start_date, str):
                            start_date = datetime.fromisoformat(
                                start_date.replace("Z", "+00:00")
                            )
                        if created_at < start_date:
                            continue

                    if "end" in date_range:
                        end_date = date_range["end"]
                        if isinstance(end_date, str):
                            end_date = datetime.fromisoformat(
                                end_date.replace("Z", "+00:00")
                            )
                        if created_at > end_date:
                            continue

            filtered.append(memory)

        return filtered

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

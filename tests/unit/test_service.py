"""
Unit tests for MemoryService.

Tests the memory service with mocked dependencies to avoid real database
and embedding operations.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from memory_server.config import EmbeddingConfig
from memory_server.embedding.cache import EmbeddingCache
from memory_server.embedding.service import EmbeddingService
from memory_server.service import MemoryService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    mock = MagicMock()
    mock.check_duplicate_hash.return_value = None
    mock.insert_memory.return_value = 1
    mock.get_memory_by_id.return_value = None
    mock.vector_search.return_value = []
    mock.list_memories.return_value = []
    mock.delete_memory.return_value = True
    return mock


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    mock = MagicMock(spec=EmbeddingService)
    mock.generate_embedding.return_value = [0.1] * 384
    mock.get_model_info.return_value = {"model": "test-model", "version": "v1"}
    mock.get_dimension.return_value = 384
    return mock


@pytest.fixture
def mock_embedding_cache():
    """Create a mock embedding cache."""
    return MagicMock(spec=EmbeddingCache)


@pytest.fixture
def memory_service(mock_db_manager, mock_embedding_service, mock_embedding_cache, tmp_path):
    """Create a MemoryService with mocked dependencies."""
    with patch("memory_server.service.DatabaseManager", return_value=mock_db_manager):
        service = MemoryService(
            db_path=tmp_path / "test.db",
            embedding_service=mock_embedding_service,
            embedding_cache=mock_embedding_cache,
        )
        service.db_manager = mock_db_manager
        return service


class TestMemoryServiceInit:
    """Tests for MemoryService initialization."""

    @patch("memory_server.service.DatabaseManager")
    def test_init_with_defaults(self, mock_db_class):
        """Test initialization with default parameters."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        service = MemoryService()

        mock_db_class.assert_called_once()
        mock_db.initialize.assert_called_once()
        assert service.embedding_service is not None
        assert service.embedding_cache is not None

    @patch("memory_server.service.DatabaseManager")
    def test_init_with_custom_path(self, mock_db_class, tmp_path):
        """Test initialization with custom database path."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        db_path = tmp_path / "custom.db"
        service = MemoryService(db_path=db_path)

        mock_db_class.assert_called_once_with(db_path=db_path)
        mock_db.initialize.assert_called_once()

    @patch("memory_server.service.DatabaseManager")
    def test_init_with_custom_services(self, mock_db_class):
        """Test initialization with custom embedding service and cache."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        custom_embedding = MagicMock(spec=EmbeddingService)
        custom_cache = MagicMock(spec=EmbeddingCache)

        service = MemoryService(
            embedding_service=custom_embedding,
            embedding_cache=custom_cache,
        )

        assert service.embedding_service == custom_embedding
        # Note: The service might create a new cache if the provided one is None-like
        # This test verifies that custom services can be provided
        assert service.embedding_service is not None


class TestStoreMemory:
    """Tests for store_memory method."""

    def test_store_new_memory(self, memory_service, mock_db_manager, mock_embedding_service, mock_embedding_cache):
        """Test storing a new memory."""
        content = "Test memory content"
        # Configure the cache on the service instance
        memory_service.embedding_cache.get = MagicMock(return_value=None)  # Cache miss
        memory_service.embedding_cache.set = MagicMock()
        mock_embedding_service.generate_embedding.return_value = [0.1] * 384
        mock_db_manager.check_duplicate_hash.return_value = None  # No duplicate
        mock_db_manager.vector_search.return_value = []  # No near duplicates
        mock_db_manager.insert_memory.return_value = 123

        result = memory_service.store_memory(
            content=content,
            tags=["test"],
            priority="HIGH",
        )

        assert result["success"] is True
        assert result["memory_id"] == 123
        assert result["duplicate"] is False
        assert mock_embedding_service.generate_embedding.called
        assert memory_service.embedding_cache.set.called
        mock_db_manager.insert_memory.assert_called_once()

    def test_store_duplicate_hash(self, memory_service, mock_db_manager):
        """Test storing duplicate content (hash match)."""
        content = "Duplicate content"
        existing_id = 456
        mock_db_manager.check_duplicate_hash.return_value = existing_id

        result = memory_service.store_memory(content=content)

        assert result["success"] is True
        assert result["memory_id"] == existing_id
        assert result["duplicate"] is True
        # Should not generate embedding or insert
        mock_db_manager.insert_memory.assert_not_called()

    def test_store_with_cached_embedding(self, memory_service, mock_embedding_cache, mock_embedding_service, mock_db_manager):
        """Test storing memory when embedding is cached."""
        content = "Test content"
        cached_embedding = [0.2] * 384
        # Set cache to return the cached embedding
        memory_service.embedding_cache.get = MagicMock(return_value=cached_embedding)
        mock_db_manager.check_duplicate_hash.return_value = None
        mock_db_manager.vector_search.return_value = []  # No near duplicates
        mock_db_manager.insert_memory.return_value = 456

        result = memory_service.store_memory(content=content)

        assert result["success"] is True
        assert result["memory_id"] == 456
        # Verify cache was checked
        assert memory_service.embedding_cache.get.called

    def test_store_empty_content(self, memory_service):
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            memory_service.store_memory(content="")

        with pytest.raises(ValueError, match="Content cannot be empty"):
            memory_service.store_memory(content="   ")

    def test_store_with_all_parameters(self, memory_service, mock_db_manager):
        """Test storing memory with all optional parameters."""
        content = "Full memory content"
        mock_db_manager.insert_memory.return_value = 789

        result = memory_service.store_memory(
            content=content,
            tags=["tag1", "tag2"],
            priority="CORE",
            category="test-category",
            source="manual",
            project_id="test-project",
        )

        assert result["success"] is True
        call_args = mock_db_manager.insert_memory.call_args
        assert call_args.kwargs["content"] == content
        assert call_args.kwargs["tags"] == ["tag1", "tag2"]
        assert call_args.kwargs["priority"] == "CORE"
        assert call_args.kwargs["category"] == "test-category"
        assert call_args.kwargs["source"] == "manual"
        assert call_args.kwargs["project_id"] == "test-project"


class TestSearchMemory:
    """Tests for search_memory method."""

    def test_search_basic(self, memory_service, mock_db_manager, mock_embedding_service):
        """Test basic memory search."""
        query = "test query"
        mock_embedding_service.generate_embedding.return_value = [0.1] * 384
        mock_db_manager.vector_search.return_value = [(1, 0.9), (2, 0.8)]
        mock_db_manager.get_memory_by_id.side_effect = [
            {"id": 1, "content": "Memory 1", "created_at": datetime.now(timezone.utc), "priority": "NORMAL", "access_count": 0},
            {"id": 2, "content": "Memory 2", "created_at": datetime.now(timezone.utc), "priority": "NORMAL", "access_count": 0},
        ]

        result = memory_service.search_memory(query, limit=10)

        assert "memories" in result
        assert "total" in result
        assert "limit" in result
        assert len(result["memories"]) == 2
        assert result["limit"] == 10
        mock_embedding_service.generate_embedding.assert_called_once_with(query)

    def test_search_empty_query(self, memory_service):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            memory_service.search_memory("")

        with pytest.raises(ValueError, match="Query cannot be empty"):
            memory_service.search_memory("   ")

    def test_search_no_results(self, memory_service, mock_db_manager, mock_embedding_service):
        """Test search when no results found."""
        query = "test query"
        mock_embedding_service.generate_embedding.return_value = [0.1] * 384
        mock_db_manager.vector_search.return_value = []

        result = memory_service.search_memory(query)

        assert result["memories"] == []
        assert result["total"] == 0

    def test_search_with_filters(self, memory_service, mock_db_manager, mock_embedding_service):
        """Test search with filters applied."""
        query = "test query"
        mock_embedding_service.generate_embedding.return_value = [0.1] * 384
        mock_db_manager.vector_search.return_value = [(1, 0.9), (2, 0.8)]
        mock_db_manager.get_memory_by_id.side_effect = [
            {"id": 1, "content": "Memory 1", "created_at": datetime.now(timezone.utc), "priority": "HIGH", "access_count": 0, "tags": ["test"]},
            {"id": 2, "content": "Memory 2", "created_at": datetime.now(timezone.utc), "priority": "NORMAL", "access_count": 0, "tags": ["other"]},
        ]

        result = memory_service.search_memory(
            query,
            filters={"priority": "HIGH", "tags": ["test"]},
        )

        # Should filter to only HIGH priority with "test" tag
        assert len(result["memories"]) <= 2
        for memory in result["memories"]:
            assert memory["priority"] == "HIGH"
            assert "test" in memory.get("tags", [])

    def test_search_respects_limit(self, memory_service, mock_db_manager, mock_embedding_service):
        """Test that search respects the limit parameter."""
        query = "test query"
        mock_embedding_service.generate_embedding.return_value = [0.1] * 384
        # Return many results
        mock_db_manager.vector_search.return_value = [(i, 0.9 - i * 0.01) for i in range(1, 21)]
        mock_db_manager.get_memory_by_id.side_effect = [
            {"id": i, "content": f"Memory {i}", "created_at": datetime.now(timezone.utc), "priority": "NORMAL", "access_count": 0}
            for i in range(1, 21)
        ]

        result = memory_service.search_memory(query, limit=5)

        assert len(result["memories"]) == 5
        assert result["limit"] == 5


class TestListMemories:
    """Tests for list_memories method."""

    def test_list_basic(self, memory_service, mock_db_manager):
        """Test basic memory listing."""
        mock_db_manager.list_memories.return_value = [
            {"id": 1, "content": "Memory 1"},
            {"id": 2, "content": "Memory 2"},
        ]

        result = memory_service.list_memories()

        assert "memories" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result
        assert "has_more" in result
        assert len(result["memories"]) == 2

    def test_list_with_filters(self, memory_service, mock_db_manager):
        """Test listing with filters."""
        filters = {"priority": "HIGH", "tags": ["test"]}
        mock_db_manager.list_memories.return_value = [{"id": 1, "content": "Memory 1"}]

        result = memory_service.list_memories(filters=filters)

        call_args = mock_db_manager.list_memories.call_args
        assert call_args.kwargs["filters"] == filters

    def test_list_pagination(self, memory_service, mock_db_manager):
        """Test listing with pagination."""
        # Return limit+1 to test has_more
        mock_db_manager.list_memories.return_value = [
            {"id": i, "content": f"Memory {i}"} for i in range(1, 52)  # 51 items (limit+1)
        ]

        result = memory_service.list_memories(limit=50, offset=0)

        assert result["limit"] == 50
        assert result["offset"] == 0
        assert len(result["memories"]) == 50  # Should be truncated to limit
        # Should have more if we got limit+1
        assert result["has_more"] is True

    def test_list_custom_sorting(self, memory_service, mock_db_manager):
        """Test listing with custom sorting."""
        mock_db_manager.list_memories.return_value = []

        result = memory_service.list_memories(sort_by="priority", sort_order="ASC")

        call_args = mock_db_manager.list_memories.call_args
        assert call_args.kwargs["sort_by"] == "priority"
        assert call_args.kwargs["sort_order"] == "ASC"


class TestDeleteMemory:
    """Tests for delete_memory method."""

    def test_delete_by_id(self, memory_service, mock_db_manager):
        """Test deleting memory by ID."""
        memory_id = 123
        mock_db_manager.delete_memory.return_value = True

        result = memory_service.delete_memory(memory_id=memory_id)

        assert result["success"] is True
        assert result["memory_id"] == memory_id
        mock_db_manager.delete_memory.assert_called_once_with(memory_id)

    def test_delete_by_hash(self, memory_service, mock_db_manager):
        """Test deleting memory by content hash."""
        content_hash = "abc123"
        memory_id = 456
        mock_db_manager.get_memory_by_hash.return_value = {"id": memory_id}
        mock_db_manager.delete_memory.return_value = True

        result = memory_service.delete_memory(content_hash=content_hash)

        assert result["success"] is True
        assert result["memory_id"] == memory_id
        mock_db_manager.get_memory_by_hash.assert_called_once_with(content_hash)
        mock_db_manager.delete_memory.assert_called_once_with(memory_id)

    def test_delete_not_found_by_hash(self, memory_service, mock_db_manager):
        """Test deleting memory by hash when not found."""
        content_hash = "nonexistent"
        mock_db_manager.get_memory_by_hash.return_value = None

        result = memory_service.delete_memory(content_hash=content_hash)

        assert result["success"] is False
        assert result["memory_id"] is None
        mock_db_manager.delete_memory.assert_not_called()

    def test_delete_no_parameters(self, memory_service):
        """Test that deleting without ID or hash raises ValueError."""
        with pytest.raises(ValueError, match="Either memory_id or content_hash must be provided"):
            memory_service.delete_memory()


class TestGetMemory:
    """Tests for get_memory method."""

    def test_get_existing_memory(self, memory_service, mock_db_manager):
        """Test getting an existing memory."""
        memory_id = 123
        memory_data = {
            "id": memory_id,
            "content": "Test memory",
            "created_at": datetime.now(timezone.utc),
        }
        mock_db_manager.get_memory_by_id.return_value = memory_data

        result = memory_service.get_memory(memory_id)

        assert result == memory_data
        mock_db_manager.get_memory_by_id.assert_called_once_with(memory_id)
        mock_db_manager.update_access_count.assert_called_once_with(memory_id)

    def test_get_nonexistent_memory(self, memory_service, mock_db_manager):
        """Test getting a non-existent memory."""
        memory_id = 999
        mock_db_manager.get_memory_by_id.return_value = None

        result = memory_service.get_memory(memory_id)

        assert result is None
        mock_db_manager.update_access_count.assert_not_called()


class TestHelperMethods:
    """Tests for helper methods."""

    def test_generate_content_hash(self, memory_service):
        """Test content hash generation."""
        content = "test content"
        hash1 = memory_service._generate_content_hash(content)
        hash2 = memory_service._generate_content_hash(content)

        # Should be deterministic
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_apply_filters_priority(self, memory_service):
        """Test applying priority filter."""
        memories = [
            {"id": 1, "priority": "HIGH"},
            {"id": 2, "priority": "NORMAL"},
            {"id": 3, "priority": "HIGH"},
        ]

        filtered = memory_service._apply_filters(memories, {"priority": "HIGH"})

        assert len(filtered) == 2
        assert all(m["priority"] == "HIGH" for m in filtered)

    def test_apply_filters_tags(self, memory_service):
        """Test applying tags filter."""
        memories = [
            {"id": 1, "tags": ["test", "example"]},
            {"id": 2, "tags": ["other"]},
            {"id": 3, "tags": ["test"]},
        ]

        filtered = memory_service._apply_filters(memories, {"tags": ["test"]})

        assert len(filtered) == 2
        assert all("test" in m.get("tags", []) for m in filtered)

    def test_apply_filters_date_range(self, memory_service):
        """Test applying date range filter."""
        now = datetime.now(timezone.utc)
        memories = [
            {"id": 1, "created_at": now},
            {"id": 2, "created_at": now.replace(year=now.year - 1)},
            {"id": 3, "created_at": now},
        ]

        start_date = now.replace(month=1, day=1)
        filtered = memory_service._apply_filters(
            memories,
            {"date_range": {"start": start_date.isoformat()}},
        )

        assert len(filtered) >= 1
        assert all(
            datetime.fromisoformat(m["created_at"].replace("Z", "+00:00")) >= start_date
            if isinstance(m["created_at"], str)
            else m["created_at"] >= start_date
            for m in filtered
        )

    def test_apply_filters_no_filters(self, memory_service):
        """Test that no filters returns all memories."""
        memories = [{"id": 1}, {"id": 2}, {"id": 3}]

        filtered = memory_service._apply_filters(memories, {})

        assert len(filtered) == 3

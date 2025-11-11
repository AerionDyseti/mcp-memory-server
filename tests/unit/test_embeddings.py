"""
Unit tests for embedding service and cache.

Tests EmbeddingService and EmbeddingCache with mocked dependencies
to avoid downloading real models.
"""

import hashlib
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from memory_server.config import EmbeddingConfig, get_settings
from memory_server.embedding.cache import EmbeddingCache
from memory_server.embedding.service import EmbeddingService

pytestmark = pytest.mark.unit


class TestEmbeddingCache:
    """Tests for EmbeddingCache class."""

    def test_init_default_size(self):
        """Test cache initialization with default size."""
        cache = EmbeddingCache()
        assert cache.max_size == 1000
        assert len(cache) == 0

    def test_init_custom_size(self):
        """Test cache initialization with custom size."""
        cache = EmbeddingCache(max_size=50)
        assert cache.max_size == 50
        assert len(cache) == 0

    def test_set_and_get(self, embedding_cache, sample_embedding):
        """Test storing and retrieving embeddings."""
        content_hash = "abc123"
        
        # Store embedding
        embedding_cache.set(content_hash, sample_embedding)
        assert len(embedding_cache) == 1
        
        # Retrieve embedding
        retrieved = embedding_cache.get(content_hash)
        assert retrieved == sample_embedding

    def test_get_nonexistent(self, embedding_cache):
        """Test retrieving non-existent embedding returns None."""
        result = embedding_cache.get("nonexistent")
        assert result is None

    def test_lru_eviction(self, small_embedding_cache, sample_embedding):
        """Test LRU eviction when cache reaches capacity."""
        # Fill cache to capacity
        for i in range(5):
            small_embedding_cache.set(f"hash_{i}", sample_embedding)
        
        assert len(small_embedding_cache) == 5
        
        # Access first item to mark as recently used
        small_embedding_cache.get("hash_0")
        
        # Add new item - should evict hash_1 (least recently used)
        small_embedding_cache.set("hash_5", sample_embedding)
        
        assert len(small_embedding_cache) == 5
        assert small_embedding_cache.get("hash_0") is not None  # Still in cache
        assert small_embedding_cache.get("hash_1") is None  # Evicted
        assert small_embedding_cache.get("hash_5") is not None  # New item

    def test_lru_access_order(self, small_embedding_cache, sample_embedding):
        """Test that accessing items updates their position in LRU order."""
        # Add items
        for i in range(5):
            small_embedding_cache.set(f"hash_{i}", sample_embedding)
        
        # Access hash_2 should mark it as recently used
        small_embedding_cache.get("hash_2")
        
        # Add new item - should evict hash_0 (oldest, not recently accessed)
        small_embedding_cache.set("hash_5", sample_embedding)
        
        assert small_embedding_cache.get("hash_0") is None  # Evicted
        assert small_embedding_cache.get("hash_2") is not None  # Still in cache

    def test_set_overwrites_existing(self, embedding_cache, sample_embedding):
        """Test that setting same hash overwrites existing value."""
        content_hash = "abc123"
        embedding1 = [0.1] * 384
        embedding2 = [0.2] * 384
        
        embedding_cache.set(content_hash, embedding1)
        assert embedding_cache.get(content_hash) == embedding1
        
        embedding_cache.set(content_hash, embedding2)
        assert len(embedding_cache) == 1  # Still only one entry
        assert embedding_cache.get(content_hash) == embedding2

    def test_clear(self, embedding_cache, sample_embedding):
        """Test clearing the cache."""
        # Add some items
        for i in range(5):
            embedding_cache.set(f"hash_{i}", sample_embedding)
        
        assert len(embedding_cache) == 5
        
        # Clear cache
        embedding_cache.clear()
        
        assert len(embedding_cache) == 0
        assert embedding_cache.get("hash_0") is None

    def test_size_method(self, embedding_cache, sample_embedding):
        """Test size() method returns correct count."""
        assert embedding_cache.size() == 0
        
        embedding_cache.set("hash_1", sample_embedding)
        assert embedding_cache.size() == 1
        
        embedding_cache.set("hash_2", sample_embedding)
        assert embedding_cache.size() == 2

    def test_len_dunder(self, embedding_cache, sample_embedding):
        """Test __len__ method works with len() function."""
        assert len(embedding_cache) == 0
        
        embedding_cache.set("hash_1", sample_embedding)
        assert len(embedding_cache) == 1

    def test_set_empty_embedding(self, embedding_cache):
        """Test that setting empty embedding is handled gracefully."""
        embedding_cache.set("hash_1", [])
        # Should not crash, but may log warning
        assert len(embedding_cache) == 0  # Empty embeddings not cached

    def test_thread_safety(self, embedding_cache, sample_embedding):
        """Test that cache operations are thread-safe."""
        import threading
        
        def add_items(start_idx, count):
            for i in range(start_idx, start_idx + count):
                embedding_cache.set(f"hash_{i}", sample_embedding)
        
        # Run multiple threads adding items concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_items, args=(i * 10, 10))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All items should be in cache
        assert len(embedding_cache) == 50
        for i in range(50):
            assert embedding_cache.get(f"hash_{i}") is not None


class TestEmbeddingService:
    """Tests for EmbeddingService class."""

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_init_with_default_config(self, mock_text_embedding_class):
        """Test initialization with default config from settings."""
        mock_model = MagicMock()
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        
        # Should use settings from get_settings()
        settings = get_settings()
        mock_text_embedding_class.assert_called_once_with(
            model_name=settings.embedding.model,
            device=settings.embedding.device,
            show_progress=True,
        )
        assert service.config == settings.embedding
        assert service.model == mock_model

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_init_with_custom_config(self, mock_text_embedding_class):
        """Test initialization with custom config."""
        mock_model = MagicMock()
        mock_text_embedding_class.return_value = mock_model
        
        custom_config = EmbeddingConfig(
            model="custom-model",
            dimension=384,
            device="cpu",
        )
        
        service = EmbeddingService(config=custom_config)
        
        mock_text_embedding_class.assert_called_once_with(
            model_name="custom-model",
            device="cpu",
            show_progress=True,
        )
        assert service.config == custom_config

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_init_model_load_failure(self, mock_text_embedding_class):
        """Test that initialization failure raises RuntimeError."""
        mock_text_embedding_class.side_effect = Exception("Model not found")
        
        with pytest.raises(RuntimeError, match="Failed to initialize embedding model"):
            EmbeddingService()

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_generate_embedding(self, mock_text_embedding_class):
        """Test generating embedding for single text."""
        # Create mock embedding
        mock_embedding = np.random.RandomState(42).rand(384)
        norm = np.linalg.norm(mock_embedding)
        mock_embedding = (mock_embedding / norm).tolist()
        
        mock_model = MagicMock()
        mock_model.embed.return_value = iter([np.array(mock_embedding)])
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        result = service.generate_embedding("test text")
        
        assert len(result) == 384
        assert isinstance(result, list)
        # Check normalization (L2 norm should be ~1.0)
        norm_result = np.linalg.norm(result)
        assert abs(norm_result - 1.0) < 0.01

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_generate_embedding_empty_text(self, mock_text_embedding_class):
        """Test that empty text raises ValueError."""
        mock_model = MagicMock()
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        
        with pytest.raises(ValueError, match="Cannot generate embedding for empty text"):
            service.generate_embedding("")

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_generate_embedding_failure(self, mock_text_embedding_class):
        """Test that embedding generation failure raises RuntimeError."""
        mock_model = MagicMock()
        mock_model.embed.side_effect = Exception("Embedding failed")
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        
        with pytest.raises(RuntimeError, match="Failed to generate embedding"):
            service.generate_embedding("test text")

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_generate_embeddings_batch(self, mock_text_embedding_class):
        """Test generating embeddings for batch of texts."""
        texts = ["text 1", "text 2", "text 3"]
        
        # Create mock embeddings
        mock_embeddings = []
        for i, text in enumerate(texts):
            emb = np.random.RandomState(i).rand(384)
            norm = np.linalg.norm(emb)
            mock_embeddings.append(emb / norm)
        
        mock_model = MagicMock()
        mock_model.embed.return_value = iter(mock_embeddings)
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        results = service.generate_embeddings_batch(texts)
        
        assert len(results) == 3
        for result in results:
            assert len(result) == 384
            assert isinstance(result, list)
            # Check normalization
            norm_result = np.linalg.norm(result)
            assert abs(norm_result - 1.0) < 0.01

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_generate_embeddings_batch_empty_list(self, mock_text_embedding_class):
        """Test that empty text list raises ValueError."""
        mock_model = MagicMock()
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        
        with pytest.raises(ValueError, match="Cannot generate embeddings for empty text list"):
            service.generate_embeddings_batch([])

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_generate_embeddings_batch_all_empty_texts(self, mock_text_embedding_class):
        """Test batch with all empty texts raises RuntimeError."""
        mock_model = MagicMock()
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        
        with pytest.raises(RuntimeError, match="All texts in batch are empty"):
            service.generate_embeddings_batch(["", "", ""])

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_generate_embeddings_batch_mixed_empty(self, mock_text_embedding_class):
        """Test batch with some empty texts handles them correctly."""
        texts = ["text 1", "", "text 3"]
        
        # Create mock embeddings for non-empty texts
        mock_embeddings = []
        for i in [0, 2]:  # Only for non-empty texts
            emb = np.random.RandomState(i).rand(384)
            norm = np.linalg.norm(emb)
            mock_embeddings.append(emb / norm)
        
        mock_model = MagicMock()
        mock_model.embed.return_value = iter(mock_embeddings)
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        results = service.generate_embeddings_batch(texts)
        
        assert len(results) == 3
        assert len(results[0]) == 384  # First text has embedding
        assert results[1] == [0.0] * 384  # Empty text gets zero vector
        assert len(results[2]) == 384  # Third text has embedding

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_get_model_info(self, mock_text_embedding_class):
        """Test getting model information."""
        mock_model = MagicMock()
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        info = service.get_model_info()
        
        assert "model" in info
        assert "version" in info
        assert info["model"] == service.config.model

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_get_dimension(self, mock_text_embedding_class):
        """Test getting embedding dimension."""
        mock_model = MagicMock()
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        dimension = service.get_dimension()
        
        assert dimension == 384
        assert dimension == service.config.dimension

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_normalize_embedding(self, mock_text_embedding_class):
        """Test embedding normalization helper."""
        mock_model = MagicMock()
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        
        # Create non-normalized vector
        vector = np.array([1.0, 2.0, 3.0] * 128)  # 384 dim
        normalized = service._normalize_embedding(vector)
        
        # Check it's normalized
        norm = np.linalg.norm(normalized)
        assert abs(norm - 1.0) < 0.01
        
        # Check it's a list
        assert isinstance(normalized, list)
        assert len(normalized) == 384

    @patch("memory_server.embedding.service.TextEmbedding")
    def test_normalize_zero_vector(self, mock_text_embedding_class):
        """Test normalization of zero vector."""
        mock_model = MagicMock()
        mock_text_embedding_class.return_value = mock_model
        
        service = EmbeddingService()
        
        # Zero vector
        vector = np.zeros(384)
        normalized = service._normalize_embedding(vector)
        
        # Should return zero vector as-is
        assert normalized == [0.0] * 384

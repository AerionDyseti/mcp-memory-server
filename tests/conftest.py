"""
Shared pytest fixtures for memory server tests.
"""

import hashlib
from unittest.mock import MagicMock

import numpy as np
import pytest

from memory_server.config import EmbeddingConfig
from memory_server.embedding.cache import EmbeddingCache
from memory_server.embedding.service import EmbeddingService


@pytest.fixture
def mock_embedding_service(monkeypatch):
    """
    Mock EmbeddingService that returns deterministic embeddings.

    Returns deterministic embeddings based on text hash to avoid
    downloading real models in unit tests.
    """
    def generate_mock_embedding(text: str, dimension: int = 384) -> list[float]:
        """Generate deterministic embedding from text hash."""
        # Create deterministic vector from text hash
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        # Generate vector with values between 0 and 1
        vector = [(hash_val % 1000 + i) / 1000.0 for i in range(dimension)]
        # Normalize to unit vector
        arr = np.array(vector)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    mock_service = MagicMock(spec=EmbeddingService)
    mock_service.config = EmbeddingConfig()
    mock_service.generate_embedding.side_effect = lambda text: generate_mock_embedding(
        text, 384
    )
    mock_service.generate_embeddings_batch.side_effect = (
        lambda texts: [generate_mock_embedding(text, 384) for text in texts]
    )
    mock_service.get_model_info.return_value = {
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "version": "v2",
    }
    mock_service.get_dimension.return_value = 384

    return mock_service


@pytest.fixture
def embedding_cache():
    """Create a fresh EmbeddingCache instance for each test."""
    return EmbeddingCache(max_size=1000)


@pytest.fixture
def small_embedding_cache():
    """Create a small EmbeddingCache instance (max_size=5) for testing eviction."""
    return EmbeddingCache(max_size=5)


@pytest.fixture
def sample_embedding():
    """Generate a sample normalized embedding vector."""
    # Create a deterministic 384-dim embedding
    vector = np.random.RandomState(42).rand(384)
    # Normalize to unit vector
    norm = np.linalg.norm(vector)
    return (vector / norm).tolist()


@pytest.fixture
def sample_texts():
    """Sample texts for testing batch operations."""
    return [
        "Use FastAPI for REST APIs with automatic OpenAPI documentation",
        "SQLite WAL mode enables concurrent reads",
        "Python async context manager pattern for resource cleanup",
    ]

"""
Thread-safe LRU cache for storing embeddings.

This module provides the EmbeddingCache class which implements a least recently used
(LRU) cache for embeddings to avoid redundant computation.
"""

from collections import OrderedDict
from threading import RLock
from typing import Optional

from memory_server.utils import get_logger

logger = get_logger(__name__)


class EmbeddingCache:
    """
    Thread-safe LRU cache for embeddings.

    This cache stores embeddings keyed by content hash to avoid
    regenerating embeddings for the same content. It uses an
    OrderedDict to maintain insertion order and implements LRU
    eviction when the cache reaches its maximum size.

    Attributes:
        max_size: Maximum number of entries in the cache
        cache: OrderedDict storing content_hash -> embedding mappings
        lock: RLock for thread-safe operations
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize the embedding cache.

        Args:
            max_size: Maximum number of entries to store (default: 1000)
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, list[float]] = OrderedDict()
        self.lock = RLock()
        
        logger.debug(f"Initialized EmbeddingCache with max_size={max_size}")

    def get(self, content_hash: str) -> Optional[list[float]]:
        """
        Get an embedding from the cache.

        Args:
            content_hash: Hash of the content to retrieve embedding for

        Returns:
            Embedding vector if found, None otherwise

        Note:
            Accessing an item moves it to the end (most recently used)
        """
        with self.lock:
            if content_hash not in self.cache:
                logger.debug(f"Cache miss for hash: {content_hash[:8]}...")
                return None
            
            # Move to end (mark as recently used)
            embedding = self.cache.pop(content_hash)
            self.cache[content_hash] = embedding
            
            logger.debug(f"Cache hit for hash: {content_hash[:8]}...")
            return embedding

    def set(self, content_hash: str, embedding: list[float]) -> None:
        """
        Store an embedding in the cache.

        Args:
            content_hash: Hash of the content
            embedding: Embedding vector to store

        Note:
            If cache is at capacity, the least recently used item is evicted
        """
        if not embedding:
            logger.warning("Attempted to cache empty embedding")
            return
        
        with self.lock:
            # Remove item if it already exists (will be re-added at end)
            if content_hash in self.cache:
                self.cache.pop(content_hash)
            
            # Check if we need to evict oldest item
            elif len(self.cache) >= self.max_size:
                # Remove least recently used (first item)
                oldest_key = next(iter(self.cache))
                self.cache.pop(oldest_key)
                logger.debug(
                    f"Evicted oldest cache entry: {oldest_key[:8]}... "
                    f"(cache at capacity: {self.max_size})"
                )
            
            # Add new item at end (most recently used)
            self.cache[content_hash] = embedding
            logger.debug(
                f"Cached embedding for hash: {content_hash[:8]}... "
                f"(cache size: {len(self.cache)})"
            )

    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self.lock:
            size_before = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared embedding cache ({size_before} entries removed)")

    def size(self) -> int:
        """
        Get the current number of entries in the cache.

        Returns:
            Number of cached embeddings
        """
        with self.lock:
            return len(self.cache)

    def __len__(self) -> int:
        """
        Get the current number of entries in the cache.

        Returns:
            Number of cached embeddings

        Note:
            This allows using len(cache) syntax
        """
        return self.size()

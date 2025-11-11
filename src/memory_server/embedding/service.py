"""
Embedding service for generating text embeddings.

This module provides the EmbeddingService class which uses FastEmbed to generate
384-dimensional embeddings for text content.
"""

from typing import Any, Optional

import numpy as np
from fastembed import TextEmbedding

from memory_server.config import EmbeddingConfig, get_settings
from memory_server.utils import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using FastEmbed.

    This service handles:
    - Embedding generation for single texts
    - Batch embedding generation
    - Model initialization and management
    - Embedding normalization

    Attributes:
        config: Embedding configuration
        model: FastEmbed TextEmbedding model instance
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initialize the embedding service.

        Args:
            config: Optional embedding configuration. If not provided,
                   uses settings from get_settings().embedding

        Raises:
            RuntimeError: If model initialization fails
        """
        if config is None:
            config = get_settings().embedding

        self.config = config
        logger.info(
            f"Initializing EmbeddingService with model: {config.model}, "
            f"dimension: {config.dimension}, device: {config.device}"
        )

        try:
            # Initialize FastEmbed TextEmbedding model
            self.model = TextEmbedding(
                model_name=config.model,
                device=config.device,
                show_progress=True,  # Show download progress on first run
            )
            logger.info("EmbeddingService initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize embedding model '{config.model}': {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to generate embedding for

        Returns:
            384-dimensional normalized embedding vector as list of floats

        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding generation fails
        """
        if not text:
            raise ValueError("Cannot generate embedding for empty text")

        try:
            logger.debug(f"Generating embedding for text of length {len(text)}")
            
            # FastEmbed returns a generator, we need to convert to list
            embeddings = list(self.model.embed([text]))
            
            if not embeddings or len(embeddings) == 0:
                raise RuntimeError("No embedding returned from model")
            
            # Get the first (and only) embedding
            embedding = embeddings[0]
            
            # Normalize and convert to list
            normalized = self._normalize_embedding(embedding)
            
            logger.debug(f"Generated embedding with dimension {len(normalized)}")
            return normalized

        except Exception as e:
            error_msg = f"Failed to generate embedding: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to generate embeddings for

        Returns:
            List of 384-dimensional normalized embedding vectors

        Raises:
            ValueError: If texts list is empty
            RuntimeError: If embedding generation fails
        """
        if not texts:
            raise ValueError("Cannot generate embeddings for empty text list")

        try:
            logger.debug(f"Generating embeddings for {len(texts)} texts")
            
            # Filter out empty texts but keep track of indices
            valid_indices = []
            valid_texts = []
            for i, text in enumerate(texts):
                if text:
                    valid_indices.append(i)
                    valid_texts.append(text)
            
            if not valid_texts:
                raise ValueError("All texts in batch are empty")
            
            # Generate embeddings for valid texts
            embeddings_generator = self.model.embed(valid_texts)
            valid_embeddings = list(embeddings_generator)
            
            # Normalize embeddings
            normalized_embeddings = [
                self._normalize_embedding(emb) for emb in valid_embeddings
            ]
            
            # Reconstruct full list with empty embeddings for empty texts
            result = []
            valid_idx = 0
            for i in range(len(texts)):
                if i in valid_indices:
                    result.append(normalized_embeddings[valid_idx])
                    valid_idx += 1
                else:
                    # Return zero vector for empty texts
                    result.append([0.0] * self.config.dimension)
            
            logger.debug(f"Generated {len(result)} embeddings")
            return result

        except Exception as e:
            error_msg = f"Failed to generate batch embeddings: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def get_model_info(self) -> dict[str, str]:
        """
        Get information about the embedding model.

        Returns:
            Dictionary with model name and version
        """
        return {
            "model": self.config.model,
            "version": "unknown",  # FastEmbed doesn't expose version info easily
        }

    def get_dimension(self) -> int:
        """
        Get the dimension of the embeddings.

        Returns:
            Embedding dimension (384)
        """
        return self.config.dimension

    def _normalize_embedding(self, embedding: np.ndarray) -> list[float]:
        """
        Normalize embedding to unit vector.

        Args:
            embedding: Numpy array embedding

        Returns:
            Normalized embedding as list of floats

        Note:
            Handles zero vectors by returning them as-is
        """
        # Convert to numpy array if needed
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)
        
        # Calculate L2 norm
        norm = np.linalg.norm(embedding)
        
        # Handle zero vector
        if norm == 0:
            logger.warning("Zero vector encountered during normalization")
            return embedding.tolist()
        
        # Normalize to unit vector
        normalized = embedding / norm
        
        return normalized.tolist()

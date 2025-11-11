"""
Configuration settings for the memory server.

Manages global configuration including embedding models, retrieval settings,
and automatic triggers.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""

    model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model to use",
    )
    dimension: int = Field(
        default=384,
        description="Embedding vector dimension",
    )
    device: Literal["cpu", "cuda", "mps"] = Field(
        default="cpu",
        description="Device to run embeddings on",
    )


class ScoringWeights(BaseModel):
    """Weights for multi-factor scoring algorithm."""

    similarity: float = Field(default=0.4, ge=0.0, le=1.0)
    recency: float = Field(default=0.2, ge=0.0, le=1.0)
    priority: float = Field(default=0.2, ge=0.0, le=1.0)
    usage: float = Field(default=0.2, ge=0.0, le=1.0)


class RetrievalConfig(BaseModel):
    """Configuration for memory retrieval."""

    default_limit: int = Field(
        default=10,
        description="Default number of memories to retrieve",
    )
    session_start_limit: int = Field(
        default=8,
        description="Number of memories to retrieve at session start",
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for retrieval",
    )
    scoring_weights: ScoringWeights = Field(
        default_factory=ScoringWeights,
        description="Weights for scoring factors",
    )


class AutoTriggersConfig(BaseModel):
    """Configuration for automatic memory triggers."""

    session_end: bool = Field(
        default=True,
        description="Generate memories at session end",
    )
    decision_detection: bool = Field(
        default=True,
        description="Detect and store key decisions",
    )
    error_resolution: bool = Field(
        default=True,
        description="Store error resolutions",
    )


class DeduplicationConfig(BaseModel):
    """Configuration for memory deduplication."""

    auto_check: bool = Field(
        default=True,
        description="Automatically check for duplicates on store",
    )
    similarity_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for duplicate detection",
    )


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database paths
    global_db_path: Path = Field(
        default_factory=lambda: Path.home() / ".memory" / "db",
        description="Path to global memory database",
    )

    # Component configurations
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Embedding configuration",
    )
    retrieval: RetrievalConfig = Field(
        default_factory=RetrievalConfig,
        description="Retrieval configuration",
    )
    auto_triggers: AutoTriggersConfig = Field(
        default_factory=AutoTriggersConfig,
        description="Auto-trigger configuration",
    )
    deduplication: DeduplicationConfig = Field(
        default_factory=DeduplicationConfig,
        description="Deduplication configuration",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )

    def get_log_dir(self) -> Path:
        """Get the logging directory path."""
        log_dir = Path.home() / ".memory" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment/config files."""
    global _settings
    _settings = Settings()
    return _settings

"""
Scoring algorithms for memory retrieval.

This module provides multi-factor scoring functions that combine vector similarity,
recency, priority, and usage frequency to rank memories for retrieval.
"""

import math
from datetime import datetime, timezone
from typing import Any, Optional

from memory_server.config import ScoringWeights, get_settings
from memory_server.utils import get_logger

logger = get_logger(__name__)


def calculate_recency_score(created_at: datetime | str) -> float:
    """
    Calculate recency score using exponential decay.

    Formula: e^(-days/30)
    - Memories from today: score ≈ 1.0
    - Memories from 30 days ago: score ≈ 0.368 (1/e)
    - Memories from 60 days ago: score ≈ 0.135 (1/e²)
    - Older memories decay exponentially

    Args:
        created_at: Creation timestamp (datetime or ISO string)

    Returns:
        Recency score between 0.0 and 1.0 (higher = more recent)

    Examples:
        >>> from datetime import datetime, timedelta
        >>> now = datetime.now(timezone.utc)
        >>> calculate_recency_score(now)  # Very recent
        1.0
        >>> calculate_recency_score(now - timedelta(days=30))  # 30 days old
        0.368...
    """
    # Parse string to datetime if needed
    if isinstance(created_at, str):
        try:
            # Try ISO format first
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            # Fallback to common formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                try:
                    created_at = datetime.strptime(created_at, fmt)
                    break
                except ValueError:
                    continue
            else:
                logger.warning(f"Could not parse created_at: {created_at}, using 0.0 score")
                return 0.0

    # Ensure timezone-aware datetime
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    # Calculate days since creation
    now = datetime.now(timezone.utc)
    delta = now - created_at
    days = delta.total_seconds() / (24 * 60 * 60)

    # Exponential decay: e^(-days/30)
    # For negative days (future dates), clamp to 1.0
    if days < 0:
        logger.warning(f"Future date detected: {created_at}, using 1.0 score")
        return 1.0

    score = math.exp(-days / 30.0)
    
    # Clamp to [0, 1] range (shouldn't be needed, but safety check)
    return max(0.0, min(1.0, score))


def calculate_priority_score(priority: str) -> float:
    """
    Calculate priority score based on priority level.

    Mapping:
    - CORE: 1.0 (highest priority)
    - HIGH: 0.75
    - NORMAL: 0.5 (default)
    - LOW: 0.25 (lowest priority)

    Args:
        priority: Priority level string (CORE, HIGH, NORMAL, LOW)

    Returns:
        Priority score between 0.0 and 1.0

    Examples:
        >>> calculate_priority_score("CORE")
        1.0
        >>> calculate_priority_score("HIGH")
        0.75
        >>> calculate_priority_score("NORMAL")
        0.5
        >>> calculate_priority_score("LOW")
        0.25
        >>> calculate_priority_score("INVALID")  # Unknown priority
        0.5
    """
    priority_map = {
        "CORE": 1.0,
        "HIGH": 0.75,
        "NORMAL": 0.5,
        "LOW": 0.25,
    }

    priority_upper = priority.upper() if priority else "NORMAL"
    score = priority_map.get(priority_upper, 0.5)  # Default to NORMAL for unknown

    if priority_upper not in priority_map:
        logger.debug(f"Unknown priority '{priority}', defaulting to 0.5")

    return score


def calculate_usage_score(access_count: int) -> float:
    """
    Calculate usage score using logarithmic scaling.

    Formula: log(access_count + 1) / log(100)
    - 0 accesses: score = 0.0
    - 1 access: score ≈ 0.02
    - 10 accesses: score ≈ 0.52
    - 100 accesses: score = 1.0
    - 1000 accesses: score ≈ 1.15 (clamped to 1.0)

    This provides diminishing returns for very high access counts,
    preventing frequently-accessed but irrelevant memories from
    dominating results.

    Args:
        access_count: Number of times memory has been accessed

    Returns:
        Usage score between 0.0 and 1.0 (higher = more frequently used)

    Examples:
        >>> calculate_usage_score(0)
        0.0
        >>> calculate_usage_score(1)
        0.02...
        >>> calculate_usage_score(100)
        1.0
        >>> calculate_usage_score(1000)  # Clamped to 1.0
        1.0
    """
    if access_count < 0:
        logger.warning(f"Negative access_count: {access_count}, using 0")
        access_count = 0

    if access_count == 0:
        return 0.0

    # Log-scaled: log(access_count + 1) / log(100)
    score = math.log(access_count + 1) / math.log(100.0)

    # Clamp to [0, 1] range
    return max(0.0, min(1.0, score))


def calculate_composite_score(
    similarity: float,
    created_at: datetime | str,
    priority: str,
    access_count: int,
    weights: Optional[ScoringWeights] = None,
) -> float:
    """
    Calculate composite score combining all factors.

    Formula:
        score = (
            weights.similarity * similarity +
            weights.recency * recency_score +
            weights.priority * priority_score +
            weights.usage * usage_score
        )

    Default weights (from settings):
    - 40% similarity (vector similarity)
    - 20% recency (how recent the memory is)
    - 20% priority (CORE/HIGH/NORMAL/LOW)
    - 20% usage (how often it's been accessed)

    Args:
        similarity: Vector similarity score (0.0-1.0)
        created_at: Creation timestamp
        priority: Priority level string
        access_count: Number of accesses
        weights: Optional scoring weights (defaults to settings)

    Returns:
        Composite score between 0.0 and 1.0 (higher = better match)

    Examples:
        >>> from datetime import datetime, timezone
        >>> now = datetime.now(timezone.utc)
        >>> calculate_composite_score(0.9, now, "HIGH", 10)
        0.7...  # High similarity + recent + high priority + some usage
    """
    if weights is None:
        weights = get_settings().retrieval.scoring_weights

    # Calculate individual scores
    recency = calculate_recency_score(created_at)
    priority_score = calculate_priority_score(priority)
    usage = calculate_usage_score(access_count)

    # Clamp similarity to [0, 1]
    similarity = max(0.0, min(1.0, similarity))

    # Weighted combination
    composite = (
        weights.similarity * similarity
        + weights.recency * recency
        + weights.priority * priority_score
        + weights.usage * usage
    )

    # Clamp to [0, 1] range
    return max(0.0, min(1.0, composite))


def score_memories(
    memories: list[dict[str, Any]],
    similarity_scores: dict[int, float],
    weights: Optional[ScoringWeights] = None,
) -> list[dict[str, Any]]:
    """
    Score and sort a list of memories with similarity scores.

    This function:
    1. Calculates composite scores for each memory
    2. Adds score breakdown to each memory dict
    3. Sorts memories by composite score (descending)
    4. Returns sorted list with score metadata

    Args:
        memories: List of memory dictionaries (must include id, created_at, priority, access_count)
        similarity_scores: Dict mapping memory_id -> similarity score
        weights: Optional scoring weights (defaults to settings)

    Returns:
        Sorted list of memories with added score fields:
        - score: Composite score (0.0-1.0)
        - score_breakdown: Dict with individual scores (similarity, recency, priority, usage)

    Examples:
        >>> memories = [
        ...     {"id": 1, "created_at": datetime.now(), "priority": "HIGH", "access_count": 5},
        ...     {"id": 2, "created_at": datetime.now(), "priority": "NORMAL", "access_count": 0},
        ... ]
        >>> similarities = {1: 0.9, 2: 0.8}
        >>> scored = score_memories(memories, similarities)
        >>> scored[0]["id"]  # Highest score first
        1
        >>> "score" in scored[0]
        True
    """
    if weights is None:
        weights = get_settings().retrieval.scoring_weights

    scored_memories = []

    for memory in memories:
        memory_id = memory.get("id")
        if memory_id is None:
            logger.warning(f"Memory missing id field, skipping: {memory}")
            continue

        similarity = similarity_scores.get(memory_id, 0.0)

        # Extract required fields
        created_at = memory.get("created_at")
        priority = memory.get("priority", "NORMAL")
        access_count = memory.get("access_count", 0)

        if created_at is None:
            logger.warning(f"Memory {memory_id} missing created_at, using current time")
            created_at = datetime.now(timezone.utc)

        # Calculate individual scores
        recency = calculate_recency_score(created_at)
        priority_score = calculate_priority_score(priority)
        usage = calculate_usage_score(access_count)

        # Calculate composite score
        composite = calculate_composite_score(
            similarity, created_at, priority, access_count, weights
        )

        # Add score information to memory dict
        memory_with_score = memory.copy()
        memory_with_score["score"] = composite
        memory_with_score["score_breakdown"] = {
            "similarity": similarity,
            "recency": recency,
            "priority": priority_score,
            "usage": usage,
        }

        scored_memories.append(memory_with_score)

    # Sort by composite score (descending)
    scored_memories.sort(key=lambda m: m["score"], reverse=True)

    logger.debug(f"Scored {len(scored_memories)} memories")
    return scored_memories

"""
Unit tests for scoring algorithms.

Tests all scoring functions including recency, priority, usage, and composite scoring.
"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from memory_server.config import ScoringWeights
from memory_server.utils.scoring import (
    calculate_composite_score,
    calculate_priority_score,
    calculate_recency_score,
    calculate_usage_score,
    score_memories,
)

pytestmark = pytest.mark.unit


class TestRecencyScore:
    """Tests for calculate_recency_score function."""

    def test_recent_memory(self):
        """Test that very recent memories get high scores."""
        now = datetime.now(timezone.utc)
        score = calculate_recency_score(now)
        assert score > 0.9  # Should be very close to 1.0

    def test_30_days_old(self):
        """Test that 30-day-old memories get ~0.368 score (1/e)."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        score = calculate_recency_score(thirty_days_ago)
        # Should be approximately 1/e ≈ 0.368
        assert abs(score - math.exp(-1)) < 0.01

    def test_60_days_old(self):
        """Test that 60-day-old memories get ~0.135 score (1/e²)."""
        now = datetime.now(timezone.utc)
        sixty_days_ago = now - timedelta(days=60)
        score = calculate_recency_score(sixty_days_ago)
        # Should be approximately 1/e² ≈ 0.135
        assert abs(score - math.exp(-2)) < 0.01

    def test_very_old_memory(self):
        """Test that very old memories get low scores."""
        now = datetime.now(timezone.utc)
        one_year_ago = now - timedelta(days=365)
        score = calculate_recency_score(one_year_ago)
        assert score < 0.01  # Should be very small

    def test_string_iso_format(self):
        """Test parsing ISO format datetime strings."""
        now = datetime.now(timezone.utc)
        iso_string = now.isoformat()
        score = calculate_recency_score(iso_string)
        assert score > 0.9

    def test_string_iso_with_z(self):
        """Test parsing ISO format with Z timezone."""
        now = datetime.now(timezone.utc)
        iso_string = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        score = calculate_recency_score(iso_string)
        assert score > 0.9

    def test_future_date(self):
        """Test that future dates are clamped to 1.0."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=1)
        score = calculate_recency_score(future)
        assert score == 1.0

    def test_naive_datetime(self):
        """Test that naive datetimes are handled (assumed UTC)."""
        now = datetime.now()  # Naive datetime
        score = calculate_recency_score(now)
        assert 0.0 <= score <= 1.0

    def test_invalid_string(self):
        """Test that invalid date strings return 0.0."""
        score = calculate_recency_score("invalid-date")
        assert score == 0.0


class TestPriorityScore:
    """Tests for calculate_priority_score function."""

    @pytest.mark.parametrize(
        "priority,expected",
        [
            ("CORE", 1.0),
            ("HIGH", 0.75),
            ("NORMAL", 0.5),
            ("LOW", 0.25),
            ("core", 1.0),  # Case insensitive
            ("high", 0.75),
            ("normal", 0.5),
            ("low", 0.25),
        ],
    )
    def test_priority_mapping(self, priority, expected):
        """Test that priority levels map to correct scores."""
        score = calculate_priority_score(priority)
        assert score == expected

    def test_unknown_priority(self):
        """Test that unknown priority defaults to NORMAL (0.5)."""
        score = calculate_priority_score("UNKNOWN")
        assert score == 0.5

    def test_none_priority(self):
        """Test that None priority defaults to NORMAL."""
        score = calculate_priority_score(None)
        assert score == 0.5

    def test_empty_priority(self):
        """Test that empty priority defaults to NORMAL."""
        score = calculate_priority_score("")
        assert score == 0.5


class TestUsageScore:
    """Tests for calculate_usage_score function."""

    def test_zero_accesses(self):
        """Test that zero accesses returns 0.0."""
        score = calculate_usage_score(0)
        assert score == 0.0

    def test_one_access(self):
        """Test that one access returns small positive score."""
        score = calculate_usage_score(1)
        # Should be approximately log(2) / log(100) ≈ 0.15
        expected = math.log(2) / math.log(100)
        assert abs(score - expected) < 0.01
        assert 0.0 < score < 0.2  # Should be small but positive

    def test_ten_accesses(self):
        """Test that 10 accesses returns moderate score."""
        score = calculate_usage_score(10)
        # Should be approximately log(11) / log(100) ≈ 0.52
        expected = math.log(11) / math.log(100)
        assert abs(score - expected) < 0.01

    def test_hundred_accesses(self):
        """Test that 100 accesses returns 1.0."""
        score = calculate_usage_score(100)
        assert abs(score - 1.0) < 0.01

    def test_many_accesses(self):
        """Test that many accesses are clamped to 1.0."""
        score = calculate_usage_score(1000)
        assert score == 1.0

    def test_negative_accesses(self):
        """Test that negative accesses are handled (treated as 0)."""
        score = calculate_usage_score(-1)
        assert score == 0.0


class TestCompositeScore:
    """Tests for calculate_composite_score function."""

    def test_default_weights(self):
        """Test composite score with default weights."""
        now = datetime.now(timezone.utc)
        score = calculate_composite_score(
            similarity=0.9,
            created_at=now,
            priority="HIGH",
            access_count=10,
        )
        # Should be weighted combination
        assert 0.0 <= score <= 1.0
        assert score > 0.7  # High similarity + recent + high priority

    def test_custom_weights(self):
        """Test composite score with custom weights."""
        weights = ScoringWeights(
            similarity=0.5,
            recency=0.3,
            priority=0.1,
            usage=0.1,
        )
        now = datetime.now(timezone.utc)
        score = calculate_composite_score(
            similarity=0.8,
            created_at=now,
            priority="NORMAL",
            access_count=5,
            weights=weights,
        )
        assert 0.0 <= score <= 1.0

    def test_all_factors_high(self):
        """Test composite score when all factors are high."""
        now = datetime.now(timezone.utc)
        score = calculate_composite_score(
            similarity=1.0,
            created_at=now,
            priority="CORE",
            access_count=100,
        )
        assert score > 0.9  # Should be very high

    def test_all_factors_low(self):
        """Test composite score when all factors are low."""
        old_date = datetime.now(timezone.utc) - timedelta(days=365)
        score = calculate_composite_score(
            similarity=0.1,
            created_at=old_date,
            priority="LOW",
            access_count=0,
        )
        assert score < 0.3  # Should be low

    def test_similarity_clamping(self):
        """Test that similarity values outside [0,1] are clamped."""
        now = datetime.now(timezone.utc)
        score_high = calculate_composite_score(
            similarity=1.5,  # Above 1.0
            created_at=now,
            priority="NORMAL",
            access_count=0,
        )
        score_low = calculate_composite_score(
            similarity=-0.5,  # Below 0.0
            created_at=now,
            priority="NORMAL",
            access_count=0,
        )
        assert 0.0 <= score_high <= 1.0
        assert 0.0 <= score_low <= 1.0

    def test_weights_sum_validation(self):
        """Test that weights don't need to sum to 1.0 (they're used as-is)."""
        weights = ScoringWeights(
            similarity=0.8,  # High weight
            recency=0.1,
            priority=0.05,
            usage=0.05,
        )
        now = datetime.now(timezone.utc)
        score = calculate_composite_score(
            similarity=0.9,
            created_at=now,
            priority="HIGH",
            access_count=10,
            weights=weights,
        )
        assert 0.0 <= score <= 1.0


class TestScoreMemories:
    """Tests for score_memories function."""

    def test_score_and_sort(self):
        """Test that memories are scored and sorted correctly."""
        now = datetime.now(timezone.utc)
        memories = [
            {
                "id": 1,
                "content": "Memory 1",
                "created_at": now,
                "priority": "HIGH",
                "access_count": 10,
            },
            {
                "id": 2,
                "content": "Memory 2",
                "created_at": now,
                "priority": "NORMAL",
                "access_count": 0,
            },
            {
                "id": 3,
                "content": "Memory 3",
                "created_at": now,
                "priority": "CORE",
                "access_count": 5,
            },
        ]
        similarity_scores = {1: 0.9, 2: 0.8, 3: 0.85}

        scored = score_memories(memories, similarity_scores)

        # Should be sorted by score (descending)
        assert len(scored) == 3
        assert scored[0]["score"] >= scored[1]["score"]
        assert scored[1]["score"] >= scored[2]["score"]

        # Check that score fields are added
        for memory in scored:
            assert "score" in memory
            assert "score_breakdown" in memory
            assert "similarity" in memory["score_breakdown"]
            assert "recency" in memory["score_breakdown"]
            assert "priority" in memory["score_breakdown"]
            assert "usage" in memory["score_breakdown"]

    def test_missing_similarity_score(self):
        """Test that memories without similarity scores get 0.0 similarity."""
        now = datetime.now(timezone.utc)
        memories = [
            {
                "id": 1,
                "content": "Memory 1",
                "created_at": now,
                "priority": "NORMAL",
                "access_count": 0,
            },
        ]
        similarity_scores = {}  # No similarity for memory 1

        scored = score_memories(memories, similarity_scores)

        assert len(scored) == 1
        assert scored[0]["score_breakdown"]["similarity"] == 0.0

    def test_missing_created_at(self):
        """Test that memories without created_at use current time."""
        memories = [
            {
                "id": 1,
                "content": "Memory 1",
                "priority": "NORMAL",
                "access_count": 0,
            },
        ]
        similarity_scores = {1: 0.8}

        scored = score_memories(memories, similarity_scores)

        assert len(scored) == 1
        assert "created_at" in scored[0] or scored[0]["score"] > 0

    def test_missing_id(self):
        """Test that memories without id are skipped."""
        now = datetime.now(timezone.utc)
        memories = [
            {
                "content": "Memory without ID",
                "created_at": now,
                "priority": "NORMAL",
                "access_count": 0,
            },
            {
                "id": 2,
                "content": "Memory with ID",
                "created_at": now,
                "priority": "NORMAL",
                "access_count": 0,
            },
        ]
        similarity_scores = {2: 0.8}

        scored = score_memories(memories, similarity_scores)

        # Should only have memory with ID
        assert len(scored) == 1
        assert scored[0]["id"] == 2

    def test_custom_weights(self):
        """Test scoring with custom weights."""
        now = datetime.now(timezone.utc)
        memories = [
            {
                "id": 1,
                "content": "Memory 1",
                "created_at": now,
                "priority": "NORMAL",
                "access_count": 0,
            },
        ]
        similarity_scores = {1: 0.9}
        weights = ScoringWeights(
            similarity=0.8,
            recency=0.1,
            priority=0.05,
            usage=0.05,
        )

        scored = score_memories(memories, similarity_scores, weights)

        assert len(scored) == 1
        assert "score" in scored[0]

    def test_empty_memories_list(self):
        """Test that empty memories list returns empty list."""
        scored = score_memories([], {})
        assert scored == []

    def test_default_priority_and_access_count(self):
        """Test that missing priority and access_count use defaults."""
        now = datetime.now(timezone.utc)
        memories = [
            {
                "id": 1,
                "content": "Memory 1",
                "created_at": now,
                # Missing priority and access_count
            },
        ]
        similarity_scores = {1: 0.8}

        scored = score_memories(memories, similarity_scores)

        assert len(scored) == 1
        # Should use defaults: NORMAL priority (0.5), 0 access_count (0.0 usage)
        assert scored[0]["score_breakdown"]["priority"] == 0.5
        assert scored[0]["score_breakdown"]["usage"] == 0.0

"""
Search memory MCP tool.

Provides the search_memory tool for semantic search across stored memories.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from memory_server.utils import get_logger

logger = get_logger(__name__)


class SearchFilters(BaseModel):
    """Filters for memory search."""

    tags: Optional[list[str]] = Field(
        default=None,
        description="Filter by tags. Returns memories that have any of these tags.",
    )
    priority: Optional[str] = Field(
        default=None,
        description="Filter by priority level (CORE, HIGH, NORMAL, LOW)",
    )
    date_range: Optional[dict[str, str]] = Field(
        default=None,
        description="Filter by date range. Format: {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}",
    )


class SearchMemoryInput(BaseModel):
    """Input schema for search_memory tool."""

    query: str = Field(
        ...,
        description="Search query. This will be converted to an embedding for semantic search.",
        min_length=1,
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return (1-100, default: 10)",
    )
    filters: Optional[SearchFilters] = Field(
        default=None,
        description="Optional filters to apply to search results",
    )


def create_search_memory_tool(memory_service):
    """
    Create the search_memory tool function.

    Args:
        memory_service: MemoryService instance

    Returns:
        Tool function that can be registered with FastMCP
    """

    async def search_memory(input: SearchMemoryInput) -> dict:
        """
        Search memories using semantic similarity.

        This tool performs semantic search by:
        1. Generating an embedding for the query
        2. Finding similar memories using vector search
        3. Applying multi-factor scoring (similarity, recency, priority, usage)
        4. Applying optional filters
        5. Returning top results with score breakdowns

        Args:
            input: SearchMemoryInput with query and optional filters

        Returns:
            Dictionary with:
            - memories: List of scored memories
            - total: Number of results returned
            - limit: Requested limit
            - message: Human-readable summary
        """
        try:
            # Validate query
            if not input.query or not input.query.strip():
                return {
                    "success": False,
                    "error": "Query cannot be empty",
                }

            # Convert filters to dict format
            filters = None
            if input.filters:
                filters = {}
                if input.filters.tags:
                    filters["tags"] = input.filters.tags
                if input.filters.priority:
                    filters["priority"] = input.filters.priority
                if input.filters.date_range:
                    filters["date_range"] = input.filters.date_range

            # Search memories
            result = memory_service.search_memory(
                query=input.query,
                limit=input.limit,
                filters=filters,
            )

            # Format response
            memories = result["memories"]
            total = result["total"]

            if total == 0:
                message = f"No memories found matching query: '{input.query}'"
            else:
                message = f"Found {total} memory{'ies' if total != 1 else ''} matching query: '{input.query}'"

            return {
                "success": True,
                "memories": memories,
                "total": total,
                "limit": result["limit"],
                "message": message,
            }

        except ValueError as e:
            logger.error(f"Validation error in search_memory: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Error searching memories: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to search memories: {str(e)}",
            }

    return search_memory

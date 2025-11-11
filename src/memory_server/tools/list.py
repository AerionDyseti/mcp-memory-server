"""
List memories MCP tool.

Provides the list_memories tool for listing and filtering memories.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from memory_server.utils import get_logger

logger = get_logger(__name__)


class ListFilters(BaseModel):
    """Filters for listing memories."""

    tags: Optional[list[str]] = Field(
        default=None,
        description="Filter by tags. Returns memories that have any of these tags.",
    )
    priority: Optional[str] = Field(
        default=None,
        description="Filter by priority level (CORE, HIGH, NORMAL, LOW)",
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Filter by project ID",
    )
    date_range: Optional[dict[str, str]] = Field(
        default=None,
        description="Filter by date range. Format: {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}",
    )


class ListMemoriesInput(BaseModel):
    """Input schema for list_memories tool."""

    filters: Optional[ListFilters] = Field(
        default=None,
        description="Optional filters to apply",
    )
    sort_by: str = Field(
        default="created_at",
        description="Column to sort by (created_at, priority, access_count, etc.)",
    )
    sort_order: Literal["ASC", "DESC"] = Field(
        default="DESC",
        description="Sort order: ASC (ascending) or DESC (descending, default)",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of results to return (1-500, default: 50)",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip for pagination (default: 0)",
    )


def create_list_memories_tool(memory_service):
    """
    Create the list_memories tool function.

    Args:
        memory_service: MemoryService instance

    Returns:
        Tool function that can be registered with FastMCP
    """

    async def list_memories(input: ListMemoriesInput) -> dict:
        """
        List memories with filtering and pagination.

        This tool lists memories from the database with optional filtering,
        sorting, and pagination. Unlike search_memory, this does not use
        semantic search - it queries the database directly.

        Args:
            input: ListMemoriesInput with filters, sorting, and pagination options

        Returns:
            Dictionary with:
            - memories: List of memories
            - total: Number of results returned
            - limit: Requested limit
            - offset: Requested offset
            - has_more: True if more results are available
            - message: Human-readable summary
        """
        try:
            # Convert filters to dict format
            filters = None
            if input.filters:
                filters = {}
                if input.filters.tags:
                    filters["tags"] = input.filters.tags
                if input.filters.priority:
                    filters["priority"] = input.filters.priority
                if input.filters.project_id:
                    filters["project_id"] = input.filters.project_id
                if input.filters.date_range:
                    filters["date_range"] = input.filters.date_range

            # List memories
            result = memory_service.list_memories(
                filters=filters,
                sort_by=input.sort_by,
                sort_order=input.sort_order,
                limit=input.limit,
                offset=input.offset,
            )

            # Format response
            total = result["total"]
            has_more = result["has_more"]

            if total == 0:
                message = "No memories found matching the specified filters"
            else:
                message = f"Found {total} memory{'ies' if total != 1 else ''}"
                if has_more:
                    message += f" (showing {input.limit} of {total + input.offset}+ total)"
                if input.offset > 0:
                    message += f" (offset: {input.offset})"

            return {
                "success": True,
                "memories": result["memories"],
                "total": total,
                "limit": result["limit"],
                "offset": result["offset"],
                "has_more": has_more,
                "message": message,
            }

        except Exception as e:
            logger.error(f"Error listing memories: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to list memories: {str(e)}",
            }

    return list_memories

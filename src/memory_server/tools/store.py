"""
Store memory MCP tool.

Provides the store_memory tool for storing new memories with semantic embeddings.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from memory_server.database.schema import Priority, get_valid_priorities
from memory_server.utils import get_logger

logger = get_logger(__name__)


class StoreMemoryInput(BaseModel):
    """Input schema for store_memory tool."""

    content: str = Field(
        ...,
        description="The memory content to store. This is the main text that will be embedded and stored.",
        min_length=1,
    )
    tags: Optional[list[str]] = Field(
        default=None,
        description="Optional list of tags to categorize the memory (e.g., ['architecture', 'database'])",
    )
    priority: Literal["CORE", "HIGH", "NORMAL", "LOW"] = Field(
        default="NORMAL",
        description="Priority level: CORE (highest), HIGH, NORMAL (default), or LOW",
    )
    category: Optional[str] = Field(
        default=None,
        description="Optional category for the memory (e.g., 'architecture', 'bug-fix', 'code-pattern')",
    )
    source: Optional[str] = Field(
        default=None,
        description="Optional source identifier (e.g., 'manual', 'auto_decision', 'session_end')",
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Optional project identifier for project-specific memories",
    )


def create_store_memory_tool(memory_service):
    """
    Create the store_memory tool function.

    Args:
        memory_service: MemoryService instance

    Returns:
        Tool function that can be registered with FastMCP
    """

    async def store_memory(input: StoreMemoryInput) -> dict:
        """
        Store a new memory with semantic embedding.

        This tool stores a memory by:
        1. Generating a content hash for duplicate detection
        2. Checking for exact duplicates (same content)
        3. Generating an embedding (using cache if available)
        4. Checking for near-duplicates (similar content)
        5. Storing in the database

        Args:
            input: StoreMemoryInput with content and optional metadata

        Returns:
            Dictionary with:
            - memory_id: ID of stored memory
            - duplicate: True if exact duplicate was found
            - near_duplicate: Optional info about similar memory if found
            - success: True if stored successfully
            - message: Human-readable status message
        """
        try:
            # Validate content
            if not input.content or not input.content.strip():
                return {
                    "success": False,
                    "error": "Content cannot be empty",
                }

            # Validate priority
            if input.priority not in get_valid_priorities():
                return {
                    "success": False,
                    "error": f"Invalid priority. Must be one of: {', '.join(get_valid_priorities())}",
                }

            # Store memory
            result = memory_service.store_memory(
                content=input.content,
                tags=input.tags,
                priority=input.priority,
                category=input.category,
                source=input.source,
                project_id=input.project_id,
            )

            # Format response message
            if result["duplicate"]:
                message = f"Exact duplicate found. Using existing memory ID: {result['memory_id']}"
            elif result.get("near_duplicate"):
                near_dup = result["near_duplicate"]
                message = (
                    f"Memory stored with ID: {result['memory_id']}. "
                    f"Near-duplicate detected (similarity: {near_dup['similarity']:.2f}, "
                    f"memory_id: {near_dup['memory_id']}). {near_dup['suggestion']}"
                )
            else:
                message = f"Memory stored successfully with ID: {result['memory_id']}"

            return {
                "success": result["success"],
                "memory_id": result["memory_id"],
                "duplicate": result["duplicate"],
                "near_duplicate": result.get("near_duplicate"),
                "message": message,
            }

        except ValueError as e:
            logger.error(f"Validation error in store_memory: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Error storing memory: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to store memory: {str(e)}",
            }

    return store_memory

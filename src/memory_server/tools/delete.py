"""
Delete memory MCP tool.

Provides the delete_memory tool for removing memories by ID or content hash.
"""

from typing import Optional

from pydantic import BaseModel, Field

from memory_server.utils import get_logger

logger = get_logger(__name__)


class DeleteMemoryInput(BaseModel):
    """Input schema for delete_memory tool."""

    memory_id: Optional[int] = Field(
        default=None,
        description="Memory ID to delete",
        ge=1,
    )
    content_hash: Optional[str] = Field(
        default=None,
        description="Content hash to delete (alternative to memory_id)",
        min_length=64,
        max_length=64,
    )

    def model_post_init(self, __context):
        """Validate that at least one of memory_id or content_hash is provided."""
        if not self.memory_id and not self.content_hash:
            raise ValueError("Either memory_id or content_hash must be provided")


def create_delete_memory_tool(memory_service):
    """
    Create the delete_memory tool function.

    Args:
        memory_service: MemoryService instance

    Returns:
        Tool function that can be registered with FastMCP
    """

    async def delete_memory(input: DeleteMemoryInput) -> dict:
        """
        Delete a memory by ID or content hash.

        This tool deletes a memory from the database. You can specify
        either the memory_id or the content_hash to identify the memory
        to delete.

        Args:
            input: DeleteMemoryInput with memory_id or content_hash

        Returns:
            Dictionary with:
            - success: True if deleted successfully
            - memory_id: ID of deleted memory (if found)
            - message: Human-readable status message
        """
        try:
            # Validate that at least one identifier is provided
            if not input.memory_id and not input.content_hash:
                return {
                    "success": False,
                    "error": "Either memory_id or content_hash must be provided",
                }

            # Delete memory
            result = memory_service.delete_memory(
                memory_id=input.memory_id,
                content_hash=input.content_hash,
            )

            # Format response
            if result["success"]:
                message = f"Memory {result['memory_id']} deleted successfully"
            else:
                identifier = input.memory_id or input.content_hash[:8] + "..."
                message = f"Memory not found: {identifier}"

            return {
                "success": result["success"],
                "memory_id": result.get("memory_id"),
                "message": message,
            }

        except ValueError as e:
            logger.error(f"Validation error in delete_memory: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Error deleting memory: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to delete memory: {str(e)}",
            }

    return delete_memory

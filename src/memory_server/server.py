"""
MCP Server implementation for memory storage.

Provides MCP tools for semantic memory storage and retrieval.
"""

from fastmcp import FastMCP

from memory_server.config import get_settings
from memory_server.service import MemoryService
from memory_server.tools.delete import create_delete_memory_tool
from memory_server.tools.list import create_list_memories_tool
from memory_server.tools.search import create_search_memory_tool
from memory_server.tools.store import create_store_memory_tool
from memory_server.utils import get_logger

logger = get_logger(__name__)

# Global memory service instance (initialized on server startup)
_memory_service: MemoryService | None = None


def get_memory_service() -> MemoryService:
    """
    Get or create the global memory service instance.

    Returns:
        MemoryService instance
    """
    global _memory_service
    if _memory_service is None:
        logger.info("Initializing MemoryService...")
        _memory_service = MemoryService()
        logger.info("MemoryService initialized")
    return _memory_service


def create_server() -> FastMCP:
    """
    Create and configure the FastMCP server instance.

    Returns:
        Configured FastMCP server
    """
    settings = get_settings()
    logger.info(f"Creating memory server with log level: {settings.log_level}")

    mcp = FastMCP(
        name="memory-server",
        instructions="Semantic memory storage using sqlite-vec and local embeddings",
    )

    # Initialize memory service
    memory_service = get_memory_service()

    # Health check tool
    @mcp.tool
    def ping() -> str:
        """Health check endpoint."""
        return "pong"

    # Register memory management tools
    # Create tool functions and register them with FastMCP
    store_tool_func = create_store_memory_tool(memory_service)
    search_tool_func = create_search_memory_tool(memory_service)
    list_tool_func = create_list_memories_tool(memory_service)
    delete_tool_func = create_delete_memory_tool(memory_service)

    # Register tools using the decorator pattern
    mcp.tool(name="store_memory")(store_tool_func)
    mcp.tool(name="search_memory")(search_tool_func)
    mcp.tool(name="list_memories")(list_tool_func)
    mcp.tool(name="delete_memory")(delete_tool_func)

    logger.info("Memory server created successfully with 5 tools (ping, store, search, list, delete)")
    return mcp


def run_server():
    """Run the memory server with stdio transport."""
    logger.info("Starting memory server...")
    mcp = create_server()

    try:
        # Run with default stdio transport for Claude Code integration
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise

"""
Memory Server - MCP server for semantic memory storage.

An MCP (Model Context Protocol) server that provides semantic memory storage
using sqlite-vec and local embeddings for privacy and performance.
"""

__version__ = "0.1.0"

from memory_server.server import create_server


def main():
    """Main entry point for the memory server CLI."""
    from memory_server.server import run_server

    run_server()


__all__ = ["create_server", "main", "__version__"]

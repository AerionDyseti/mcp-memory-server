# mcp-memory — MVP Specification

## Overview

A simple, zero-configuration RAG memory server for MCP clients (like Claude Code). It gives AI the ability to recall previous information without having to hold all of that information in context.

## Design Philosophy

**Config Optional**: Sensible defaults, everything works out of the box. Configuration is available for those who want it, but never required.

## Deployment

- **Single command startup**: `uvx mcp-memory`
- **No repo clone required** — published as a Python package
- **Local SQLite file** — default location works automatically, configurable via environment variable if desired

## Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python | ML ecosystem, Claude Code proficiency |
| MCP SDK | `mcp` | Official Anthropic SDK |
| Embeddings | MiniLM-v6 (`all-MiniLM-L6-v2`) | Small, fast, runs on CPU, proven reliable |
| Vector Storage | sqlite-vec | Single file, no external dependencies |

## Data Model

### Memory
```python
@dataclass
class Memory:
    id: str                     # Unique identifier (UUID)
    content: str                # The text content of the memory
    embedding: list[float]      # Vector embedding (384 dimensions for MiniLM-v6)
    metadata: dict              # Flexible key-value metadata
    created_at: datetime        # When the memory was created
    updated_at: datetime        # When the memory was last modified
    superseded_by: str | None   # ID of the memory that replaces this one (soft-delete/update chain)
```

### Schema Notes

- **Soft deletes only**: Memories are never truly deleted. A deleted memory has `superseded_by` set to a tombstone value (e.g., `"DELETED"`).
- **Supersession chains**: When a memory is updated, a new memory is created and the old memory's `superseded_by` points to the new one. This preserves the original embedding for retrieval while returning current content.
- **Metadata flexibility**: Start with a flexible `metadata` dict. If patterns emerge (e.g., `project` appearing on every memory), promote them to first-class fields later.

## MCP Tools

Four tools total:

### 1. `store_memory`

Create a new memory.

**Parameters:**
- `content` (string, required): The text content to store
- `metadata` (object, optional): Key-value pairs for metadata

**Returns:**
- `id`: The ID of the created memory

**Behavior:**
- Generate UUID for the memory
- Embed the content using MiniLM-v6
- Store in SQLite with current timestamp
- `superseded_by` is null

---

### 2. `delete_memory`

Soft-delete a memory.

**Parameters:**
- `id` (string, required): The ID of the memory to delete

**Returns:**
- `success`: boolean

**Behavior:**
- Set `superseded_by` to `"DELETED"` (or similar tombstone value)
- Memory remains in database but won't appear in search results

---

### 3. `search_memories`

Semantic search for relevant memories.

**Parameters:**
- `query` (string, required): The search query
- `limit` (integer, optional, default 10): Maximum number of results to return

**Returns:**
- Array of memories, ranked by semantic similarity

**Behavior:**
- Embed the query using MiniLM-v6
- Search sqlite-vec for top-k similar embeddings
- Filter out memories where `superseded_by` is not null
- **Supersession chain handling**: If a superseded memory would have matched, follow the chain to the head and return the current version instead
- Return results ranked by similarity score

---

### 4. `get_memory`

Retrieve a specific memory by ID.

**Parameters:**
- `id` (string, required): The ID of the memory to retrieve

**Returns:**
- The memory object, or null if not found

**Behavior:**
- Direct lookup by ID
- If memory has `superseded_by` set, optionally follow chain to head (TBD: might want to return as-is with a flag indicating it's superseded)

---

## Retrieval Algorithm (MVP)

1. Embed query using MiniLM-v6
2. Vector similarity search in sqlite-vec
3. Rank by semantic similarity score only (no decay, no boosting)
4. Filter out superseded/deleted memories
5. For any superseded memory that would have matched, substitute the head of its chain
6. Return top-k results

Future enhancements (post-MVP):
- Time decay weighting
- Metadata filtering (e.g., "only memories from project X")
- Recency boosting

## Supersession Chain Logic

When updating a memory:
```
Original Memory A (content: "foo")
    ↓ update
Memory A.superseded_by = B.id
Memory B (content: "bar") ← new memory created
    ↓ update  
Memory B.superseded_by = C.id
Memory C (content: "baz") ← head of chain
```

**Traversal**: Always follow `superseded_by` pointers until you reach a memory where `superseded_by` is null. That's the head.

**Why this matters**: The embedding for "foo" still exists and is searchable. If someone searches for something similar to "foo", they'll find it—but get back "baz" (the current truth).

## Project Structure
```
mcp-memory/
├── pyproject.toml          # Package config, dependencies, uvx entry point
├── README.md               # User-facing documentation
├── src/
│   └── mcp_memory/
│       ├── __init__.py
│       ├── server.py       # MCP server setup and tool definitions
│       ├── memory.py       # Memory dataclass and business logic
│       ├── store.py        # SQLite/sqlite-vec storage layer
│       └── embeddings.py   # MiniLM-v6 embedding wrapper
└── tests/
    └── ...
```

## Configuration

All configuration via environment variables, all optional:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_MEMORY_DB_PATH` | `~/.local/share/mcp-memory/memories.db` | Path to SQLite database file |
| `MCP_MEMORY_MODEL` | `all-MiniLM-L6-v2` | Embedding model (future: allow swapping) |

## Dependencies
```toml
[project]
dependencies = [
    "mcp",                    # MCP SDK
    "sentence-transformers",  # For MiniLM-v6 embeddings
    "sqlite-vec",             # Vector search in SQLite
]
```

## Stretch Goals (Cut First If Needed)

1. **CLI for debugging**: `mcp-memory list`, `mcp-memory search "query"`, `mcp-memory get <id>`
2. **Web UI**: Simple browser interface for browsing and searching memories

## Out of Scope for MVP

- Working memory / session state (belongs in client)
- Memory consolidation / clustering
- Multiple embedding model support
- Non-SQLite backends
- Authentication / multi-user

## Success Criteria

MVP is complete when:

1. `uvx mcp-memory` starts the server with zero configuration
2. All four MCP tools work correctly
3. Semantic search returns relevant results
4. Supersession chains work (update a memory, search for old content, get new content)
5. Soft deletes work (deleted memories don't appear in search)

## Open Questions (Decide During Implementation)

1. **get_memory on superseded memory**: Return as-is with a flag, or auto-follow to head?
2. **Tombstone value**: Use `"DELETED"` string, or a special UUID, or a boolean `is_deleted` field?
3. **Default DB location**: `~/.local/share/mcp-memory/` or somewhere else?

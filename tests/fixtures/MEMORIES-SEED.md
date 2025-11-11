# Test Memories for Seeding

This file contains realistic test memories in markdown format for seeding test databases.

---

## Architectural Decision: Use FastAPI for REST API

**Tags:** architecture, api, framework, fastapi
**Priority:** HIGH
**Category:** architecture
**Content:**
Decided to use FastAPI instead of Flask because:
- Built-in async support
- Automatic OpenAPI documentation
- Pydantic validation
- Better performance for I/O-bound operations

---

## Architectural Decision: Use SQLite for Local Storage

**Tags:** architecture, database, sqlite
**Priority:** HIGH
**Category:** architecture
**Content:**
Chose SQLite over PostgreSQL for local-first applications because:
- Zero configuration
- Single file database
- Perfect for embedded use cases
- Excellent performance for read-heavy workloads

---

## Architectural Decision: Use sqlite-vec for Vector Search

**Tags:** architecture, database, vector-search, embeddings
**Priority:** CORE
**Category:** architecture
**Content:**
Selected sqlite-vec for vector similarity search because:
- Native SQLite extension (no external service)
- Fast KNN search performance
- Simple integration with existing SQLite databases
- Local-first approach aligns with privacy goals

---

## Architectural Decision: FastEmbed for Local Embeddings

**Tags:** architecture, embeddings, ml
**Priority:** HIGH
**Category:** architecture
**Content:**
Chose FastEmbed over cloud APIs because:
- No API costs
- Complete privacy (embeddings generated locally)
- FastEmbed supports MiniLM models
- CPU-optimized for local execution

---

## Architectural Decision: Pydantic for Validation

**Tags:** architecture, validation, python
**Priority:** NORMAL
**Category:** architecture
**Content:**
Use Pydantic for all input validation:
- Type safety with Python type hints
- Automatic JSON schema generation
- Clear error messages
- Integrates well with FastAPI

---

## Architectural Decision: MCP Protocol for Tool Interface

**Tags:** architecture, mcp, protocol
**Priority:** CORE
**Category:** architecture
**Content:**
Using Model Context Protocol (MCP) for tool interface:
- Standard protocol for AI assistants
- Works with Claude Code and other MCP clients
- FastMCP provides clean Python implementation
- Future-proof as protocol evolves

---

## Architectural Decision: Dual-Level Memory Storage

**Tags:** architecture, storage, project-management
**Priority:** HIGH
**Category:** architecture
**Content:**
Implement dual-level storage:
- Global memories in ~/.memory/db (cross-project knowledge)
- Project memories in .memory/db (project-specific)
- Project memories take precedence in search results
- Enables both personal and project-specific context

---

## Bug Fix: SQLite Database Lock

**Tags:** bug, database, fix, sqlite
**Priority:** NORMAL
**Category:** bug-fix
**Content:**
Issue: Getting "database is locked" errors in tests
Solution: Enable WAL mode with PRAGMA journal_mode=WAL
Also set busy_timeout=5000 for better concurrency
Error signature: sqlite3.OperationalError: database is locked

---

## Bug Fix: FastEmbed Model Download on First Run

**Tags:** bug, embeddings, fix
**Priority:** NORMAL
**Category:** bug-fix
**Content:**
Issue: First embedding generation takes long time
Solution: Model downloads automatically on first use (~100MB)
Handle gracefully with progress indicator
Cache model files in user's home directory

---

## Bug Fix: sqlite-vec Extension Not Found

**Tags:** bug, database, fix, sqlite-vec
**Priority:** HIGH
**Category:** bug-fix
**Content:**
Issue: RuntimeError when sqlite-vec extension not installed
Solution: Check for extension in common locations
Provide clear error message with installation instructions
Graceful fallback if extension unavailable

---

## Bug Fix: Embedding Dimension Mismatch

**Tags:** bug, embeddings, fix, validation
**Priority:** NORMAL
**Category:** bug-fix
**Content:**
Issue: Embeddings with wrong dimension cause errors
Solution: Validate embedding dimension on insert
Return clear error if dimension doesn't match expected (384)
Check dimension matches model configuration

---

## Bug Fix: Empty Content in Memory Storage

**Tags:** bug, validation, fix
**Priority:** NORMAL
**Category:** bug-fix
**Content:**
Issue: Empty strings or whitespace-only content stored
Solution: Validate content is not empty before storage
Trim whitespace and check length > 0
Return clear validation error message

---

## Bug Fix: Thread Safety in EmbeddingCache

**Tags:** bug, cache, fix, threading
**Priority:** NORMAL
**Category:** bug-fix
**Content:**
Issue: Race conditions when multiple threads access cache
Solution: Use RLock for thread-safe operations
Protect all cache operations (get, set, clear)
Test with concurrent access patterns

---

## Code Pattern: Async Context Manager

**Tags:** pattern, python, async
**Priority:** NORMAL
**Category:** code-pattern
**Content:**
Standard pattern for resources with async cleanup:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def db_connection(path):
    conn = await connect(path)
    try:
        yield conn
    finally:
        await conn.close()
```

Use for any resource requiring cleanup in async code.

---

## Code Pattern: Pydantic Input Validation

**Tags:** pattern, validation, pydantic
**Priority:** NORMAL
**Category:** code-pattern
**Content:**
Use Pydantic models for all tool inputs:

```python
from pydantic import BaseModel, Field

class StoreMemoryInput(BaseModel):
    content: str = Field(..., min_length=1)
    priority: Literal["CORE", "HIGH", "NORMAL", "LOW"] = "NORMAL"
```

Provides automatic validation and clear error messages.

---

## Code Pattern: Multi-Factor Scoring

**Tags:** pattern, scoring, algorithm
**Priority:** NORMAL
**Category:** code-pattern
**Content:**
Combine multiple factors for ranking:

```python
score = (
    0.4 * similarity +
    0.2 * recency +
    0.2 * priority +
    0.2 * usage
)
```

Weights configurable via settings for tuning.

---

## Code Pattern: LRU Cache Implementation

**Tags:** pattern, cache, python
**Priority:** NORMAL
**Category:** code-pattern
**Content:**
Use OrderedDict for LRU cache:

```python
from collections import OrderedDict
from threading import RLock

class LRUCache:
    def __init__(self, max_size):
        self.cache = OrderedDict()
        self.lock = RLock()
```

Move accessed items to end, remove from front when full.

---

## Code Pattern: Error Handling with Logging

**Tags:** pattern, error-handling, logging
**Priority:** NORMAL
**Category:** code-pattern
**Content:**
Always log errors with context:

```python
try:
    result = operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise RuntimeError(f"User-friendly message: {e}") from e
```

Include exc_info=True for stack traces in logs.

---

## Configuration: Environment Variables

**Tags:** config, env, best-practice
**Priority:** NORMAL
**Category:** configuration
**Content:**
Best practice for configuration:
- Use .env files for local development
- Use environment variables in production
- Never commit .env to git
- Use python-dotenv for loading

Example:
DATABASE_URL=sqlite:///./test.db
MEMORY_DB_PATH=~/.memory/db
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

---

## Configuration: Logging Setup

**Tags:** config, logging, best-practice
**Priority:** NORMAL
**Category:** configuration
**Content:**
Configure logging with file and console handlers:
- Console: INFO level for user visibility
- File: DEBUG level for troubleshooting
- Rotate log files to prevent disk fill
- Use structured format with timestamps

Log directory: ~/.memory/logs/

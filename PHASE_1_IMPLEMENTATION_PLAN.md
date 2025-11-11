# Phase 1 Implementation Plan: Global Memory System

## Overview
Implement a working MCP memory server with global storage, semantic search, and 4 core tools (store, search, list, delete).

---

## Implementation Order (by dependency)

### Stage 1: Database Layer (Foundation)
**Priority: CRITICAL - Everything depends on this**

#### 1.1 Create `src/memory_server/database/schema.py`
Define database schema and SQL statements:
- Constants for table names, column names
- SQL CREATE TABLE statement for `memories` table with all fields (id, content, content_hash, priority, category, tags as JSON, project_id, source, timestamps, embedding_model, embedding_model_version, embedding_dimension, access_count, last_accessed_at, usage_contexts as JSON)
- SQL CREATE VIRTUAL TABLE for `vec_memories` using sqlite-vec with memory_id and embedding[384]
- SQL CREATE INDEX statements for: idx_priority, idx_project_id, idx_created_at, idx_content_hash
- Schema validation functions

#### 1.2 Create `src/memory_server/database/manager.py`
Implement DatabaseManager class:
- `__init__`: Accept db_path parameter (defaults to ~/.memory/db)
- `initialize()`: Create database file, load sqlite-vec extension, create tables and indexes if not exist
- `_load_vec_extension()`: Load sqlite-vec shared library
- `insert_memory()`: Insert into both memories and vec_memories tables, return memory_id
- `get_memory_by_id()`: Fetch single memory with all metadata
- `get_memory_by_hash()`: Fetch by content_hash
- `delete_memory()`: Delete from both tables by memory_id
- `vector_search()`: KNN search using sqlite-vec distance function, return memory_ids + similarity scores
- `list_memories()`: Query with filters (priority, tags, date_range), sorting, pagination
- `update_access_count()`: Increment access_count and update last_accessed_at
- `check_duplicate_hash()`: Check if content_hash exists
- Context manager support for connections
- Transaction handling with rollback on error

#### 1.3 Update `src/memory_server/database/__init__.py`
Export DatabaseManager class

---

### Stage 2: Embedding Service
**Priority: CRITICAL - Needed before storage**

#### 2.1 Create `src/memory_server/embedding/service.py`
Implement EmbeddingService class:
- `__init__`: Initialize FastEmbed with BAAI/bge-small-en-v1.5 model, CPU device
- `generate_embedding()`: Take text string, return 384-dim numpy array
- `generate_embeddings_batch()`: Take list of strings, return list of embeddings (efficient batching)
- `get_model_info()`: Return model name and version
- `get_dimension()`: Return 384
- Handle model download on first run
- Error handling for embedding failures
- Normalize embeddings (unit vectors)

#### 2.2 Create `src/memory_server/embedding/cache.py`
Implement EmbeddingCache class:
- LRU cache for embeddings (max 1000 entries)
- `get(content_hash)`: Return cached embedding or None
- `set(content_hash, embedding)`: Store embedding in cache
- `clear()`: Clear entire cache
- Thread-safe operations

#### 2.3 Update `src/memory_server/embedding/__init__.py`
Export EmbeddingService and EmbeddingCache

---

### Stage 3: Scoring Algorithm
**Priority: HIGH - Needed for search**

#### 3.1 Create `src/memory_server/utils/scoring.py`
Implement scoring functions:
- `calculate_recency_score(created_at)`: Exponential decay from current time (e^(-days/30))
- `calculate_priority_score(priority)`: Map CORE=1.0, HIGH=0.75, NORMAL=0.5, LOW=0.25
- `calculate_usage_score(access_count)`: Log-scaled log(access_count + 1) / log(100)
- `calculate_composite_score(similarity, created_at, priority, access_count)`: Combine with weights (40% similarity, 20% recency, 20% priority, 20% usage)
- `score_memories(memories, similarity_scores)`: Batch score list of memories, return sorted with score breakdowns
- Include docstrings with formula explanations

#### 3.2 Update `src/memory_server/utils/__init__.py`
Export scoring functions

---

### Stage 4: Memory Service (Business Logic)
**Priority: HIGH - Core functionality**

#### 4.1 Create `src/memory_server/service.py`
Implement MemoryService class:
- `__init__`: Initialize DatabaseManager, EmbeddingService, EmbeddingCache, load config
- `store_memory(content, tags, priority, category, source)`:
  - Generate content_hash (SHA256)
  - Check for duplicate hash → if exists, return existing memory_id with duplicate=True
  - Generate embedding (check cache first)
  - Check vector similarity for near-duplicates (>0.9) → if found, return with suggestion to merge
  - Insert into database with embedding
  - Cache embedding
  - Return memory_id, success=True
- `search_memory(query, limit, filters)`:
  - Generate query embedding
  - Perform vector search from database (get top N*2 candidates)
  - Fetch full memory details
  - Apply composite scoring
  - Apply filters (tags, priority, date_range)
  - Sort by final score
  - Return top N with scores and breakdowns
- `list_memories(filters, sort_by, limit, offset)`:
  - Query database with filters
  - Apply sorting
  - Return paginated results with metadata
- `delete_memory(memory_id, content_hash)`:
  - Delete from database
  - Return success status
- `get_memory(memory_id)`:
  - Fetch and increment access count
  - Return memory details
- Error handling with logging

---

### Stage 5: MCP Tools (User Interface)
**Priority: HIGH - User-facing**

#### 5.1 Create `src/memory_server/tools/__init__.py`
Setup tool registration helper

#### 5.2 Create `src/memory_server/tools/store.py`
Implement store_memory tool:
- Input schema: content (required), tags (list, optional), priority (enum, default NORMAL), category (optional), source (optional)
- Validation: content not empty, priority in allowed values
- Call MemoryService.store_memory()
- Return: memory_id, duplicate flag, success message
- Error messages for validation failures

#### 5.3 Create `src/memory_server/tools/search.py`
Implement search_memory tool:
- Input schema: query (required), limit (default 10), filters (optional dict with tags, priority, date_range)
- Call MemoryService.search_memory()
- Return: list of memories with scores, score breakdowns, total count
- Format output for readability

#### 5.4 Create `src/memory_server/tools/list.py`
Implement list_memories tool:
- Input schema: filters (optional), sort_by (default created_at desc), limit (default 50), offset (default 0)
- Call MemoryService.list_memories()
- Return: paginated list with metadata (total, has_more)

#### 5.5 Create `src/memory_server/tools/delete.py`
Implement delete_memory tool:
- Input schema: memory_id OR content_hash (one required)
- Validation: at least one provided
- Call MemoryService.delete_memory()
- Return: success message with deleted memory info

#### 5.6 Update `src/memory_server/server.py`
- Initialize MemoryService on server startup
- Register all 4 tools with FastMCP
- Keep existing ping tool
- Add error handling middleware
- Set up stdio transport

#### 5.7 Update `src/memory_server/__init__.py`
Export main() function that starts server

---

### Stage 6: Testing Infrastructure
**Priority: MEDIUM - Validation**

#### 6.1 Create `tests/conftest.py`
Shared pytest fixtures:
- `temp_db_path`: Temporary database file for testing
- `mock_embedding_service`: Mock that returns deterministic embeddings from content hash
- `test_db_manager`: DatabaseManager with temp database
- `test_memory_service`: MemoryService with mocked embeddings
- `sample_memories`: List of 5-10 test memory objects
- Async fixtures for async tests

#### 6.2 Create `tests/fixtures/MEMORIES-SEED.md`
20 realistic test memories in markdown format:
- 7 architectural decisions (database choices, framework decisions)
- 6 bug fixes with solutions (async issues, database locks)
- 5 code patterns (error handling, testing patterns)
- 2 configuration notes (environment setup)

#### 6.3 Create `tests/fixtures/seed_memories.py`
Script to parse MEMORIES-SEED.md and load into test database

#### 6.4 Create `tests/unit/test_database.py`
Unit tests for DatabaseManager:
- Test database initialization creates tables and indexes
- Test insert_memory and get_memory_by_id
- Test delete_memory
- Test check_duplicate_hash
- Test list_memories with various filters
- Test vector_search returns expected structure
- Use in-memory database (:memory:)

#### 6.5 Create `tests/unit/test_embeddings.py`
Unit tests for EmbeddingService:
- Test generate_embedding returns 384-dim array
- Test generate_embeddings_batch
- Test embedding normalization
- Test cache hit/miss behavior
- Mock FastEmbed to avoid model download

#### 6.6 Create `tests/unit/test_scoring.py`
Unit tests for scoring functions:
- Test recency_score with known timestamps
- Test priority_score for all priority levels
- Test usage_score with various access counts
- Test composite_score combines correctly
- Test score_memories sorts correctly

#### 6.7 Create `tests/unit/test_service.py`
Unit tests for MemoryService:
- Test store_memory with mock embeddings
- Test duplicate detection (hash and vector)
- Test search_memory returns scored results
- Test list_memories applies filters
- Test delete_memory
- Mock DatabaseManager and EmbeddingService

#### 6.8 Create `tests/integration/test_end_to_end.py`
Integration tests with real embeddings and database:
- Test store → search flow finds relevant memories
- Test semantic search returns related content
- Test filtering works correctly
- Test scoring ranks results appropriately
- Use temporary database, real FastEmbed

#### 6.9 Create `tests/integration/test_mcp_client.py`
E2E tests with FastMCP Client:
- Test server startup and connection
- Test calling store_memory tool
- Test calling search_memory tool
- Test calling list_memories tool
- Test calling delete_memory tool
- Test error handling for invalid inputs

---

## File Checklist

### New Files to Create (19):
- [ ] `src/memory_server/database/schema.py`
- [ ] `src/memory_server/database/manager.py`
- [ ] `src/memory_server/embedding/service.py`
- [ ] `src/memory_server/embedding/cache.py`
- [ ] `src/memory_server/utils/scoring.py`
- [ ] `src/memory_server/service.py`
- [ ] `src/memory_server/tools/__init__.py`
- [ ] `src/memory_server/tools/store.py`
- [ ] `src/memory_server/tools/search.py`
- [ ] `src/memory_server/tools/list.py`
- [ ] `src/memory_server/tools/delete.py`
- [ ] `tests/conftest.py`
- [ ] `tests/fixtures/MEMORIES-SEED.md`
- [ ] `tests/fixtures/seed_memories.py`
- [ ] `tests/unit/test_database.py`
- [ ] `tests/unit/test_embeddings.py`
- [ ] `tests/unit/test_scoring.py`
- [ ] `tests/unit/test_service.py`
- [ ] `tests/integration/test_end_to_end.py`
- [ ] `tests/integration/test_mcp_client.py`

### Files to Edit (5):
- [ ] `src/memory_server/database/__init__.py` - Export DatabaseManager
- [ ] `src/memory_server/embedding/__init__.py` - Export EmbeddingService, EmbeddingCache
- [ ] `src/memory_server/utils/__init__.py` - Export scoring functions
- [ ] `src/memory_server/server.py` - Register tools, initialize service
- [ ] `src/memory_server/__init__.py` - Export main()

---

## Success Criteria
1. ✅ All 4 MCP tools work (store, search, list, delete)
2. ✅ Semantic search returns relevant results
3. ✅ Duplicate detection works (hash and vector similarity)
4. ✅ Search latency < 100ms for reasonable dataset
5. ✅ Test coverage > 80%
6. ✅ All tests pass
7. ✅ Server starts successfully via `memory-server` command
8. ✅ Can be configured in Claude Code's config.json

---

## Implementation Notes for Agentic Coder

**Important Dependencies:**
- sqlite-vec extension must be loaded before creating virtual tables
- FastEmbed downloads model on first use (~100MB) - handle gracefully
- Use asyncio for FastMCP server (async tool handlers)
- Connection handling: use context managers, enable WAL mode for concurrency

**Error Handling Patterns:**
- Database: Retry on lock errors with exponential backoff
- Embeddings: Graceful fallback if model fails to load
- Validation: Pydantic models with clear error messages
- Tools: Catch exceptions, return user-friendly error messages

**Testing Strategy:**
- Unit tests: Fast, mocked, isolated
- Integration tests: Real embeddings, temporary database
- E2E tests: Full MCP client-server interaction

**Code Quality:**
- Type hints everywhere (use Pydantic for validation)
- Docstrings with examples
- Logging at appropriate levels (INFO for operations, DEBUG for details)
- Follow existing code style (check config/settings.py as reference)

**Configuration:**
- Respect settings from config/settings.py
- Global database path: `Path.home() / ".memory" / "db"`
- Create parent directories if needed
- Handle missing config gracefully with defaults

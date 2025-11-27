import { describe, expect, test, beforeEach, afterEach } from "bun:test";
import { mkdtempSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import type { Database } from "bun:sqlite";
import { createDatabase, type DrizzleDB } from "../src/db/connection";
import { MemoryRepository } from "../src/db/memory.repository";
import { EmbeddingsService } from "../src/services/embeddings.service";
import { MemoryService } from "../src/services/memory.service";
import { DELETED_TOMBSTONE } from "../src/types/memory";

describe("MemoryService", () => {
  let db: DrizzleDB;
  let sqlite: Database;
  let repository: MemoryRepository;
  let embeddings: EmbeddingsService;
  let service: MemoryService;
  let tmpDir: string;
  let dbPath: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "mcp-memory-test-"));
    dbPath = join(tmpDir, "test.db");
    const conn = createDatabase(dbPath);
    db = conn.db;
    sqlite = conn.sqlite;
    repository = new MemoryRepository(db, sqlite);
    embeddings = new EmbeddingsService("Xenova/all-MiniLM-L6-v2", 384);
    service = new MemoryService(repository, embeddings);
  });

  afterEach(() => {
    sqlite.close();
    rmSync(tmpDir, { recursive: true });
  });

  describe("createDatabase", () => {
    test("creates database file", () => {
      const file = Bun.file(dbPath);
      expect(file.size).toBeGreaterThan(0);
    });

    test("creates parent directories if needed", () => {
      const nestedPath = join(tmpDir, "nested", "deep", "test.db");
      const nestedConn = createDatabase(nestedPath);
      const file = Bun.file(nestedPath);
      expect(file.size).toBeGreaterThan(0);
      nestedConn.sqlite.close();
    });
  });

  describe("store", () => {
    test("creates memory with generated UUID", async () => {
      const memory = await service.store("test content");
      expect(memory.id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
      );
    });

    test("stores content correctly", async () => {
      const memory = await service.store("test content");
      expect(memory.content).toBe("test content");
    });

    test("stores metadata correctly", async () => {
      const metadata = { key: "value", nested: { a: 1 } };
      const memory = await service.store("test", metadata);
      expect(memory.metadata).toEqual(metadata);
    });

    test("defaults to empty metadata", async () => {
      const memory = await service.store("test");
      expect(memory.metadata).toEqual({});
    });

    test("generates embedding", async () => {
      const memory = await service.store("test content");
      expect(memory.embedding).toBeArray();
      expect(memory.embedding.length).toBe(384);
    });

    test("sets timestamps", async () => {
      const before = new Date();
      const memory = await service.store("test");
      const after = new Date();

      expect(memory.createdAt.getTime()).toBeGreaterThanOrEqual(before.getTime());
      expect(memory.createdAt.getTime()).toBeLessThanOrEqual(after.getTime());
      expect(memory.updatedAt.getTime()).toBe(memory.createdAt.getTime());
    });

    test("sets supersededBy to null", async () => {
      const memory = await service.store("test");
      expect(memory.supersededBy).toBeNull();
    });
  });

  describe("get", () => {
    test("retrieves stored memory", async () => {
      const stored = await service.store("test content", { key: "value" });
      const retrieved = service.get(stored.id);

      expect(retrieved).not.toBeNull();
      expect(retrieved!.id).toBe(stored.id);
      expect(retrieved!.content).toBe("test content");
      expect(retrieved!.metadata).toEqual({ key: "value" });
    });

    test("retrieves embedding", async () => {
      const stored = await service.store("test content");
      const retrieved = service.get(stored.id);

      expect(retrieved!.embedding).toBeArray();
      expect(retrieved!.embedding.length).toBe(384);
      for (let i = 0; i < 10; i++) {
        expect(retrieved!.embedding[i]).toBeCloseTo(stored.embedding[i], 5);
      }
    });

    test("returns null for non-existent ID", () => {
      const retrieved = service.get("non-existent-id");
      expect(retrieved).toBeNull();
    });

    test("retrieves deleted memory (with supersededBy set)", async () => {
      const stored = await service.store("test");
      service.delete(stored.id);

      const retrieved = service.get(stored.id);
      expect(retrieved).not.toBeNull();
      expect(retrieved!.supersededBy).toBe(DELETED_TOMBSTONE);
    });
  });

  describe("delete", () => {
    test("soft-deletes memory by setting supersededBy", async () => {
      const stored = await service.store("test");
      const success = service.delete(stored.id);

      expect(success).toBe(true);
      const retrieved = service.get(stored.id);
      expect(retrieved!.supersededBy).toBe(DELETED_TOMBSTONE);
    });

    test("returns false for non-existent ID", () => {
      const success = service.delete("non-existent-id");
      expect(success).toBe(false);
    });

    test("can delete already deleted memory", async () => {
      const stored = await service.store("test");
      service.delete(stored.id);
      const success = service.delete(stored.id);
      expect(success).toBe(true);
    });
  });

  describe("search", () => {
    test("finds semantically similar memories", async () => {
      await service.store("Python is a programming language");
      await service.store("JavaScript runs in web browsers");
      await service.store("Cats are furry animals");

      const results = await service.search("coding and software development");

      expect(results.length).toBeGreaterThan(0);
      const contents = results.map((r) => r.content);
      expect(
        contents[0].includes("Python") || contents[0].includes("JavaScript")
      ).toBe(true);
    });

    test("respects limit parameter", async () => {
      await service.store("Memory 1");
      await service.store("Memory 2");
      await service.store("Memory 3");

      const results = await service.search("memory", 2);
      expect(results.length).toBe(2);
    });

    test("defaults to limit of 10", async () => {
      for (let i = 0; i < 15; i++) {
        await service.store(`Memory ${i}`);
      }

      const results = await service.search("memory");
      expect(results.length).toBe(10);
    });

    test("excludes deleted memories", async () => {
      const mem1 = await service.store("Python programming");
      await service.store("JavaScript programming");

      service.delete(mem1.id);

      const results = await service.search("programming");
      expect(results.length).toBe(1);
      expect(results[0].content).toBe("JavaScript programming");
    });

    test("returns empty array when no matches", async () => {
      const results = await service.search("nonexistent query");
      expect(results).toBeArray();
      expect(results.length).toBe(0);
    });

    test("excludes superseded memories but follows chain to head", async () => {
      const mem1 = await service.store("Original content about cats");
      const mem2 = await service.store("Updated content about cats");

      sqlite.query("UPDATE memories SET superseded_by = ? WHERE id = ?").run(
        mem2.id,
        mem1.id
      );

      const results = await service.search("cats");
      expect(results.length).toBe(1);
      expect(results[0].id).toBe(mem2.id);
    });

    test("avoids duplicate results from supersession chains", async () => {
      const mem1 = await service.store("Cats are pets");
      const mem2 = await service.store("Cats are furry pets");
      const mem3 = await service.store("Cats are furry friendly pets");

      sqlite.query("UPDATE memories SET superseded_by = ? WHERE id = ?").run(
        mem2.id,
        mem1.id
      );
      sqlite.query("UPDATE memories SET superseded_by = ? WHERE id = ?").run(
        mem3.id,
        mem2.id
      );

      const results = await service.search("cats pets", 10);
      const ids = results.map((r) => r.id);
      const uniqueIds = [...new Set(ids)];
      expect(ids.length).toBe(uniqueIds.length);
    });
  });
});

describe("MemoryRepository", () => {
  let db: DrizzleDB;
  let sqlite: Database;
  let repository: MemoryRepository;
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "mcp-memory-test-"));
    const dbPath = join(tmpDir, "test.db");
    const conn = createDatabase(dbPath);
    db = conn.db;
    sqlite = conn.sqlite;
    repository = new MemoryRepository(db, sqlite);
  });

  afterEach(() => {
    sqlite.close();
    rmSync(tmpDir, { recursive: true });
  });

  describe("findSimilar", () => {
    test("returns empty array when no memories", () => {
      const results = repository.findSimilar(new Array(384).fill(0), 10);
      expect(results).toBeArray();
      expect(results.length).toBe(0);
    });
  });
});

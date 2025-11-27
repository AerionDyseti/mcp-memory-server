import type { Database } from "bun:sqlite";
import { eq } from "drizzle-orm";
import {
  serializeVector,
  deserializeVector,
} from "@aeriondyseti/drizzle-sqlite-vec";

import type { DrizzleDB } from "./connection.js";
import { memories } from "./schema.js";
import {
  type Memory,
  type VectorRow,
  DELETED_TOMBSTONE,
} from "../types/memory.js";

export class MemoryRepository {
  constructor(
    private db: DrizzleDB,
    private sqlite: Database
  ) {}

  insert(memory: Memory): void {
    // Insert into memories table using Drizzle
    this.db.insert(memories).values({
      id: memory.id,
      content: memory.content,
      metadata: JSON.stringify(memory.metadata),
      createdAt: memory.createdAt.toISOString(),
      updatedAt: memory.updatedAt.toISOString(),
      supersededBy: memory.supersededBy,
    }).run();

    // Insert into vec_memories using raw SQL (sqlite-vec doesn't work with ORMs)
    this.sqlite
      .query(`INSERT INTO vec_memories (id, embedding) VALUES (?, ?)`)
      .run(memory.id, serializeVector(memory.embedding));
  }

  findById(id: string): Memory | null {
    const row = this.db
      .select()
      .from(memories)
      .where(eq(memories.id, id))
      .get();

    if (!row) {
      return null;
    }

    // Get embedding from vec_memories using raw SQL
    const vecRow = this.sqlite
      .query("SELECT embedding FROM vec_memories WHERE id = ?")
      .get(id) as { embedding: Uint8Array } | null;

    const embedding = vecRow ? deserializeVector(Buffer.from(vecRow.embedding)) : [];

    return {
      id: row.id,
      content: row.content,
      embedding,
      metadata: JSON.parse(row.metadata),
      createdAt: new Date(row.createdAt),
      updatedAt: new Date(row.updatedAt),
      supersededBy: row.supersededBy,
    };
  }

  markDeleted(id: string): boolean {
    const existing = this.db
      .select({ id: memories.id })
      .from(memories)
      .where(eq(memories.id, id))
      .get();

    if (!existing) {
      return false;
    }

    const now = new Date();
    this.db
      .update(memories)
      .set({
        supersededBy: DELETED_TOMBSTONE,
        updatedAt: now.toISOString(),
      })
      .where(eq(memories.id, id))
      .run();

    return true;
  }

  findSimilar(embedding: number[], limit: number): VectorRow[] {
    // Vector search must use raw SQL
    return this.sqlite
      .query(
        `SELECT id, distance
         FROM vec_memories
         WHERE embedding MATCH ?
         ORDER BY distance
         LIMIT ?`
      )
      .all(serializeVector(embedding), limit) as VectorRow[];
  }
}

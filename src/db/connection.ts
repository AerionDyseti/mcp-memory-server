import { Database } from "bun:sqlite";
import { drizzle, type BunSQLiteDatabase } from "drizzle-orm/bun-sqlite";
import * as sqliteVec from "sqlite-vec";
import { mkdirSync } from "fs";
import { dirname } from "path";
import { sql } from "drizzle-orm";

import * as schema from "./schema.js";
import { vecMemories } from "./schema.js";

export type DrizzleDB = BunSQLiteDatabase<typeof schema>;

export interface DatabaseConnection {
  db: DrizzleDB;
  sqlite: Database;
}

export function createDatabase(dbPath: string): DatabaseConnection {
  // Ensure directory exists
  mkdirSync(dirname(dbPath), { recursive: true });

  const sqlite = new Database(dbPath);
  sqliteVec.load(sqlite);

  const db = drizzle(sqlite, { schema });

  initSchema(db, sqlite);

  return { db, sqlite };
}

function initSchema(db: DrizzleDB, sqlite: Database): void {
  // Create memories table using Drizzle
  db.run(sql`
    CREATE TABLE IF NOT EXISTS memories (
      id TEXT PRIMARY KEY,
      content TEXT NOT NULL,
      metadata TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      superseded_by TEXT
    )
  `);

  // Create vec_memories virtual table using drizzle-sqlite-vec
  sqlite.run(vecMemories.createSQL());
}

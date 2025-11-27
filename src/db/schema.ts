import { sqliteTable, text } from "drizzle-orm/sqlite-core";
import {
  vec0Table,
  vecText,
  vecFloat,
  EmbeddingDimensions,
} from "@aeriondyseti/drizzle-sqlite-vec";

export const memories = sqliteTable("memories", {
  id: text("id").primaryKey(),
  content: text("content").notNull(),
  metadata: text("metadata").notNull().default("{}"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
  supersededBy: text("superseded_by"),
});

export const vecMemories = vec0Table("vec_memories", {
  id: vecText("id").primaryKey(),
  embedding: vecFloat("embedding", EmbeddingDimensions.MINILM_L6_V2),
});

export type MemoryRecord = typeof memories.$inferSelect;
export type NewMemoryRecord = typeof memories.$inferInsert;

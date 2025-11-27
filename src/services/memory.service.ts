import { randomUUID } from "crypto";
import type { Memory } from "../types/memory.js";
import { DELETED_TOMBSTONE, isSuperseded } from "../types/memory.js";
import type { MemoryRepository } from "../db/memory.repository.js";
import type { EmbeddingsService } from "./embeddings.service.js";

export class MemoryService {
  constructor(
    private repository: MemoryRepository,
    private embeddings: EmbeddingsService
  ) {}

  async store(content: string, metadata: Record<string, unknown> = {}): Promise<Memory> {
    const id = randomUUID();
    const now = new Date();
    const embedding = await this.embeddings.embed(content);

    const memory: Memory = {
      id,
      content,
      embedding,
      metadata,
      createdAt: now,
      updatedAt: now,
      supersededBy: null,
    };

    this.repository.insert(memory);
    return memory;
  }

  get(id: string): Memory | null {
    return this.repository.findById(id);
  }

  delete(id: string): boolean {
    return this.repository.markDeleted(id);
  }

  async search(query: string, limit: number = 10): Promise<Memory[]> {
    const queryEmbedding = await this.embeddings.embed(query);
    const fetchLimit = limit * 3;

    const rows = this.repository.findSimilar(queryEmbedding, fetchLimit);

    const results: Memory[] = [];
    const seenIds = new Set<string>();

    for (const row of rows) {
      let memory = this.repository.findById(row.id);

      if (!memory) {
        continue;
      }

      if (isSuperseded(memory)) {
        memory = this.followSupersessionChain(row.id);
        if (!memory) {
          continue;
        }
      }

      if (seenIds.has(memory.id)) {
        continue;
      }
      seenIds.add(memory.id);

      results.push(memory);
      if (results.length >= limit) {
        break;
      }
    }

    return results;
  }

  private followSupersessionChain(memoryId: string): Memory | null {
    const visited = new Set<string>();
    let currentId: string | null = memoryId;

    while (currentId && !visited.has(currentId)) {
      visited.add(currentId);
      const memory = this.repository.findById(currentId);

      if (!memory) {
        return null;
      }

      if (memory.supersededBy === null) {
        return memory;
      }

      if (memory.supersededBy === DELETED_TOMBSTONE) {
        return null;
      }

      currentId = memory.supersededBy;
    }

    return null;
  }
}

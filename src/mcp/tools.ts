import type { Tool } from "@modelcontextprotocol/sdk/types.js";

export const storeMemoryTool: Tool = {
  name: "store_memory",
  description: "Store a new memory. Use this to save information for later recall.",
  inputSchema: {
    type: "object",
    properties: {
      content: {
        type: "string",
        description: "The text content to store as a memory",
      },
      metadata: {
        type: "object",
        description: "Optional key-value metadata to attach to the memory",
        additionalProperties: true,
      },
    },
    required: ["content"],
  },
};

export const deleteMemoryTool: Tool = {
  name: "delete_memory",
  description:
    "Delete a memory by its ID. The memory will be soft-deleted and won't appear in search results.",
  inputSchema: {
    type: "object",
    properties: {
      id: {
        type: "string",
        description: "The ID of the memory to delete",
      },
    },
    required: ["id"],
  },
};

export const searchMemoriesTool: Tool = {
  name: "search_memories",
  description:
    "Search for memories using semantic similarity. Returns the most relevant memories for the given query.",
  inputSchema: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "The search query to find relevant memories",
      },
      limit: {
        type: "integer",
        description: "Maximum number of results to return (default: 10)",
        default: 10,
      },
    },
    required: ["query"],
  },
};

export const getMemoryTool: Tool = {
  name: "get_memory",
  description: "Retrieve a specific memory by its ID.",
  inputSchema: {
    type: "object",
    properties: {
      id: {
        type: "string",
        description: "The ID of the memory to retrieve",
      },
    },
    required: ["id"],
  },
};

export const tools: Tool[] = [
  storeMemoryTool,
  deleteMemoryTool,
  searchMemoriesTool,
  getMemoryTool,
];

"""
Script to parse MEMORIES-SEED.md and load memories into test database.

This module provides utilities for seeding test databases with realistic
memory data from the MEMORIES-SEED.md file.
"""

import re
from pathlib import Path
from typing import Any

from memory_server.service import MemoryService


def parse_seed_markdown(content: str) -> list[dict[str, Any]]:
    """
    Parse markdown seed format into memory dictionaries.

    Expected format:
    ## Title
    **Tags:** tag1, tag2, tag3
    **Priority:** HIGH
    **Category:** category-name
    **Content:**
    Memory content here...

    Args:
        content: Markdown content from MEMORIES-SEED.md

    Returns:
        List of memory dictionaries ready for storage
    """
    memories = []

    # Split by horizontal rules (---)
    sections = re.split(r"^---\s*$", content, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section or not section.startswith("##"):
            continue

        # Extract title (first line after ##)
        lines = section.split("\n")
        title_match = re.match(r"^##\s+(.+)$", lines[0])
        if not title_match:
            continue

        memory: dict[str, Any] = {
            "content": "",
            "tags": None,
            "priority": "NORMAL",
            "category": None,
            "source": "seed",
        }

        # Parse metadata lines
        i = 1
        while i < len(lines):
            line = lines[i].strip()

            # Tags
            if line.startswith("**Tags:**"):
                tags_str = line.replace("**Tags:**", "").strip()
                memory["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

            # Priority
            elif line.startswith("**Priority:**"):
                priority = line.replace("**Priority:**", "").strip()
                memory["priority"] = priority

            # Category
            elif line.startswith("**Category:**"):
                category = line.replace("**Category:**", "").strip()
                memory["category"] = category

            # Content section
            elif line.startswith("**Content:**"):
                # Collect all content after this line
                content_lines = []
                i += 1
                while i < len(lines):
                    content_lines.append(lines[i])
                    i += 1
                memory["content"] = "\n".join(content_lines).strip()
                break

            i += 1

        # Only add if we have content
        if memory["content"]:
            memories.append(memory)

    return memories


def seed_memories_from_file(
    service: MemoryService, seed_file: Path
) -> int:
    """
    Load memories from seed file into the memory service.

    Args:
        service: MemoryService instance
        seed_file: Path to MEMORIES-SEED.md file

    Returns:
        Number of memories successfully stored
    """
    content = seed_file.read_text(encoding="utf-8")
    memories = parse_seed_markdown(content)

    stored_count = 0
    for memory in memories:
        try:
            result = service.store_memory(
                content=memory["content"],
                tags=memory.get("tags"),
                priority=memory.get("priority", "NORMAL"),
                category=memory.get("category"),
                source=memory.get("source", "seed"),
            )
            if result["success"]:
                stored_count += 1
        except Exception as e:
            print(f"Failed to store memory: {e}")
            continue

    return stored_count


def get_seed_file_path() -> Path:
    """
    Get the path to MEMORIES-SEED.md file.

    Returns:
        Path to seed file
    """
    # Assume we're in tests/fixtures/ or tests/
    current_file = Path(__file__)
    seed_file = current_file.parent / "MEMORIES-SEED.md"
    if seed_file.exists():
        return seed_file

    # Try tests/fixtures/
    seed_file = current_file.parent.parent / "fixtures" / "MEMORIES-SEED.md"
    return seed_file


# For direct execution
if __name__ == "__main__":
    seed_file = get_seed_file_path()
    if not seed_file.exists():
        print(f"Seed file not found: {seed_file}")
    else:
        service = MemoryService()
        count = seed_memories_from_file(service, seed_file)
        print(f"✓ Seeded {count} test memories")

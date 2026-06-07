"""
services/__init__.py — Shared data models for the GraphRAG pipeline.

Every phase consumes and produces the types defined here so that the
inter-phase contracts are explicit and Pydantic-validated.
"""

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, field_validator


# ── Phase 1 output ────────────────────────────────────────────────────────────

class ChunkDict(TypedDict):
    text: str
    source: str
    chunk_index: int
    page_number: int


# ── Phase 2 Pydantic models ───────────────────────────────────────────────────

class Entity(BaseModel):
    name: str
    type: str

    @field_validator("name", "type", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class Relation(BaseModel):
    source: str
    relation: str
    target: str

    @field_validator("source", "relation", "target", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class ExtractionResult(BaseModel):
    chunk_index: int
    entities: list[Entity]
    relations: list[Relation]


# ── Phase 4 output ────────────────────────────────────────────────────────────

class CommunityGroup(TypedDict):
    community_id: int
    level: str          # "root" | "low" | "high"
    node_names: list[str]


# ── Phase 5 output ────────────────────────────────────────────────────────────

class CommunitySummary(TypedDict):
    community_id: int
    level: str
    summary_text: str


__all__ = [
    "ChunkDict",
    "Entity",
    "Relation",
    "ExtractionResult",
    "CommunityGroup",
    "CommunitySummary",
]

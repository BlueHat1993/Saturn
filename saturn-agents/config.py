"""
config.py — Centralised settings loaded from .env via Pydantic-Settings.

All services receive a Settings instance through dependency injection;
nothing reads environment variables directly outside this module.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── LLM keys ────────────────────────────────────────────────────────────
    deepseek_api_key: str
    google_api_key: str

    # ── Neo4j ────────────────────────────────────────────────────────────────
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    # ── Qdrant ───────────────────────────────────────────────────────────────
    qdrant_host: str
    qdrant_port: int
    qdrant_collection: str

    # ── Chunking ─────────────────────────────────────────────────────────────
    chunk_size: int
    chunk_overlap: int

    # ── Parallelism ──────────────────────────────────────────────────────────
    max_workers: int

    # ── Embedding ────────────────────────────────────────────────────────────
    embedding_model: str
    embedding_dim: int

    # ── DeepSeek endpoint ────────────────────────────────────────────────────
    deepseek_base_url: str
    deepseek_model: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a singleton Settings instance (cached after first call)."""
    return Settings()

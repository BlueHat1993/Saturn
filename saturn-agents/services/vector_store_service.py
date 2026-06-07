"""
services/vector_store_service.py — Phase 6: embed summaries & chunks, upsert to Qdrant.

Embeds each community summary and each original text chunk using the
Gemini embedding-2 model (3072-dimensional vectors), then upserts them
into the Qdrant collection `graph_rag` with typed payloads so the collection
supports filtered semantic search by type, level, community_id, etc.

Point IDs are stable UUIDs derived from content keys via uuid5, so the
pipeline is idempotent — re-running overwrites existing points cleanly.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from google import genai
from qdrant_client.models import PointStruct

from config import Settings
from db import QdrantClientWrapper
from services import ChunkDict, CommunitySummary

logger = logging.getLogger(__name__)

# Stable UUID namespace — do NOT change after first run or IDs will shift
_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # RFC 4122 URL namespace


def _stable_uuid(key: str) -> str:
    """Generate a deterministic UUID string from a unique string key."""
    return str(uuid.uuid5(_NAMESPACE, key))


class VectorStoreService:
    """
    Phase 6 — summaries + chunks → Qdrant vectors.

    Args:
        qdrant_wrapper: Injected QdrantClientWrapper.
        settings:       Injected application settings.
    """

    def __init__(self, qdrant_wrapper: QdrantClientWrapper, settings: Settings) -> None:
        self._qdrant = qdrant_wrapper
        self._settings = settings
        # Initialise Gemini client (picks up GOOGLE_API_KEY from env)
        self._genai_client = genai.Client(api_key=settings.google_api_key)

    def embed_and_store(
        self,
        summaries: list[CommunitySummary],
        chunks: list[ChunkDict],
    ) -> None:
        """
        Embed all summaries and chunks, then upsert into Qdrant.

        Args:
            summaries: Output of Phase 5.
            chunks:    Output of Phase 1.
        """
        collection = self._settings.qdrant_collection
        vector_size = self._settings.embedding_dim

        # Ensure the collection exists with correct dimensions
        self._qdrant.ensure_collection(name=collection, vector_size=vector_size)

        # ── Upsert community summaries ────────────────────────────────────────
        logger.info("Embedding %d community summaries…", len(summaries))
        summary_points = self._build_summary_points(summaries)
        self._upsert_batch(collection, summary_points)
        logger.info("  → %d summary points upserted.", len(summary_points))

        # ── Upsert text chunks ────────────────────────────────────────────────
        logger.info("Embedding %d text chunks…", len(chunks))
        chunk_points = self._build_chunk_points(chunks)
        self._upsert_batch(collection, chunk_points)
        logger.info("  → %d chunk points upserted.", len(chunk_points))

        logger.info(
            "Phase 6 complete: collection '%s' has %d + %d = %d total points.",
            collection,
            len(summary_points),
            len(chunk_points),
            len(summary_points) + len(chunk_points),
        )

    # ── Builders ──────────────────────────────────────────────────────────────

    def _build_summary_points(self, summaries: list[CommunitySummary]) -> list[PointStruct]:
        points: list[PointStruct] = []
        for summary in summaries:
            vector = self._embed(summary["summary_text"])
            point_id = _stable_uuid(f"community:{summary['community_id']}")
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "type": "community",
                        "community_id": summary["community_id"],
                        "level": summary["level"],
                        "text": summary["summary_text"],
                    },
                )
            )
        return points

    def _build_chunk_points(self, chunks: list[ChunkDict]) -> list[PointStruct]:
        points: list[PointStruct] = []
        for chunk in chunks:
            vector = self._embed(chunk["text"])
            point_id = _stable_uuid(f"chunk:{chunk['chunk_index']}:{chunk['source']}")
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "type": "chunk",
                        "chunk_index": chunk["chunk_index"],
                        "source": chunk["source"],
                        "page_number": chunk["page_number"],
                        "text": chunk["text"],
                    },
                )
            )
        return points

    # ── Embedding ─────────────────────────────────────────────────────────────

    def _embed(self, text: str) -> list[float]:
        """Embed a single text string using Gemini embedding-2 (3072 dims)."""
        response = self._genai_client.models.embed_content(
            model=self._settings.embedding_model,
            contents=text,
        )
        # gemini-embedding-2 returns a list of EmbedContentResponse;
        # take the first (and only) embedding's values
        return list(response.embeddings[0].values)

    # ── Qdrant upsert ─────────────────────────────────────────────────────────

    def _upsert_batch(self, collection: str, points: list[PointStruct]) -> None:
        """Upsert a batch of points into Qdrant in one call."""
        if not points:
            return
        client = self._qdrant.get_client()
        client.upsert(collection_name=collection, points=points)

"""
db/qdrant_client.py — Thin wrapper around the Qdrant Python client.

Handles collection bootstrapping (idempotent) and exposes the raw client
for injection into VectorStoreService.
"""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


class QdrantClientWrapper:
    """Manages a single QdrantClient instance for the lifetime of the pipeline."""

    def __init__(self, host: str, port: int) -> None:
        self._client = QdrantClient(host=host, port=port)

    def get_client(self) -> QdrantClient:
        """Return the underlying raw QdrantClient (for injection)."""
        return self._client

    def ensure_collection(self, name: str, vector_size: int) -> None:
        """
        Idempotently create a Qdrant collection.

        If the collection already exists with matching vector dimensions this
        is a no-op; if the dimensions differ a ValueError is raised to protect
        against silent data corruption.
        """
        existing = {c.name: c for c in self._client.get_collections().collections}

        if name in existing:
            actual_size = (
                existing[name].config.params.vectors.size  # type: ignore[union-attr]
                if hasattr(existing[name].config.params.vectors, "size")
                else next(iter(existing[name].config.params.vectors.values())).size  # type: ignore[union-attr]
            )
            if actual_size != vector_size:
                raise ValueError(
                    f"Qdrant collection '{name}' exists with dim={actual_size}, "
                    f"expected dim={vector_size}. Delete the collection first."
                )
            return  # already correct — nothing to do

        self._client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "QdrantClientWrapper":
        return self

    def __exit__(self, *_) -> None:
        self.close()

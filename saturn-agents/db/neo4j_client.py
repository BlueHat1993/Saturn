"""
db/neo4j_client.py — Thin wrapper around the Neo4j driver.

Intended to be instantiated once in main.py and dependency-injected into
every service that needs graph access.  Implements the context-manager
protocol so callers can use it with `with Neo4jClient(...) as client:`.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from neo4j import GraphDatabase, Session


class Neo4jClient:
    """Manages a single Neo4j driver instance for the lifetime of the pipeline."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    # ── Context manager (outer — wraps the whole pipeline run) ───────────────

    def __enter__(self) -> "Neo4jClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── Session factory (used per-service call) ───────────────────────────────

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Yield a live Neo4j session; auto-closes on exit."""
        with self._driver.session() as sess:
            yield sess

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        """Explicitly close the underlying driver (called in __exit__)."""
        self._driver.close()

    def verify_connectivity(self) -> None:
        """Raise if the database is unreachable."""
        self._driver.verify_connectivity()

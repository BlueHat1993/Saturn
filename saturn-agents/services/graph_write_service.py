"""
services/graph_write_service.py — Phase 3: write entities and relationships to Neo4j.

Each entity is MERGEd as a node whose label equals its type and whose primary
key is `name`.  Each relation is MERGEd as a directed edge between two entity
nodes.  Both nodes and edges carry `chunk_index` and `source` as provenance
properties so every fact can be traced back to its originating chunk.
"""

from __future__ import annotations

import logging

from db import Neo4jClient
from services import ChunkDict, ExtractionResult

logger = logging.getLogger(__name__)

# Sanitise relation/type strings so they are valid Neo4j identifiers
_SAFE_CHARS = str.maketrans({" ": "_", "-": "_", "/": "_"})


def _sanitize(label: str) -> str:
    """Convert a free-text label to a valid Neo4j identifier segment."""
    return label.upper().translate(_SAFE_CHARS)


class GraphWriteService:
    """
    Phase 3 — ExtractionResults → Neo4j graph.

    Args:
        neo4j_client: Injected Neo4jClient wrapper.
    """

    def __init__(self, neo4j_client: Neo4jClient) -> None:
        self._neo4j = neo4j_client

    def write(
        self,
        extractions: list[ExtractionResult],
        chunks: list[ChunkDict],
    ) -> None:
        """
        Persist all entities and relations extracted from chunks into Neo4j.

        Args:
            extractions: Output of Phase 2.
            chunks: Output of Phase 1 (used to look up source per chunk_index).
        """
        # Build a quick lookup: chunk_index → source file path
        source_map: dict[int, str] = {c["chunk_index"]: c["source"] for c in chunks}

        entity_count = 0
        relation_count = 0

        with self._neo4j.session() as session:
            for result in extractions:
                chunk_idx = result.chunk_index
                source = source_map.get(chunk_idx, "unknown")

                # ── Write entities ────────────────────────────────────────────
                for entity in result.entities:
                    safe_type = _sanitize(entity.type)
                    session.run(
                        f"""
                        MERGE (n:`{safe_type}` {{name: $name}})
                        SET n.type       = $type,
                            n.chunk_index = $chunk_index,
                            n.source      = $source
                        """,
                        name=entity.name,
                        type=entity.type,
                        chunk_index=chunk_idx,
                        source=source,
                    )
                    entity_count += 1

                # ── Write relations ───────────────────────────────────────────
                for rel in result.relations:
                    safe_rel = _sanitize(rel.relation)
                    session.run(
                        f"""
                        MATCH (a {{name: $source_name}})
                        MATCH (b {{name: $target_name}})
                        MERGE (a)-[r:`{safe_rel}`]->(b)
                        SET r.chunk_index = $chunk_index,
                            r.source      = $source
                        """,
                        source_name=rel.source,
                        target_name=rel.target,
                        chunk_index=chunk_idx,
                        source=source,
                    )
                    relation_count += 1

        logger.info(
            "Phase 3 complete: %d entities, %d relations written to Neo4j",
            entity_count,
            relation_count,
        )

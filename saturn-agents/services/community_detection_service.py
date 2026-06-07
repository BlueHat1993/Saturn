"""
services/community_detection_service.py — Phase 4: Leiden community detection via Neo4j GDS.

Steps:
  1. Project the full Neo4j graph into a GDS in-memory projection.
  2. Run gds.leiden.write to compute community IDs and persist them on nodes.
  3. Query nodes grouped by community_id.
  4. Classify communities into levels (root / low / high) based on member count.
  5. Write community_level back to each node.
  6. Drop the GDS projection to free memory.

Level thresholds (configurable via class constants):
  root  — ≥ 50 members   (few large communities, high-level abstractions)
  low   — 10–49 members  (mid-size topic clusters)
  high  — < 10 members   (fine-grained, leaf-level communities)
"""

from __future__ import annotations

import logging

from db import Neo4jClient
from services import CommunityGroup

logger = logging.getLogger(__name__)

# ── Level thresholds ──────────────────────────────────────────────────────────
_ROOT_MIN_SIZE = 50
_LOW_MIN_SIZE = 10

_GDS_GRAPH_NAME = "saturn_pipeline_graph"


def _classify_level(member_count: int) -> str:
    if member_count >= _ROOT_MIN_SIZE:
        return "root"
    if member_count >= _LOW_MIN_SIZE:
        return "low"
    return "high"


class CommunityDetectionService:
    """
    Phase 4 — Neo4j graph → community labels.

    Args:
        neo4j_client: Injected Neo4jClient wrapper.
    """

    def __init__(self, neo4j_client: Neo4jClient) -> None:
        self._neo4j = neo4j_client

    def detect(self) -> list[CommunityGroup]:
        """
        Run Leiden community detection and return community groups.

        Returns:
            List of CommunityGroup dicts with community_id, level, node_names.
        """
        with self._neo4j.session() as session:
            self._drop_projection_if_exists(session)
            self._project_graph(session)

            try:
                self._run_leiden(session)
                communities = self._fetch_communities(session)
                self._write_levels(session, communities)
            finally:
                # Always drop the in-memory projection to avoid GDS memory leaks
                self._drop_projection(session)

        logger.info(
            "Phase 4 complete: %d communities detected (root=%d, low=%d, high=%d)",
            len(communities),
            sum(1 for c in communities if c["level"] == "root"),
            sum(1 for c in communities if c["level"] == "low"),
            sum(1 for c in communities if c["level"] == "high"),
        )
        return communities

    # ── GDS helpers ───────────────────────────────────────────────────────────

    def _drop_projection_if_exists(self, session) -> None:
        """Drop leftover projection from a previous crashed run."""
        result = session.run(
            "CALL gds.graph.exists($name) YIELD exists",
            name=_GDS_GRAPH_NAME,
        ).single()
        if result and result["exists"]:
            logger.warning("Stale GDS projection found — dropping before re-project.")
            session.run(
                "CALL gds.graph.drop($name)",
                name=_GDS_GRAPH_NAME,
            )

    def _project_graph(self, session) -> None:
        """Project all nodes and relationships into GDS memory."""
        session.run(
            """
            CALL gds.graph.project(
                $name,
                '*',
                { __ALL__: { type: '*', orientation: 'UNDIRECTED' } }
            )
            """,
            name=_GDS_GRAPH_NAME,
        )
        logger.debug("GDS graph projection '%s' created.", _GDS_GRAPH_NAME)

    def _run_leiden(self, session) -> None:
        """Execute Leiden algorithm and write community_id back to nodes."""
        result = session.run(
            """
            CALL gds.leiden.write($name, {
                writeProperty: 'community_id',
                randomSeed:    42
            })
            YIELD communityCount, modularity
            RETURN communityCount, modularity
            """,
            name=_GDS_GRAPH_NAME,
        ).single()
        if result:
            logger.info(
                "Leiden finished: %d communities, modularity=%.4f",
                result["communityCount"],
                result["modularity"],
            )

    def _fetch_communities(self, session) -> list[CommunityGroup]:
        """Group nodes by community_id and classify each group."""
        records = session.run(
            """
            MATCH (n)
            WHERE n.community_id IS NOT NULL
            WITH n.community_id AS community_id, collect(n.name) AS node_names
            RETURN community_id, node_names
            ORDER BY community_id
            """
        ).data()

        communities: list[CommunityGroup] = []
        for rec in records:
            cid = rec["community_id"]
            names = [n for n in rec["node_names"] if n is not None]
            level = _classify_level(len(names))
            communities.append(
                CommunityGroup(community_id=cid, level=level, node_names=names)
            )
        return communities

    def _write_levels(self, session, communities: list[CommunityGroup]) -> None:
        """Persist community_level back onto every node."""
        for community in communities:
            session.run(
                """
                MATCH (n)
                WHERE n.community_id = $cid
                SET n.community_level = $level
                """,
                cid=community["community_id"],
                level=community["level"],
            )
        logger.debug("community_level written to all nodes.")

    def _drop_projection(self, session) -> None:
        """Remove the in-memory GDS projection."""
        session.run("CALL gds.graph.drop($name)", name=_GDS_GRAPH_NAME)
        logger.debug("GDS projection '%s' dropped.", _GDS_GRAPH_NAME)

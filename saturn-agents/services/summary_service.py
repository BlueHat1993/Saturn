"""
services/summary_service.py — Phase 5: community summary generation via DeepSeek-chat.

For each community detected in Phase 4:
  1. Query Neo4j for all member nodes and the internal edges between them.
  2. Construct a plain-text subgraph description.
  3. Send the description to DeepSeek-chat and collect the summary.

The summary is a single paragraph of natural language that describes the
theme, key entities, and relationships within the community.
"""

from __future__ import annotations

import logging

from openai import OpenAI

from config import Settings
from db import Neo4jClient
from services import CommunityGroup, CommunitySummary

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a knowledge-graph analyst. You will be given a description of a
subgraph — a set of entities and the relationships between them.

Write a concise single-paragraph summary (3–5 sentences) that:
- Identifies the central theme or topic of this cluster.
- Names the most important entities.
- Explains the key relationships between them.
- Is written in clear, factual prose — no bullet points, no headings.
"""

_USER_TEMPLATE = """\
Summarize the following subgraph community:

{subgraph_description}
"""


class SummaryService:
    """
    Phase 5 — community groups → natural-language summaries.

    Args:
        neo4j_client: Injected Neo4jClient wrapper.
        settings:     Injected application settings.
    """

    def __init__(self, neo4j_client: Neo4jClient, settings: Settings) -> None:
        self._neo4j = neo4j_client
        self._client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self._model = settings.deepseek_model

    def summarize(self, communities: list[CommunityGroup]) -> list[CommunitySummary]:
        """
        Generate a natural-language summary for each community.

        Args:
            communities: Output of Phase 4.

        Returns:
            List of CommunitySummary dicts.
        """
        summaries: list[CommunitySummary] = []

        for community in communities:
            cid = community["community_id"]
            level = community["level"]
            logger.debug("Summarizing community %d (%s, %d nodes)", cid, level, len(community["node_names"]))

            try:
                subgraph_desc = self._build_subgraph_description(community)
                summary_text = self._call_llm(subgraph_desc)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to summarize community %d: %s", cid, exc)
                summary_text = f"[Summary unavailable for community {cid}]"

            summaries.append(
                CommunitySummary(
                    community_id=cid,
                    level=level,
                    summary_text=summary_text,
                )
            )

        logger.info("Phase 5 complete: %d community summaries generated", len(summaries))
        return summaries

    # ── private helpers ───────────────────────────────────────────────────────

    def _build_subgraph_description(self, community: CommunityGroup) -> str:
        """
        Query Neo4j for member nodes and internal edges, then format as text.
        """
        node_names = community["node_names"]
        cid = community["community_id"]

        with self._neo4j.session() as session:
            # Fetch all edges where BOTH endpoints belong to this community
            records = session.run(
                """
                MATCH (a)-[r]->(b)
                WHERE a.community_id = $cid AND b.community_id = $cid
                RETURN a.name AS src, type(r) AS rel, b.name AS tgt
                LIMIT 200
                """,
                cid=cid,
            ).data()

        lines: list[str] = [
            f"Community {cid} ({community['level']} level)",
            f"Members ({len(node_names)}): {', '.join(node_names[:30])}"
            + (" …" if len(node_names) > 30 else ""),
            "",
            "Relationships:",
        ]

        if records:
            for rec in records:
                rel_label = rec["rel"].replace("_", " ").lower()
                lines.append(f"  - {rec['src']} {rel_label} {rec['tgt']}")
        else:
            lines.append("  (no internal relationships found)")

        return "\n".join(lines)

    def _call_llm(self, subgraph_description: str) -> str:
        """Send the subgraph description to DeepSeek and return the summary text."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _USER_TEMPLATE.format(
                        subgraph_description=subgraph_description
                    ),
                },
            ],
            temperature=0.3,
        )
        return (response.choices[0].message.content or "").strip()

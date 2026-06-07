"""
services/extraction_service.py — Phase 2: entity/relationship extraction.

For each text chunk, a structured prompt is sent to DeepSeek-chat requesting
entities as (name, type) pairs and relationships as (source, relation, target)
triples in JSON.  Chunks are processed in parallel via ThreadPoolExecutor.
All responses are validated with Pydantic models defined in services/__init__.py.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

from config import Settings
from services import ChunkDict, Entity, ExtractionResult, Relation

logger = logging.getLogger(__name__)

# ── Prompt template ───────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a knowledge-graph extraction engine.
Given a passage of text, you must extract:
1. Named entities — each with a "name" and a "type" (e.g. Person, Organization, Location,
   Concept, Technology, Event, Date, Product, or any appropriate category).
2. Relationships between those entities — each as a (source, relation, target) triple,
   where source and target are entity names you extracted.

Return ONLY valid JSON in the following schema — no prose, no markdown fences:
{
  "entities": [{"name": "...", "type": "..."}],
  "relations": [{"source": "...", "relation": "...", "target": "..."}]
}

Rules:
- entity names must match exactly between the "entities" list and relation source/target fields.
- If no entities or relations are found, return empty lists.
- Do NOT include any text outside the JSON object.
"""

_USER_TEMPLATE = "Extract entities and relationships from the following text:\n\n{text}"


class ExtractionService:
    """
    Phase 2 — chunks → entities / relations.

    Args:
        settings: Injected settings (DeepSeek credentials, parallelism, model).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )

    def extract(self, chunks: list[ChunkDict]) -> list[ExtractionResult]:
        """
        Run parallel entity/relation extraction over all chunks.

        Args:
            chunks: Output of Phase 1.

        Returns:
            List of ExtractionResult (one per chunk, preserving chunk_index).
        """
        results: list[ExtractionResult] = []

        with ThreadPoolExecutor(max_workers=self._settings.max_workers) as pool:
            future_to_chunk = {
                pool.submit(self._extract_chunk, chunk): chunk
                for chunk in chunks
            }
            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Extraction failed for chunk %d: %s",
                        chunk["chunk_index"],
                        exc,
                    )
                    # Append an empty result so downstream phases aren't blocked
                    results.append(
                        ExtractionResult(
                            chunk_index=chunk["chunk_index"],
                            entities=[],
                            relations=[],
                        )
                    )

        # Sort by chunk_index so output order is deterministic
        results.sort(key=lambda r: r.chunk_index)
        logger.info(
            "Phase 2 complete: extracted from %d chunks (%d entities, %d relations total)",
            len(results),
            sum(len(r.entities) for r in results),
            sum(len(r.relations) for r in results),
        )
        return results

    # ── private helpers ───────────────────────────────────────────────────────

    def _extract_chunk(self, chunk: ChunkDict) -> ExtractionResult:
        """Call DeepSeek for a single chunk and parse the JSON response."""
        response = self._client.chat.completions.create(
            model=self._settings.deepseek_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _USER_TEMPLATE.format(text=chunk["text"])},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"
        return self._parse_response(chunk["chunk_index"], raw)

    @staticmethod
    def _parse_response(chunk_index: int, raw: str) -> ExtractionResult:
        """Parse and validate the JSON response from the LLM."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Non-JSON response for chunk {chunk_index}: {exc}") from exc

        entities = [Entity(**e) for e in data.get("entities", [])]
        relations = [Relation(**r) for r in data.get("relations", [])]

        return ExtractionResult(
            chunk_index=chunk_index,
            entities=entities,
            relations=relations,
        )

"""
main.py — GraphRAG Pipeline Orchestrator.

Usage:
    python main.py [path/to/document.pdf ...]

If no arguments are given, the pipeline falls back to the hardcoded
DEFAULT_PDF path defined below.

Phases
------
1  Ingestion          PDF → text chunks
2  Extraction         chunks → entities / relations  (DeepSeek-chat, parallel)
3  Graph Write        entities + relations → Neo4j
4  Community Detect   Leiden via Neo4j GDS → community labels on nodes
5  Summarisation      communities → natural-language summaries (DeepSeek-chat)
6  Vector Store       summaries + chunks → Gemini embeddings → Qdrant
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env before importing anything that reads settings ──────────────────
load_dotenv()

from config import get_settings
from db import Neo4jClient, QdrantClientWrapper
from services.ingestion_service import IngestionService
from services.extraction_service import ExtractionService
from services.graph_write_service import GraphWriteService
from services.community_detection_service import CommunityDetectionService
from services.summary_service import SummaryService
from services.vector_store_service import VectorStoreService

# ── Default PDF (used when no CLI arg is provided) ───────────────────────────
DEFAULT_PDF = "sample.pdf"

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────

def _phase_banner(number: int, name: str) -> None:
    logger.info("=" * 60)
    logger.info("  PHASE %d — %s", number, name)
    logger.info("=" * 60)


def run_pipeline(pdf_paths: list[str]) -> None:
    settings = get_settings()

    # ── Validate inputs ───────────────────────────────────────────────────────
    valid_paths = [p for p in pdf_paths if Path(p).exists()]
    if not valid_paths:
        logger.error("No valid PDF paths supplied. Aborting.")
        sys.exit(1)
    logger.info("Processing %d PDF file(s): %s", len(valid_paths), valid_paths)

    # ── Instantiate DB wrappers (dependency-injected into services) ───────────
    neo4j_client = Neo4jClient(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
    qdrant_wrapper = QdrantClientWrapper(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )

    pipeline_start = time.perf_counter()

    try:
        # ── Phase 1 — Ingestion ───────────────────────────────────────────────
        _phase_banner(1, "Document Ingestion & Chunking")
        t0 = time.perf_counter()
        ingestion_svc = IngestionService(settings)
        chunks = ingestion_svc.ingest(valid_paths)
        logger.info("→ %d chunks in %.1fs", len(chunks), time.perf_counter() - t0)

        # ── Phase 2 — Extraction ──────────────────────────────────────────────
        _phase_banner(2, "Entity / Relationship Extraction")
        t0 = time.perf_counter()
        extraction_svc = ExtractionService(settings)
        extractions = extraction_svc.extract(chunks)
        logger.info("→ Extraction done in %.1fs", time.perf_counter() - t0)

        # ── Phase 3 — Graph Write ─────────────────────────────────────────────
        _phase_banner(3, "Neo4j Graph Write")
        t0 = time.perf_counter()
        graph_svc = GraphWriteService(neo4j_client)
        graph_svc.write(extractions, chunks)
        logger.info("→ Graph written in %.1fs", time.perf_counter() - t0)

        # ── Phase 4 — Community Detection ─────────────────────────────────────
        _phase_banner(4, "Community Detection (Leiden / GDS)")
        t0 = time.perf_counter()
        community_svc = CommunityDetectionService(neo4j_client)
        communities = community_svc.detect()
        logger.info(
            "→ %d communities detected in %.1fs",
            len(communities),
            time.perf_counter() - t0,
        )

        # ── Phase 5 — Community Summarisation ─────────────────────────────────
        _phase_banner(5, "Community Summary Generation")
        t0 = time.perf_counter()
        summary_svc = SummaryService(neo4j_client, settings)
        summaries = summary_svc.summarize(communities)
        logger.info(
            "→ %d summaries generated in %.1fs",
            len(summaries),
            time.perf_counter() - t0,
        )

        # ── Phase 6 — Vector Store ─────────────────────────────────────────────
        _phase_banner(6, "Vector Storage (Gemini Embeddings → Qdrant)")
        t0 = time.perf_counter()
        vector_svc = VectorStoreService(qdrant_wrapper, settings)
        vector_svc.embed_and_store(summaries, chunks)
        logger.info(
            "→ Qdrant upsert done in %.1fs",
            time.perf_counter() - t0,
        )

    finally:
        neo4j_client.close()
        qdrant_wrapper.close()

    # ── Done ──────────────────────────────────────────────────────────────────
    total = time.perf_counter() - pipeline_start
    logger.info("=" * 60)
    logger.info("  PIPELINE COMPLETE — total time: %.1fs", total)
    logger.info("  Qdrant collection '%s' is ready for queries.", settings.qdrant_collection)
    logger.info("=" * 60)


if __name__ == "__main__":
    pdf_args = sys.argv[1:] if len(sys.argv) > 1 else [DEFAULT_PDF]
    run_pipeline(pdf_args)

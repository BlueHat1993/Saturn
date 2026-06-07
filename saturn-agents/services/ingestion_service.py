"""
services/ingestion_service.py — Phase 1: PDF ingestion and chunking.

Loads one or more PDF files with pypdf, captures page-level text,
then splits into overlapping chunks via LangChain's
RecursiveCharacterTextSplitter.  Each chunk carries source, chunk_index,
and page_number metadata for downstream provenance tracking.
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from config import Settings
from services import ChunkDict

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Phase 1 — PDF → chunks.

    Args:
        settings: Injected application settings (chunk_size, chunk_overlap).
    """

    def __init__(self, settings: Settings) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            add_start_index=False,
        )

    def ingest(self, pdf_paths: list[str]) -> list[ChunkDict]:
        """
        Load all PDFs and return a flat list of text chunks with metadata.

        Args:
            pdf_paths: Absolute or relative paths to PDF files.

        Returns:
            List of ChunkDicts ordered by (source, chunk_index).
        """
        all_chunks: list[ChunkDict] = []
        global_chunk_index = 0

        for pdf_path in pdf_paths:
            path = Path(pdf_path)
            if not path.exists():
                logger.warning("PDF not found, skipping: %s", pdf_path)
                continue

            logger.info("Ingesting: %s", path.name)
            page_texts = self._extract_pages(path)

            for page_number, page_text in page_texts:
                if not page_text.strip():
                    continue

                raw_chunks = self._splitter.split_text(page_text)
                for raw_chunk in raw_chunks:
                    all_chunks.append(
                        ChunkDict(
                            text=raw_chunk,
                            source=str(path),
                            chunk_index=global_chunk_index,
                            page_number=page_number,
                        )
                    )
                    global_chunk_index += 1

        logger.info("Phase 1 complete: %d chunks from %d file(s)", len(all_chunks), len(pdf_paths))
        return all_chunks

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_pages(path: Path) -> list[tuple[int, str]]:
        """Return [(1-based page_number, page_text)] for every page in the PDF."""
        reader = PdfReader(str(path))
        results: list[tuple[int, str]] = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            results.append((i, text))
        return results

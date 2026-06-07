"""Run the Saturn agentic graph workflow sequentially from a normal Python script.

This runner calls the `decompose_node`, `neo4j_node`, `qdrant_node`, and
`synthesis_node` functions from `agents.saturn_graph` in sequence and logs the
state after each step. Running the nodes sequentially avoids concurrent graph
update issues seen when invoking the compiled graph in parallel.

Usage:
    python run_local_query.py --query "Who is related to Acme Corp?"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from agents.saturn_graph import (
    decompose_node,
    neo4j_node,
    qdrant_node,
    synthesis_node,
)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", "-q", required=True, help="User question")
    args = parser.parse_args(argv)

    configure_logging()
    logger = logging.getLogger("run_local_query")

    state = {"user_query": args.query}
    logger.info("Starting sequential Saturn Graph RAG run")
    logger.info("Initial state: %s", json.dumps(state))

    try:
        state = decompose_node(state)
        logger.info("After decompose_node: %s", json.dumps(state, indent=2))

        state = neo4j_node(state)
        logger.info("After neo4j_node: %s", json.dumps(state, indent=2))

        state = qdrant_node(state)
        logger.info("After qdrant_node: %s", json.dumps(state, indent=2))

        state = synthesis_node(state)
        logger.info("After synthesis_node: %s", json.dumps(state, indent=2))

        # print final JSON state to stdout for easy capture
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0

    except Exception:
        logger.exception("Error while running sequential graph workflow")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

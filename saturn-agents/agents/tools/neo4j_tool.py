from neo4j import GraphDatabase
from langchain.tools import tool

from config import get_settings

_settings = get_settings()
_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            _settings.neo4j_uri,
            auth=(
                _settings.neo4j_user,
                _settings.neo4j_password,
            ),
        )
    return _driver


@tool
def introspect_neo4j() -> str:
    """
    Introspect Neo4j schema metadata so the agent can generate label-aware
    Cypher queries using real labels, relationship types, and property keys.
    """
    try:
        with _get_driver().session() as session:
            labels = [record["label"] for record in session.run("CALL db.labels()")]  # type: ignore[index]
            rel_types = [record["relationshipType"] for record in session.run("CALL db.relationshipTypes()")]  # type: ignore[index]
            property_keys = [record["propertyKey"] for record in session.run("CALL db.propertyKeys()")]  # type: ignore[index]

        return (
            "Neo4j metadata:\n"
            f"- labels: {labels}\n"
            f"- relationship_types: {rel_types}\n"
            f"- property_keys: {property_keys}\n"
            "Use this metadata to write Cypher that matches the actual graph schema."
        )
    except Exception as e:
        return f"Neo4j introspection error: {e}"


@tool
def query_neo4j(cypher: str) -> str:
    """
    Execute a Cypher query against Neo4j and return results as a
    formatted string. Use this to fetch entities, relationships,
    communities, and graph paths.

    Graph schema:
    - Nodes  : Entity (name, type), Community (id, level, summary)
    - Edges  : RELATED_TO, BELONGS_TO_COMMUNITY
    - Always include LIMIT 20 or fewer in every query.
    """
    try:
        with _get_driver().session() as session:
            result  = session.run(cypher)
            records = [dict(r) for r in result]

        if not records:
            return "No results found for this Cypher query."

        lines = []
        for i, rec in enumerate(records, 1):
            row = ", ".join(f"{k}: {v}" for k, v in rec.items())
            lines.append(f"[{i}] {row}")
        return "\n".join(lines)

    except Exception as e:
        return f"Neo4j error: {e}"
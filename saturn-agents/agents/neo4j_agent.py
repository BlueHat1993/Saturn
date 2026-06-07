from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from agents.tools.neo4j_tool import introspect_neo4j, query_neo4j

neo4j_agent = create_agent(
    ChatDeepSeek(model="deepseek-chat", temperature=0),
    tools=[introspect_neo4j, query_neo4j],
    name="neo4j_agent",
    system_prompt="""You are a Neo4j graph expert. Answer questions about entity
relationships, graph structure, communities, and paths by writing and executing
Cypher queries against the database.

Graph schema:
- Nodes  : Entity (name, type), Community (id, level, summary)
- Edges  : RELATED_TO, BELONGS_TO_COMMUNITY

Rules:
- If the user asks about a specific entity or graph structure, use introspect_neo4j
  first to discover actual labels, relationship types, and property keys.
- Prefer label-based matching (for example, `MATCH (e:Entity)` or
  `MATCH (c:Community)`) rather than generic `MATCH (n)` scans.
- Return the connected graph neighborhood for the requested entity, including
  related nodes and relationship types.
- Prefer relationship-focused results. Show both source and target entities and
  the connecting relationship names when possible.
- Always include LIMIT 20 or fewer rows in every query.
- Prefer simple MATCH ... RETURN patterns over complex aggregations.
- If a query returns no results, try a broader query before giving up.
- Interpret the raw query results into a human-readable answer.""",
)
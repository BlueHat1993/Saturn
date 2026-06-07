from typing import TypedDict


class GraphRAGState(TypedDict):
    user_query:        str
    graph_question:    str   # sub-question routed to Neo4j Agent
    semantic_question: str   # sub-question routed to Qdrant Agent
    graph_result:      str   # structured output from Neo4j Agent
    semantic_result:   str   # prose output from Qdrant Agent
    final_answer:      str   # synthesised final answer
    error:             str   # any error surfaced during the run
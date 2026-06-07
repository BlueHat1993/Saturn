from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage

from .state import GraphRAGState
from .neo4j_agent import neo4j_agent
from .qdrant_agent import qdrant_agent

# ── shared LLM for decompose + synthesis (no tools needed) ────────────────────
_llm = ChatDeepSeek(model="deepseek-chat", temperature=0.2)


# ── decompose agent ────────────────────────────────────────────────────────────
_decompose_agent = create_agent(
    ChatDeepSeek(model="deepseek-chat", temperature=0),
    tools=[],
    name="decompose_agent",
    system_prompt="""You decompose a user query into exactly two focused sub-questions.

Respond in this EXACT format with no extra text, preamble, or explanation:
GRAPH: <question about entities, relationships, connections, or communities — answerable by Cypher on Neo4j>
SEMANTIC: <question about meaning, context, summaries, or explanations — answerable by vector search on Qdrant>""",
)


# ── synthesis agent ────────────────────────────────────────────────────────────
_synthesis_agent = create_agent(
    _llm,
    tools=[],
    name="synthesis_agent",
    system_prompt="""You are a synthesis agent. You receive two context sources:

GRAPH CONTEXT   — structured data about entity relationships and communities from Neo4j
SEMANTIC CONTEXT — relevant document summaries and chunks from a vector store (Qdrant)

Your job is to merge both into a single coherent, grounded answer.
- Use graph context to establish structure, connections, and entity relationships
- Use semantic context to provide explanation, detail, and narrative
- If the two sources conflict, prefer graph context for structural facts
  and semantic context for interpretation
- Be concise but complete
- Never hallucinate beyond what is provided in the two contexts""",
)


# ══════════════════════════════════════════════════════════════════════════════
# NODE 1 — decompose
# Splits the user query into a graph sub-question and a semantic sub-question
# ══════════════════════════════════════════════════════════════════════════════
def decompose_node(state: GraphRAGState) -> GraphRAGState:
    try:
        result = _decompose_agent.invoke(
            {"messages": [HumanMessage(content=state["user_query"])]}
        )
        text = result["messages"][-1].content.strip()

        graph_q, semantic_q = "", ""
        for line in text.splitlines():
            if line.startswith("GRAPH:"):
                graph_q    = line.replace("GRAPH:", "").strip()
            elif line.startswith("SEMANTIC:"):
                semantic_q = line.replace("SEMANTIC:", "").strip()

        # fallback — if parsing fails, use the original query for both
        return {
            **state,
            "graph_question":    graph_q    or state["user_query"],
            "semantic_question": semantic_q or state["user_query"],
        }
    except Exception as e:
        return {
            **state,
            "graph_question":    state["user_query"],
            "semantic_question": state["user_query"],
            "error": f"Decompose error: {e}",
        }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 2a — neo4j agent
# Answers the graph sub-question by generating + executing Cypher queries
# ══════════════════════════════════════════════════════════════════════════════
def neo4j_node(state: GraphRAGState) -> GraphRAGState:
    try:
        result = neo4j_agent.invoke(
            {"messages": [HumanMessage(content=state["graph_question"])]}
        )
        return {**state, "graph_result": result["messages"][-1].content}
    except Exception as e:
        return {**state, "graph_result": f"Neo4j Agent error: {e}"}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 2b — qdrant agent
# Answers the semantic sub-question via vector search with level filtering
# ══════════════════════════════════════════════════════════════════════════════
def qdrant_node(state: GraphRAGState) -> GraphRAGState:
    try:
        result = qdrant_agent.invoke(
            {"messages": [HumanMessage(content=state["semantic_question"])]}
        )
        return {**state, "semantic_result": result["messages"][-1].content}
    except Exception as e:
        return {**state, "semantic_result": f"Qdrant Agent error: {e}"}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 3 — synthesis
# Merges graph structure + semantic context into one final grounded answer
# ══════════════════════════════════════════════════════════════════════════════
def synthesis_node(state: GraphRAGState) -> GraphRAGState:
    prompt = f"""Original question: {state["user_query"]}

GRAPH CONTEXT (from Neo4j):
{state["graph_result"]}

SEMANTIC CONTEXT (from Qdrant):
{state["semantic_result"]}

Synthesise a final answer:"""

    try:
        result = _synthesis_agent.invoke(
            {"messages": [HumanMessage(content=prompt)]}
        )
        return {**state, "final_answer": result["messages"][-1].content.strip()}
    except Exception as e:
        return {**state, "final_answer": f"Synthesis error: {e}"}


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH ASSEMBLY
# decompose → [neo4j_agent ‖ qdrant_agent] → synthesis → END
# ══════════════════════════════════════════════════════════════════════════════
def build_graph() -> any:
    g = StateGraph(GraphRAGState)

    g.add_node("decompose",    decompose_node)
    g.add_node("neo4j_agent",  neo4j_node)
    g.add_node("qdrant_agent", qdrant_node)
    g.add_node("synthesis",    synthesis_node)

    g.set_entry_point("decompose")

    # fan-out: decompose fires both agents in parallel
    g.add_edge("decompose",    "neo4j_agent")
    g.add_edge("decompose",    "qdrant_agent")

    # fan-in: synthesis waits for both agents to complete
    g.add_edge("neo4j_agent",  "synthesis")
    g.add_edge("qdrant_agent", "synthesis")

    g.add_edge("synthesis", END)

    return g.compile()


graph_rag_app = build_graph()
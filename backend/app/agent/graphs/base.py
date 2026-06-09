"""Built-in LangGraph graph builders."""
from langgraph.graph import END, StateGraph

from app.agent.state import AgentState


def _pass_node(state: AgentState) -> AgentState:
    return state


def build_linear_graph(nodes: list[str]):
    graph = StateGraph(AgentState)
    for node in nodes:
        graph.add_node(node, _pass_node)
    graph.set_entry_point(nodes[0])
    for current_node, next_node in zip(nodes, nodes[1:]):
        graph.add_edge(current_node, next_node)
    graph.add_edge(nodes[-1], END)
    return graph.compile()

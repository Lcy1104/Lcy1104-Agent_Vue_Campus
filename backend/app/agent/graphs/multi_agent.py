"""Multi-agent collaboration built-in graph."""
from app.agent.graphs.base import build_linear_graph


def build_graph():
    return build_linear_graph(["analyst", "executor", "validator", "final"])

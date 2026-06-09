"""Shared LangGraph agent state definitions."""
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    strategy_name: str
    selected_model_id: str | None
    tool_results: list[dict[str, Any]]
    final_answer: str

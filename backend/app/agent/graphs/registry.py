"""Built-in LangGraph strategy registry."""

BUILTIN_AGENT_STRATEGIES = {
    "react": {
        "display_name": "ReAct 模式",
        "description": "适合工具调用型问答，先由 Agent 判断行动，再调用知识库工具观察，最后生成答案。",
        "graph_nodes": ["agent", "tools", "final"],
        "graph_edges": ["agent -> tools", "tools -> final"],
        "configurable_models": ["agent"],
    },
    "plan_execute": {
        "display_name": "Plan-Execute 模式",
        "description": "先规划任务步骤，再逐步执行并汇总结果，适合复杂查询和多步骤任务。",
        "graph_nodes": ["planner", "executor", "validator", "final"],
        "graph_edges": ["planner -> executor", "executor -> validator", "validator -> final"],
        "configurable_models": ["planner", "executor", "validator"],
    },
    "multi_agent": {
        "display_name": "多 Agent 协作模式",
        "description": "分析、执行、校验三个子图协同工作，各子图可绑定不同模型。",
        "graph_nodes": ["analyst", "executor", "validator", "final"],
        "graph_edges": ["analyst -> executor", "executor -> validator", "validator -> final"],
        "configurable_models": ["analyst", "executor", "validator"],
    },
}


def get_strategy_metadata(strategy_name: str) -> dict:
    return BUILTIN_AGENT_STRATEGIES[strategy_name]


def list_strategy_metadata() -> list[dict]:
    return [
        {"strategy_name": strategy_name, **metadata}
        for strategy_name, metadata in BUILTIN_AGENT_STRATEGIES.items()
    ]

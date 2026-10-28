"""
Intelligent Agent Router built with LangGraph.
Uses Task Analysis to classify business intent, conditionally routes to specialized agents,
supports agent chaining and shared state, and validates outputs with Pydantic.
"""

from typing import Any, Callable, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END

from app.schemas.ai import TaskAnalysisResult
from app.schemas.agent import (
    ResearchAgentResult,
    ContentGenerationResult,
    DataAnalysisResult,
    ReportingResult,
)
from app.agents.task_analyzer import run_task_analysis_agent
from app.agents.specialized.research_agent import run_research_agent
from app.agents.specialized.content_agent import run_content_agent
from app.agents.specialized.data_agent import run_data_agent
from app.agents.specialized.reporting_agent import run_reporting_agent


# ── Shared State Schema ───────────────────────────────────────────────────────

class MultiAgentState(TypedDict):
    task_description: str
    data_input: Optional[str]
    context: Optional[Dict[str, Any]]
    agent_override: Optional[str]
    tone: Optional[str]
    task_analysis: Optional[TaskAnalysisResult]
    selected_agent: Optional[str]
    routing_reasoning: Optional[str]
    agent_output: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_log: List[str]
    _llm_callable: Optional[Callable]


# ── LangGraph Nodes ──────────────────────────────────────────────────────────

async def analyze_and_route_node(state: MultiAgentState) -> Dict[str, Any]:
    """
    Evaluates the task using the Task Analysis Agent and determines the target specialized agent.
    Respects manual agent_override if provided.
    """
    logs = list(state.get("execution_log", []))
    task_desc = (state.get("task_description") or "").strip()

    if len(task_desc) < 3:
        return {
            "error": "Task description is too short (minimum 3 characters required).",
            "execution_log": logs + ["router_failed_short_input"],
        }

    override = state.get("agent_override")
    llm_callable = state.get("_llm_callable")

    # If user explicitly overrode the agent selection
    if override in ("research", "content_generation", "data_analysis", "reporting"):
        return {
            "selected_agent": override,
            "routing_reasoning": f"Manually overridden by user request to '{override}'.",
            "execution_log": logs + [f"router_manual_override:{override}"],
        }

    try:
        # Run Task Analysis Agent to classify category and intent
        analysis: TaskAnalysisResult = await run_task_analysis_agent(
            task_description=task_desc,
            context=state.get("context"),
            llm_callable=llm_callable,
        )

        cat = analysis.category
        has_data = bool(state.get("data_input"))

        # Map task category to specialized agent
        if cat == "data_analysis" or (has_data and cat not in ("content_generation", "reporting")):
            selected = "data_analysis"
            reason = f"Classified as data analysis: {analysis.explanation}"
        elif cat == "content_generation":
            selected = "content_generation"
            reason = f"Classified as content generation: {analysis.explanation}"
        elif cat == "reporting":
            selected = "reporting"
            reason = f"Classified as enterprise reporting: {analysis.explanation}"
        elif cat == "research":
            selected = "research"
            reason = f"Classified as research and fact discovery: {analysis.explanation}"
        else:
            # Fallback for 'general'
            lower_desc = task_desc.lower()
            if any(w in lower_desc for w in ("report", "summary", "briefing")):
                selected = "reporting"
            elif any(w in lower_desc for w in ("write", "email", "draft", "post")):
                selected = "content_generation"
            elif any(w in lower_desc for w in ("data", "csv", "metric", "trend", "chart")):
                selected = "data_analysis"
            else:
                selected = "research"
            reason = f"General domain defaulted to {selected} based on task intent."

        return {
            "task_analysis": analysis,
            "selected_agent": selected,
            "routing_reasoning": reason,
            "execution_log": logs + [f"routed_to:{selected}"],
        }
    except Exception as exc:
        return {
            "error": f"Task analysis and routing failed: {str(exc)}",
            "execution_log": logs + [f"routing_failed:{type(exc).__name__}"],
        }


async def research_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """Executes the specialized Research Agent."""
    logs = list(state.get("execution_log", []))
    try:
        result = await run_research_agent(
            task_description=state["task_description"],
            context=state.get("context"),
            data_input=state.get("data_input"),
            llm_callable=state.get("_llm_callable"),
        )
        return {
            "agent_output": result.model_dump(),
            "execution_log": logs + ["research_agent_success"],
        }
    except Exception as exc:
        return {
            "error": f"Research agent failed: {str(exc)}",
            "execution_log": logs + [f"research_failed:{type(exc).__name__}"],
        }


async def content_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """Executes the specialized Content Generation Agent."""
    logs = list(state.get("execution_log", []))
    try:
        result = await run_content_agent(
            task_description=state["task_description"],
            tone=state.get("tone"),
            context=state.get("context"),
            data_input=state.get("data_input"),
            llm_callable=state.get("_llm_callable"),
        )
        return {
            "agent_output": result.model_dump(),
            "execution_log": logs + ["content_agent_success"],
        }
    except Exception as exc:
        return {
            "error": f"Content generation agent failed: {str(exc)}",
            "execution_log": logs + [f"content_failed:{type(exc).__name__}"],
        }


async def data_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """Executes the specialized Data Analysis Agent."""
    logs = list(state.get("execution_log", []))
    try:
        result = await run_data_agent(
            task_description=state["task_description"],
            data_input=state.get("data_input"),
            context=state.get("context"),
            llm_callable=state.get("_llm_callable"),
        )
        return {
            "agent_output": result.model_dump(),
            "execution_log": logs + ["data_agent_success"],
        }
    except Exception as exc:
        return {
            "error": f"Data analysis agent failed: {str(exc)}",
            "execution_log": logs + [f"data_failed:{type(exc).__name__}"],
        }


async def reporting_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """Executes the specialized Reporting Agent."""
    logs = list(state.get("execution_log", []))
    try:
        result = await run_reporting_agent(
            task_description=state["task_description"],
            context=state.get("context"),
            data_input=state.get("data_input"),
            prior_agent_output=state.get("agent_output"),
            llm_callable=state.get("_llm_callable"),
        )
        return {
            "agent_output": result.model_dump(),
            "execution_log": logs + ["reporting_agent_success"],
        }
    except Exception as exc:
        return {
            "error": f"Reporting agent failed: {str(exc)}",
            "execution_log": logs + [f"reporting_failed:{type(exc).__name__}"],
        }


def validate_and_finalize_node(state: MultiAgentState) -> Dict[str, Any]:
    """
    Validates output data against the expected Pydantic schema for the chosen agent.
    """
    logs = list(state.get("execution_log", []))
    selected = state.get("selected_agent")
    raw_output = state.get("agent_output")

    if not raw_output:
        return {
            "error": state.get("error") or "Agent finished without producing output.",
            "execution_log": logs + ["validation_missing_output"],
        }

    try:
        if selected == "research":
            validated = ResearchAgentResult(**raw_output)
        elif selected == "content_generation":
            validated = ContentGenerationResult(**raw_output)
        elif selected == "data_analysis":
            validated = DataAnalysisResult(**raw_output)
        elif selected == "reporting":
            validated = ReportingResult(**raw_output)
        else:
            validated = raw_output

        return {
            "agent_output": validated.model_dump() if hasattr(validated, "model_dump") else validated,
            "execution_log": logs + ["pydantic_schema_validated"],
        }
    except Exception as exc:
        return {
            "error": f"Pydantic validation failed for {selected} output: {str(exc)}",
            "execution_log": logs + ["pydantic_validation_error"],
        }


def error_handler_node(state: MultiAgentState) -> Dict[str, Any]:
    """Terminal error node for multi-agent execution."""
    logs = list(state.get("execution_log", []))
    return {
        "execution_log": logs + ["multi_agent_terminated_with_error"],
    }


# ── Conditional Routing Functions ────────────────────────────────────────────

def route_after_analysis(state: MultiAgentState) -> str:
    if state.get("error"):
        return "error"
    selected = state.get("selected_agent")
    if selected in ("research", "content_generation", "data_analysis", "reporting"):
        return selected
    return "error"


def route_after_agent_execution(state: MultiAgentState) -> str:
    if state.get("error"):
        return "error"
    return "validate_and_finalize"


# ── StateGraph Construction ──────────────────────────────────────────────────

def build_multi_agent_router_graph():
    """Constructs and compiles the Multi-Agent Router StateGraph."""
    graph = StateGraph(MultiAgentState)

    # 1. Register Nodes
    graph.add_node("analyze_and_route", analyze_and_route_node)
    graph.add_node("research", research_agent_node)
    graph.add_node("content_generation", content_agent_node)
    graph.add_node("data_analysis", data_agent_node)
    graph.add_node("reporting", reporting_agent_node)
    graph.add_node("validate_and_finalize", validate_and_finalize_node)
    graph.add_node("error_handler", error_handler_node)

    # 2. Flow Edges
    graph.add_edge(START, "analyze_and_route")

    graph.add_conditional_edges(
        "analyze_and_route",
        route_after_analysis,
        {
            "research": "research",
            "content_generation": "content_generation",
            "data_analysis": "data_analysis",
            "reporting": "reporting",
            "error": "error_handler",
        },
    )

    for agent_node in ("research", "content_generation", "data_analysis", "reporting"):
        graph.add_conditional_edges(
            agent_node,
            route_after_agent_execution,
            {
                "validate_and_finalize": "validate_and_finalize",
                "error": "error_handler",
            },
        )

    graph.add_edge("validate_and_finalize", END)
    graph.add_edge("error_handler", END)

    return graph.compile()


multi_agent_router = build_multi_agent_router_graph()


# ── Public Runner ────────────────────────────────────────────────────────────

async def run_intelligent_router(
    task_description: str,
    data_input: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    agent_override: Optional[str] = None,
    tone: Optional[str] = None,
    llm_callable: Optional[Callable] = None,
) -> MultiAgentState:
    """
    Executes the Multi-Agent Intelligent Router against an incoming task request.
    """
    initial_state: MultiAgentState = {
        "task_description": task_description,
        "data_input": data_input,
        "context": context,
        "agent_override": agent_override,
        "tone": tone,
        "task_analysis": None,
        "selected_agent": None,
        "routing_reasoning": None,
        "agent_output": None,
        "error": None,
        "execution_log": ["router_started"],
        "_llm_callable": llm_callable,
    }

    final_state = await multi_agent_router.ainvoke(initial_state)

    if final_state.get("error"):
        raise ValueError(final_state["error"])

    return final_state

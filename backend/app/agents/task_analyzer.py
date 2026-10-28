"""
Intelligent Task Analysis Agent built with LangGraph and Google Gemini.

Architecture:
- Defined State schema (TaskAnalysisState)
- Sequential and conditional execution nodes:
  1. validate_and_prepare: Validates task prompt & constraints
  2. analyze_with_llm: Invokes Gemini API via official SDK with structured JSON mode
  3. parse_and_validate: Enforces Pydantic schema validation
  4. enrich_recommendations: Enhances subtasks & recommendations
  5. error_handler: Gracefully captures and formats failures
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END

from app.schemas.ai import TaskAnalysisResult
from app.services import gemini_service


# ── System Instruction for Gemini ─────────────────────────────────────────────

TASK_ANALYZER_SYSTEM_INSTRUCTION = """
You are an expert Enterprise AI Workflow Architect and Task Analysis Engine.
Your responsibility is to analyze business tasks, infer the underlying intent, categorize them, assess priority and complexity, and recommend concrete execution steps.

You MUST respond strictly with a valid JSON object matching the following structure:
{
  "task_intent": "Clear 1-2 sentence description of user's core intent and business objective",
  "category": "one of: research | reporting | content_generation | data_analysis | general",
  "priority": "one of: low | medium | high | critical",
  "complexity": "one of: simple | moderate | complex",
  "recommended_action": "Specific recommended next action or automated agent pipeline to execute",
  "explanation": "Concise 1-3 sentence rationale justifying your classification and recommendation",
  "suggested_subtasks": [
    "Subtask step 1",
    "Subtask step 2",
    "Subtask step 3"
  ]
}

Classification Criteria:
- Category:
  * research: Information gathering, competitor discovery, literature lookup, market investigation.
  * reporting: Summaries, KPI dashboards, status updates, periodic performance reports.
  * content_generation: Writing articles, emails, marketing copy, social posts, drafting documents.
  * data_analysis: Statistical processing, metrics calculation, churn analysis, numerical interpretation.
  * general: Any task not clearly fitting the above domains.
- Priority:
  * critical: Urgent customer escalations, security incidents, blocker decisions.
  * high: Direct impact on revenue, executive deliverables, timely deadlines.
  * medium: Standard daily business operations, recurring improvements.
  * low: Nice-to-have, backlog ideas, background optimization.
- Complexity:
  * simple: Single step, minimal ambiguity, straightforward execution.
  * moderate: 2-4 steps requiring data transformation, basic reasoning, or synthesis.
  * complex: Multi-step, cross-domain dependencies, extensive research, or large datasets.
"""


# ── Agent State Definition ───────────────────────────────────────────────────

class TaskAnalysisState(TypedDict):
    task_description: str
    context: Optional[Dict[str, Any]]
    normalized_prompt: Optional[str]
    raw_llm_response: Optional[str]
    parsed_json: Optional[Dict[str, Any]]
    analysis_result: Optional[TaskAnalysisResult]
    error: Optional[str]
    execution_log: List[str]
    # Injected LLM callable for testing and modularity
    _llm_callable: Optional[Callable]


# ── LangGraph Nodes ──────────────────────────────────────────────────────────

def validate_and_prepare_node(state: TaskAnalysisState) -> Dict[str, Any]:
    """Validates input description length and prepares the LLM prompt."""
    logs = list(state.get("execution_log", []))
    task_desc = (state.get("task_description") or "").strip()

    if len(task_desc) < 3:
        return {
            "error": "Task description is too short (minimum 3 characters required).",
            "execution_log": logs + ["validation_failed_length_too_short"],
        }

    context_str = ""
    if state.get("context"):
        context_str = f"\nAdditional Context:\n{json.dumps(state['context'], indent=2)}"

    prompt = f"Please analyze this business task:\n\nTask:\n{task_desc}{context_str}"

    return {
        "normalized_prompt": prompt,
        "execution_log": logs + ["input_validated_and_prepared"],
    }


async def analyze_with_llm_node(state: TaskAnalysisState) -> Dict[str, Any]:
    """Calls the Gemini API (or injected callable) to generate structured analysis."""
    logs = list(state.get("execution_log", []))
    prompt = state["normalized_prompt"]
    llm_callable = state.get("_llm_callable")

    try:
        if llm_callable:
            # Used in unit tests and mocks
            raw_text = await llm_callable(prompt)
        else:
            raw_text = await gemini_service.generate_async(
                prompt=prompt,
                system_instruction=TASK_ANALYZER_SYSTEM_INSTRUCTION,
            )

        return {
            "raw_llm_response": raw_text,
            "execution_log": logs + ["llm_analysis_generated"],
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "execution_log": logs + [f"llm_call_failed: {type(exc).__name__}"],
        }


def parse_and_validate_node(state: TaskAnalysisState) -> Dict[str, Any]:
    """Parses JSON response and validates against Pydantic TaskAnalysisResult schema."""
    logs = list(state.get("execution_log", []))
    raw_text = state.get("raw_llm_response", "").strip()

    # Clean markdown code blocks if model wrapped JSON in ```json ... ```
    cleaned_text = raw_text
    if cleaned_text.startswith("```"):
        cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

    try:
        data = json.loads(cleaned_text)
    except json.JSONDecodeError as exc:
        return {
            "error": f"Failed to parse LLM output as JSON: {str(exc)}",
            "execution_log": logs + ["json_decode_failed"],
        }

    try:
        # Validate through Pydantic
        analysis = TaskAnalysisResult(**data)
        return {
            "parsed_json": data,
            "analysis_result": analysis,
            "execution_log": logs + ["pydantic_validation_success"],
        }
    except Exception as exc:
        return {
            "error": f"Pydantic validation failed for task analysis: {str(exc)}",
            "execution_log": logs + ["pydantic_validation_failed"],
        }


def enrich_recommendations_node(state: TaskAnalysisState) -> Dict[str, Any]:
    """Enriches the analysis with validated subtasks if list is empty."""
    logs = list(state.get("execution_log", []))
    result = state["analysis_result"]

    # Guarantee at least one actionable subtask
    subtasks = list(result.suggested_subtasks or [])
    if not subtasks:
        subtasks = [result.recommended_action]

    enriched_result = result.model_copy(update={"suggested_subtasks": subtasks})

    return {
        "analysis_result": enriched_result,
        "execution_log": logs + ["analysis_enriched"],
    }


def error_handler_node(state: TaskAnalysisState) -> Dict[str, Any]:
    """Terminal error-handling node that logs failure state."""
    logs = list(state.get("execution_log", []))
    return {
        "execution_log": logs + ["agent_terminated_with_error"],
    }


# ── Conditional Routing Functions ────────────────────────────────────────────

def route_after_validation(state: TaskAnalysisState) -> str:
    return "error" if state.get("error") else "analyze_with_llm"


def route_after_llm(state: TaskAnalysisState) -> str:
    return "error" if state.get("error") else "parse_and_validate"


def route_after_parse(state: TaskAnalysisState) -> str:
    return "error" if state.get("error") else "enrich_recommendations"


# ── Build the LangGraph StateGraph ────────────────────────────────────────────

def create_task_analyzer_graph():
    """Constructs and compiles the Task Analysis StateGraph."""
    graph = StateGraph(TaskAnalysisState)

    # Register Nodes
    graph.add_node("validate_and_prepare", validate_and_prepare_node)
    graph.add_node("analyze_with_llm", analyze_with_llm_node)
    graph.add_node("parse_and_validate", parse_and_validate_node)
    graph.add_node("enrich_recommendations", enrich_recommendations_node)
    graph.add_node("error_handler", error_handler_node)

    # Register Flow Edges
    graph.add_edge(START, "validate_and_prepare")
    graph.add_conditional_edges(
        "validate_and_prepare",
        route_after_validation,
        {"analyze_with_llm": "analyze_with_llm", "error": "error_handler"},
    )
    graph.add_conditional_edges(
        "analyze_with_llm",
        route_after_llm,
        {"parse_and_validate": "parse_and_validate", "error": "error_handler"},
    )
    graph.add_conditional_edges(
        "parse_and_validate",
        route_after_parse,
        {"enrich_recommendations": "enrich_recommendations", "error": "error_handler"},
    )
    graph.add_edge("enrich_recommendations", END)
    graph.add_edge("error_handler", END)

    return graph.compile()


# Singleton compiled graph
task_analyzer_agent = create_task_analyzer_graph()


# ── Public Runner Interface ──────────────────────────────────────────────────

async def run_task_analysis_agent(
    task_description: str,
    context: Optional[Dict[str, Any]] = None,
    llm_callable: Optional[Callable] = None,
) -> TaskAnalysisResult:
    """
    Executes the Task Analysis LangGraph agent against an input business task.

    :param task_description: User-provided description of the business task.
    :param context: Optional dictionary of domain or business context.
    :param llm_callable: Optional mock callable to substitute Gemini in tests.
    :returns: Validated TaskAnalysisResult.
    :raises: ValueError or appropriate domain error if execution fails.
    """
    initial_state: TaskAnalysisState = {
        "task_description": task_description,
        "context": context,
        "normalized_prompt": None,
        "raw_llm_response": None,
        "parsed_json": None,
        "analysis_result": None,
        "error": None,
        "execution_log": ["agent_started"],
        "_llm_callable": llm_callable,
    }

    final_state = await task_analyzer_agent.ainvoke(initial_state)

    if final_state.get("error"):
        raise ValueError(final_state["error"])

    if not final_state.get("analysis_result"):
        raise ValueError("Agent completed without producing an analysis result.")

    return final_state["analysis_result"]

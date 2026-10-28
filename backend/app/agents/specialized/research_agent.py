"""
Specialized Research Agent.
Analyzes research questions, synthesizes supplied context, extracts verified facts,
and provides AI-derived projections clearly distinguished from supplied facts.
"""

import json
import re
from typing import Any, Callable, Dict, Optional

from app.schemas.agent import ResearchAgentResult
from app.services import gemini_service

RESEARCH_AGENT_SYSTEM_INSTRUCTION = """
You are an Enterprise Research AI Agent specialized in deep synthesis, fact extraction, and objective analysis.
Your purpose is to thoroughly examine research questions, extract verified facts from user-provided context, and provide insightful, forward-looking strategic projections.

CRITICAL INSTRUCTIONS:
1. Strict Separation of Facts vs. AI Projections:
   - "verified_facts": MUST ONLY contain concrete factual statements directly extractable or cited from the user-provided prompt and context.
   - "ai_insights_and_projections": Place all hypotheses, extrapolations, market trends, or AI recommendations here. Clearly label them as inferences or projections.
   - Never claim external real-time web crawling unless explicitly supported by provided context citations.
2. Return strictly a JSON object with this exact structure:
{
  "topic": "Clear research subject or question",
  "executive_summary": "Concise 2-4 sentence briefing of overall research conclusions",
  "key_findings": [
    "Core takeaway 1",
    "Core takeaway 2",
    "Core takeaway 3"
  ],
  "verified_facts": [
    "Fact 1 explicitly derived from user context",
    "Fact 2 explicitly derived from user context"
  ],
  "ai_insights_and_projections": [
    "Forward-looking strategic projection 1",
    "Market or technical hypothesis 2"
  ],
  "sources_or_references": [
    "User context / internal document reference 1",
    "Domain reference 2"
  ]
}
"""


async def run_research_agent(
    task_description: str,
    context: Optional[Dict[str, Any]] = None,
    data_input: Optional[str] = None,
    llm_callable: Optional[Callable] = None,
) -> ResearchAgentResult:
    """
    Executes the Research Agent.
    """
    context_str = ""
    if context:
        context_str += f"\nProvided Context:\n{json.dumps(context, indent=2)}"
    if data_input:
        context_str += f"\nAttached Research Data / Reference:\n{data_input}"

    prompt = f"Conduct rigorous research analysis on the following requirement:\n\nTask:\n{task_description}{context_str}"

    if llm_callable:
        raw_text = await llm_callable(prompt)
    else:
        raw_text = await gemini_service.generate_async(
            prompt=prompt,
            system_instruction=RESEARCH_AGENT_SYSTEM_INSTRUCTION,
        )

    # Clean markdown formatting if present
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    data = json.loads(cleaned)
    return ResearchAgentResult(**data)

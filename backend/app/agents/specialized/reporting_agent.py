"""
Specialized Reporting Agent.
Synthesizes task outputs, multi-agent findings, and business metrics into structured,
executive-ready reports with findings, detailed analyses, and strategic next steps.
"""

import json
import re
from typing import Any, Callable, Dict, Optional

from app.schemas.agent import ReportingResult
from app.services import gemini_service

REPORTING_AGENT_SYSTEM_INSTRUCTION = """
You are an Enterprise Reporting AI Agent.
Your responsibility is to synthesize raw findings, data analyses, research outputs, and operational tasks into formal, high-impact enterprise reports for stakeholders and executives.

Format:
Return strictly a valid JSON object matching this structure:
{
  "report_title": "Clear, professional enterprise report title",
  "executive_summary": "High-level briefing summarizing the primary context, outcomes, and business impact in 2-4 sentences",
  "key_findings": [
    "Core finding 1 with strategic significance",
    "Core finding 2 with strategic significance",
    "Core finding 3 with strategic significance"
  ],
  "detailed_analysis": "Comprehensive section-by-section breakdown formatted in clean markdown (with headings, bullet points, and data callouts)",
  "strategic_recommendations": [
    "Prioritized strategic recommendation 1",
    "Prioritized strategic recommendation 2"
  ],
  "next_steps": [
    "Tactical milestone 1 for next sprint/cycle",
    "Tactical milestone 2 for next sprint/cycle"
  ]
}
"""


async def run_reporting_agent(
    task_description: str,
    context: Optional[Dict[str, Any]] = None,
    data_input: Optional[str] = None,
    prior_agent_output: Optional[Dict[str, Any]] = None,
    llm_callable: Optional[Callable] = None,
) -> ReportingResult:
    """
    Executes the Reporting Agent.
    """
    context_str = ""
    if context:
        context_str += f"\nSupplemental Context:\n{json.dumps(context, indent=2)}"
    if data_input:
        context_str += f"\nAttached Data / Metrics:\n{data_input}"
    if prior_agent_output:
        context_str += f"\nInputs from Preceding Agent Phase:\n{json.dumps(prior_agent_output, indent=2)}"

    prompt = (
        f"Generate a formal, publication-ready enterprise report based on this briefing:\n\n"
        f"Task:\n{task_description}{context_str}"
    )

    if llm_callable:
        raw_text = await llm_callable(prompt)
    else:
        raw_text = await gemini_service.generate_async(
            prompt=prompt,
            system_instruction=REPORTING_AGENT_SYSTEM_INSTRUCTION,
            temperature=0.2,
        )

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    data = json.loads(cleaned)
    return ReportingResult(**data)

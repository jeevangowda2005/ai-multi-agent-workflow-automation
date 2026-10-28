"""
Specialized Content Generation Agent.
Generates professional emails, articles, social media copy, business descriptions,
and corporate announcements across configurable writing tones.
"""

import json
import re
from typing import Any, Callable, Dict, Optional

from app.schemas.agent import ContentGenerationResult
from app.services import gemini_service

CONTENT_AGENT_SYSTEM_INSTRUCTION = """
You are an Enterprise Content Generation AI Agent.
Your responsibility is to craft high-impact, professional copy for business communications, including emails, blog articles, social media posts, corporate announcements, and product descriptions.

Tone Guidance:
- professional: Polished, corporate, objective, courteous, standard enterprise tone.
- executive: Authoritative, strategic, high-level, decisive, leadership-oriented.
- persuasive: Compelling, benefit-driven, conversion-focused, inspiring action.
- casual: Approachable, friendly, conversational, engaging yet respectful.
- concise: Direct, bulleted, minimal fluff, action-first.

Format:
Return strictly a valid JSON object matching this structure:
{
  "content_type": "one of: email | article | social_media_post | business_description | announcement",
  "tone_used": "one of: professional | casual | persuasive | executive | concise",
  "title": "Compelling title, headline, or email subject line",
  "body": "Complete formatted body in clean markdown (paragraphs, lists, headings where appropriate)",
  "alternative_headlines_or_hooks": [
    "Alternative 1",
    "Alternative 2"
  ],
  "call_to_action": "Clear single next action requested from reader",
  "target_audience": "Profile of intended audience"
}
"""


async def run_content_agent(
    task_description: str,
    tone: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    data_input: Optional[str] = None,
    llm_callable: Optional[Callable] = None,
) -> ContentGenerationResult:
    """
    Executes the Content Generation Agent.
    """
    tone_spec = f"\nRequested Tone: {tone}" if tone else "\nRequested Tone: professional (default)"
    context_str = ""
    if context:
        context_str += f"\nSupplemental Context:\n{json.dumps(context, indent=2)}"
    if data_input:
        context_str += f"\nSource Material / Key Points:\n{data_input}"

    prompt = (
        f"Generate structured business content based on the following instructions:\n\n"
        f"Task:\n{task_description}{tone_spec}{context_str}"
    )

    if llm_callable:
        raw_text = await llm_callable(prompt)
    else:
        raw_text = await gemini_service.generate_async(
            prompt=prompt,
            system_instruction=CONTENT_AGENT_SYSTEM_INSTRUCTION,
            temperature=0.3,
        )

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    data = json.loads(cleaned)
    return ContentGenerationResult(**data)

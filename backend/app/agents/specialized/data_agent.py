"""
Specialized Data Analysis Agent.
Parses and interprets user-provided CSV and JSON datasets, extracts empirical patterns,
computes verified summary statistics, and provides grounded recommendations without inventing numbers.
"""

import csv
import io
import json
import re
from typing import Any, Callable, Dict, List, Optional

from app.schemas.agent import DataAnalysisResult
from app.services import gemini_service

DATA_AGENT_SYSTEM_INSTRUCTION = """
You are an Enterprise Data Analysis AI Agent and Quantitative Auditor.
Your responsibility is to analyze provided datasets (CSV, JSON, or tabular metrics), identify statistical patterns, discover trends, detect anomalies, and formulate grounded business recommendations.

CRITICAL INSTRUCTION - NUMERICAL INTEGRITY:
- NEVER invent, fabricate, or hallucinate numerical results.
- Base all figures in "statistical_summary" and text directly on the verified computations provided in the data.
- If the dataset is small, incomplete, or contains missing values, explicitly record this under "anomalies_or_outliers".

Format:
Return strictly a valid JSON object matching this structure:
{
  "dataset_overview": "Summary of row count, dimensions, columns, and data subject matter",
  "key_trends_and_patterns": [
    "Trend 1 directly backed by numbers",
    "Trend 2 observing distribution or change"
  ],
  "statistical_summary": {
    "metric_name_1": "Verified value or summary",
    "metric_name_2": "Verified value or summary"
  },
  "anomalies_or_outliers": [
    "Identified anomaly, null value, or extreme spike"
  ],
  "data_backed_recommendations": [
    "Actionable step 1 grounded in the analyzed figures",
    "Actionable step 2 grounded in the analyzed figures"
  ]
}
"""


def _extract_dataset_precomputations(data_input: str) -> Dict[str, Any]:
    """
    Safely inspects raw data_input (CSV or JSON) to compute baseline facts
    and prevent LLM hallucination of dimensions and counts.
    """
    trimmed = data_input.strip()
    summary: Dict[str, Any] = {"format": "unstructured_text", "precomputed_facts": {}}

    # Try JSON
    if trimmed.startswith("{") or trimmed.startswith("["):
        try:
            parsed = json.loads(trimmed)
            summary["format"] = "json"
            if isinstance(parsed, list):
                summary["precomputed_facts"]["record_count"] = len(parsed)
                if len(parsed) > 0 and isinstance(parsed[0], dict):
                    summary["precomputed_facts"]["fields"] = list(parsed[0].keys())
            elif isinstance(parsed, dict):
                summary["precomputed_facts"]["keys"] = list(parsed.keys())
            return summary
        except Exception:
            pass

    # Try CSV
    if "\n" in trimmed or "," in trimmed:
        try:
            reader = csv.reader(io.StringIO(trimmed))
            rows = [r for r in reader if r]
            if len(rows) > 1:
                headers = rows[0]
                data_rows = rows[1:]
                summary["format"] = "csv"
                summary["precomputed_facts"]["header_count"] = len(headers)
                summary["precomputed_facts"]["headers"] = headers
                summary["precomputed_facts"]["row_count"] = len(data_rows)
                return summary
        except Exception:
            pass

    return summary


async def run_data_agent(
    task_description: str,
    data_input: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    llm_callable: Optional[Callable] = None,
) -> DataAnalysisResult:
    """
    Executes the Data Analysis Agent.
    """
    data_section = ""
    precomputations_section = ""

    if data_input:
        precomputed = _extract_dataset_precomputations(data_input)
        precomputations_section = (
            f"\nVerified Precomputations (Ground Truth):\n{json.dumps(precomputed, indent=2)}"
        )
        data_section = f"\nDataset Input:\n{data_input}"

    context_str = ""
    if context:
        context_str = f"\nBusiness Context:\n{json.dumps(context, indent=2)}"

    prompt = (
        f"Perform rigorous data analysis based on this task and dataset:\n\n"
        f"Task:\n{task_description}{context_str}{precomputations_section}{data_section}"
    )

    if llm_callable:
        raw_text = await llm_callable(prompt)
    else:
        raw_text = await gemini_service.generate_async(
            prompt=prompt,
            system_instruction=DATA_AGENT_SYSTEM_INSTRUCTION,
            temperature=0.1,  # Lower temperature for maximum quantitative fidelity
        )

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    data = json.loads(cleaned)
    return DataAnalysisResult(**data)

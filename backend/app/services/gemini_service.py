"""
Gemini AI service module using Google's official google-genai SDK.
Handles client lifecycle, timeouts, async generation, and error mapping.
"""

import asyncio
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import get_settings


# ── Custom Exceptions ──────────────────────────────────────────────────────────

class GeminiError(Exception):
    """Base exception for Gemini service operations."""
    pass


class GeminiNotConfiguredError(GeminiError):
    """Raised when GEMINI_API_KEY is missing or contains the default placeholder."""
    pass


class GeminiRateLimitError(GeminiError):
    """Raised when Gemini returns HTTP 429 / RESOURCE_EXHAUSTED."""
    pass


class GeminiTimeoutError(GeminiError):
    """Raised when an asynchronous API call exceeds the configured timeout."""
    pass


class GeminiAPIError(GeminiError):
    """Raised when Gemini API returns an upstream error."""
    pass


# ── Client Lifecycle ──────────────────────────────────────────────────────────

def get_gemini_client() -> genai.Client:
    """
    Constructs and returns an authenticated google-genai Client.
    Raises GeminiNotConfiguredError if the API key is unconfigured.
    """
    settings = get_settings()
    if not settings.is_gemini_configured:
        raise GeminiNotConfiguredError(
            "Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env"
        )
    return genai.Client(api_key=settings.gemini_api_key)


async def generate_async(
    prompt: str,
    system_instruction: Optional[str] = None,
    client: Optional[genai.Client] = None,
    timeout: Optional[int] = None,
    temperature: float = 0.2,
) -> str:
    """
    Executes an asynchronous call to the configured Gemini model requesting JSON output.
    Enforces a strict timeout and wraps upstream exceptions into domain errors.

    :param prompt: The input prompt for the model.
    :param system_instruction: Optional system instruction directing the model persona.
    :param client: Optional override client (useful for unit testing and mocks).
    :param timeout: Optional timeout override in seconds.
    :param temperature: Generation temperature (default 0.2 for deterministic analysis).
    :returns: Extracted text response (guaranteed JSON when using response_mime_type).
    """
    settings = get_settings()
    effective_timeout = timeout or settings.gemini_timeout_seconds

    if client is None:
        client = get_gemini_client()

    config = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json",
        system_instruction=system_instruction,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    retries = 2
    backoff = 1.5

    for attempt in range(retries + 1):
        try:
            call = client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=config,
            )
            response = await asyncio.wait_for(call, timeout=effective_timeout)
            if not response or not response.text:
                raise GeminiAPIError("Gemini returned an empty response.")
            return response.text

        except asyncio.TimeoutError as exc:
            if attempt < retries:
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            raise GeminiTimeoutError(
                f"Gemini API request timed out after {effective_timeout}s."
            ) from exc

        except APIError as exc:
            code = getattr(exc, "code", None)
            message = getattr(exc, "message", str(exc))
            is_transient = (
                code in (503, 429)
                or "RESOURCE_EXHAUSTED" in message
                or "high demand" in message.lower()
                or "temporarily" in message.lower()
            )
            if attempt < retries and is_transient:
                await asyncio.sleep(backoff)
                backoff *= 2
                continue

            if code == 429 or "RESOURCE_EXHAUSTED" in message:
                raise GeminiRateLimitError(
                    f"Gemini API rate limit exceeded: {message}"
                ) from exc
            raise GeminiAPIError(f"Gemini API error ({code}): {message}") from exc

        except GeminiError:
            raise

        except Exception as exc:
            raise GeminiAPIError(f"Unexpected error calling Gemini API: {str(exc)}") from exc

"""
RootOps — Anthropic LLM Client

Calls Anthropic's Messages API (Claude Sonnet, Haiku, Opus)
for RAG synthesis.  Requires ANTHROPIC_API_KEY to be set.
"""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def generate_anthropic(
    prompt: str,
    system_prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    conversation_history: list[dict] | None = None,
) -> str:
    """Generate a response using Anthropic's Messages API.

    Args:
        prompt: The full RAG prompt (context + query).
        system_prompt: System-level instructions.
        model: Override the configured model name.
        temperature: LLM temperature.
        max_tokens: Maximum tokens to generate.

    Returns:
        The LLM's synthesized response string.
    """
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        return (
            "⚠️ The `anthropic` package is not installed. "
            "Install it with: `pip install anthropic`"
        )

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        return (
            "⚠️ `ANTHROPIC_API_KEY` is not set. "
            "Add it to your `.env` file to use the Anthropic backend."
        )

    model_name = model or settings.ANTHROPIC_MODEL

    try:
        client = AsyncAnthropic(api_key=api_key)
        messages: list[dict] = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": prompt})

        response = await client.messages.create(
            model=model_name,
            system=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # Extract text from ContentBlock list
        text_parts = [
            block.text for block in response.content if hasattr(block, "text")
        ]
        return "\n".join(text_parts) or "No response generated."

    except Exception as e:
        logger.error("Anthropic API error: %s", e)
        return f"⚠️ Anthropic error: {e}"

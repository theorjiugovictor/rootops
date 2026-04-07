"""
RootOps — OpenAI LLM Client

Calls OpenAI's Chat Completions API (GPT-4o, GPT-4o-mini, etc.)
for RAG synthesis.  Requires OPENAI_API_KEY to be set.
"""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def generate_openai(
    prompt: str,
    system_prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    conversation_history: list[dict] | None = None,
) -> str:
    """Generate a response using OpenAI's Chat Completions API.

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
        from openai import AsyncOpenAI
    except ImportError:
        return (
            "⚠️ The `openai` package is not installed. "
            "Install it with: `pip install openai`"
        )

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return (
            "⚠️ `OPENAI_API_KEY` is not set. "
            "Add it to your `.env` file to use the OpenAI backend."
        )

    model_name = model or settings.OPENAI_MODEL

    try:
        client = AsyncOpenAI(api_key=api_key)
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or "No response generated."

    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        return f"⚠️ OpenAI error: {e}"


async def generate_openai_stream(
    prompt: str,
    system_prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    conversation_history: list[dict] | None = None,
):
    try:
        from openai import AsyncOpenAI
    except ImportError:
        yield "⚠️ The `openai` package is not installed."
        return

    api_key = settings.OPENAI_API_KEY
    model_name = model or settings.OPENAI_MODEL
    try:
        client = AsyncOpenAI(api_key=api_key)
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": prompt})

        stream = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        logger.error("OpenAI mapping streaming error: %s", e)
        yield f"\n\n[Error streaming from OpenAI: {e}]"

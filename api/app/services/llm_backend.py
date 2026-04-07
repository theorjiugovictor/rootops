"""
RootOps — LLM Backend Dispatcher

Routes LLM generation requests to the configured backend.
Supports: Ollama (default), OpenAI, Anthropic, AWS Bedrock.

Accepts:
  - context_chunks: retrieved code/log chunks (formatted into the prompt)
  - conversation_history: prior turns as [{"role": "user"|"assistant", "content": "..."}]
  - codebase_summary: pre-loaded architectural summary injected into the system prompt
"""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Base system prompt ────────────────────────────────────────────
_BASE_SYSTEM_PROMPT = """\
You are RootOps, an AI-native internal developer platform acting as a \
senior engineering advisor. You have deep, persistent knowledge of the \
codebase described in the architectural summary below.

Your role:
- Provide precise, actionable code review and architectural feedback.
- Reference specific code patterns, files, and line numbers when relevant.
- Flag potential risks by connecting current code to historical patterns.
- Remember and build on earlier parts of this conversation.
- Be concise and direct — engineers don't want fluff.

When given code context, analyse it carefully and relate it to the query.
If the context doesn't contain enough information to answer, say so honestly.
"""


def build_system_prompt(codebase_summary: str | None = None) -> str:
    """Build the full system prompt, optionally including the codebase summary."""
    if codebase_summary and codebase_summary.strip():
        return (
            _BASE_SYSTEM_PROMPT
            + "\n## Codebase Architecture\n\n"
            + codebase_summary.strip()
            + "\n"
        )
    return _BASE_SYSTEM_PROMPT


async def generate(
    query: str,
    context_chunks: list[dict],
    *,
    temperature: float = 0.3,
    conversation_history: list[dict] | None = None,
    codebase_summary: str | None = None,
) -> str:
    """Generate an LLM response using the configured backend.

    Args:
        query: The user's question or review request.
        context_chunks: Retrieved code/log chunks from vector search.
        temperature: LLM temperature.
        conversation_history: Prior turns as role/content dicts.
        codebase_summary: Architectural summary to inject into system prompt.

    Returns:
        The synthesized response string.
    """
    backend = settings.LLM_BACKEND.lower()
    system_prompt = build_system_prompt(codebase_summary)

    # Build the RAG prompt (shared across backends)
    context_text = format_context(context_chunks)
    prompt = (
        f"## Retrieved Code Context\n\n{context_text}\n\n"
        f"## Developer Query\n\n{query}\n\n"
        f"## Instructions\n\n"
        f"Analyse the retrieved code context above and answer the "
        f"developer's query. Reference specific files and line numbers "
        f"when relevant. If this code is similar to known issues, flag them."
    )

    kwargs = dict(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        conversation_history=conversation_history or [],
    )

    if backend == "ollama":
        logger.info("Using Ollama backend (model: %s)", settings.OLLAMA_MODEL)
        from app.services.llm_client import generate_ollama
        return await generate_ollama(**kwargs)

    elif backend == "openai":
        logger.info("Using OpenAI backend (model: %s)", settings.OPENAI_MODEL)
        from app.services.openai_client import generate_openai
        return await generate_openai(**kwargs)

    elif backend == "anthropic":
        logger.info("Using Anthropic backend (model: %s)", settings.ANTHROPIC_MODEL)
        from app.services.anthropic_client import generate_anthropic
        return await generate_anthropic(**kwargs)

    elif backend == "bedrock":
        logger.info("Using Bedrock backend (model: %s)", settings.BEDROCK_MODEL_ID)
        from app.services.bedrock_client import generate_bedrock
        # Bedrock client gets history injected into prompt text (no native multi-turn)
        if conversation_history:
            history_text = "\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in conversation_history
            )
            kwargs["prompt"] = f"## Conversation History\n\n{history_text}\n\n" + prompt
        return await generate_bedrock(
            prompt=kwargs["prompt"],
            system_prompt=system_prompt,
            temperature=temperature,
        )

    else:
        logger.error("Unknown LLM backend: %s", backend)
        raise ValueError(
            f"Unknown LLM backend: '{backend}'. "
            f"Set LLM_BACKEND to 'ollama', 'openai', 'anthropic', or 'bedrock'."
        )


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a readable context block."""
    if not chunks:
        return "_No relevant code context found._"

    sections: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        similarity = chunk.get("similarity", 0)
        rerank_score = chunk.get("rerank_score")
        file_path = chunk.get("file_path", "unknown")
        start = chunk.get("start_line", "?")
        end = chunk.get("end_line", "?")
        content = chunk.get("content", "")
        language = chunk.get("language", "") or ""

        score_label = (
            f"rerank: {rerank_score:.3f}" if rerank_score is not None
            else f"similarity: {similarity:.2%}"
        )

        sections.append(
            f"### Match {i} — `{file_path}` (lines {start}-{end}) [{score_label}]\n"
            f"```{language}\n{content}\n```"
        )

    return "\n\n".join(sections)


async def generate_stream(
    query: str,
    context_chunks: list[dict],
    *,
    temperature: float = 0.3,
    conversation_history: list[dict] | None = None,
    codebase_summary: str | None = None,
):
    backend = settings.LLM_BACKEND.lower()
    system_prompt = build_system_prompt(codebase_summary)

    context_text = format_context(context_chunks)
    prompt = (
        f"## Retrieved Code Context\n\n{context_text}\n\n"
        f"## Developer Query\n\n{query}\n\n"
        f"## Instructions\n\n"
        f"Analyse the retrieved code context above and answer the "
        f"developer's query. Reference specific files and line numbers "
        f"when relevant. If this code is similar to known issues, flag them."
    )

    kwargs = dict(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        conversation_history=conversation_history or [],
    )

    if backend == "ollama":
        from app.services.llm_client import generate_ollama_stream
        async for chunk in generate_ollama_stream(**kwargs):
            yield chunk

    elif backend == "openai":
        from app.services.openai_client import generate_openai_stream
        async for chunk in generate_openai_stream(**kwargs):
            yield chunk

    elif backend == "anthropic":
        from app.services.anthropic_client import generate_anthropic
        result = await generate_anthropic(**kwargs)
        yield result

    elif backend == "bedrock":
        from app.services.bedrock_client import generate_bedrock
        if conversation_history:
            history_text = "\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in conversation_history
            )
            kwargs["prompt"] = f"## Conversation History\n\n{history_text}\n\n" + prompt
        result = await generate_bedrock(
            prompt=kwargs["prompt"],
            system_prompt=system_prompt,
            temperature=temperature,
        )
        yield result
    else:
        raise ValueError(f"Unknown LLM backend: {backend}")

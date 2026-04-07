"""
RootOps V2 — AWS Bedrock LLM Client

Calls AWS Bedrock (Claude 3 Haiku by default) for RAG synthesis.
Used in ECS/cloud deployments where Ollama isn't available.
Auth via IAM role — no access keys needed when running on ECS with a task role.
"""

from __future__ import annotations

import json
import logging

import boto3
from botocore.config import Config as BotoConfig

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_bedrock_client():
    """Create a Bedrock Runtime client with the configured region."""
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.BEDROCK_REGION,
        config=BotoConfig(
            retries={"max_attempts": 3, "mode": "adaptive"},
            read_timeout=120,
        ),
    )


async def generate_bedrock(
    prompt: str,
    system_prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """Generate a response using AWS Bedrock (Claude 3.5 Sonnet by default).

    Args:
        prompt: The user prompt with RAG context.
        system_prompt: System-level instructions.
        model: Override the configured Bedrock model ID.
        temperature: LLM temperature.
        max_tokens: Maximum tokens to generate.

    Returns:
        The LLM's synthesized response string.
    """
    model_id = model or settings.BEDROCK_MODEL_ID

    # Build request body per model family.
    # Anthropic models use Messages API, while Meta Llama Instruct models
    # use native Inference payload fields.
    is_anthropic = "anthropic." in model_id   # matches anthropic.*, us.anthropic.*, eu.anthropic.*
    is_meta = "meta." in model_id

    if is_anthropic:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }
    elif is_meta:
        body = {
            "prompt": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
            f"{system_prompt}\n"
            f"<|eot_id|><|start_header_id|>user<|end_header_id|>\n"
            f"{prompt}\n"
            f"<|eot_id|><|start_header_id|>assistant<|end_header_id|>",
            "temperature": temperature,
            "max_gen_len": max_tokens,
        }
    else:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

    try:
        client = _get_bedrock_client()
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )

        response_body = json.loads(response["body"].read())

        if is_meta:
            return response_body.get("generation", "No response generated.")

        # Anthropic Messages API returns content as a list
        content_blocks = response_body.get("content", [])
        text_parts = [
            block["text"]
            for block in content_blocks
            if block.get("type") == "text"
        ]
        return "\n".join(text_parts) if text_parts else "No response generated."

    except client.exceptions.AccessDeniedException as e:
        logger.error("Bedrock access denied for model %s: %s", model_id, e)
        return (
            "⚠️ AWS Bedrock access denied. Ensure the ECS task role has "
            "`bedrock:InvokeModel` permission for model `" + model_id + "`. "
            "Also check that model access is granted in the Bedrock console. "
            "Detail: " + str(e)
        )

    except client.exceptions.ModelNotReadyException:
        logger.error("Bedrock model not ready: %s", model_id)
        return f"⚠️ Bedrock model `{model_id}` is not ready. Enable it in the AWS Console."

    except Exception as e:
        logger.error("Bedrock error: %s", e)
        return f"⚠️ Bedrock error: {e}"

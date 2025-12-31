import logging
import json
import httpx
from typing import Dict, Optional, Any
from src.config import settings

logger = logging.getLogger(__name__)

async def enrich_commit_analysis(diff_content: str) -> Optional[Dict[str, Any]]:
    """
    Enrich commit analysis using the configured LLM provider.
    Supports: Gemini, OpenAI, Anthropic.
    """
    if not settings.LLM_API_KEY:
        return None

    # Truncate diff to avoid token limits (conservative)
    truncated_diff = diff_content[:30000]
    
    prompt = f"""
    Analyze this git diff for DevOps operational risk.
    Return ONLY valid JSON.
    
    Output format:
    {{
        "risk_score": <1-10 float>,
        "summary": "<1 sentence on what this code actually changes>",
        "breaking_change": <bool>,
        "security_risk": <bool>,
        "suggested_action": "PROCEED" | "REVIEW" | "BLOCK"
    }}

    DIFF:
    {truncated_diff}
    """

    provider = settings.LLM_PROVIDER.lower()
    
    try:
        if provider == "gemini":
            return await _call_gemini(prompt)
        elif provider == "openai":
            return await _call_openai(prompt)
        elif provider == "anthropic":
            return await _call_anthropic(prompt)
        else:
            logger.error(f"Unknown LLM provider: {provider}")
            return None
            
    except Exception as e:
        logger.error(f"LLM Enrichment failed ({provider}): {e}")
        return None

async def _call_gemini(prompt: str) -> Optional[Dict]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent?key={settings.LLM_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=30.0)
        
        if response.status_code != 200:
            logger.error(f"Gemini API Error: {response.text}")
            return None
            
        data = response.json()
        try:
            candidate = data["candidates"][0]["content"]["parts"][0]["text"]
            return _parse_json(candidate)
        except (KeyError, IndexError):
            return None

async def _call_openai(prompt: str) -> Optional[Dict]:
    """Generic OpenAI-compatible endpoint"""
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": settings.LLM_MODEL or "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a DevOps Risk Analyst. Output JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=30.0)
        
        if response.status_code != 200:
            logger.error(f"OpenAI API Error: {response.text}")
            return None
            
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _parse_json(content)

async def _call_anthropic(prompt: str) -> Optional[Dict]:
    """Anthropic API endpoint"""
    url = "https://api.anthropic.com/v1/messages"
    
    headers = {
        "x-api-key": settings.LLM_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    payload = {
        "model": settings.LLM_MODEL or "claude-3-sonnet-20240229",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=30.0)
        
        if response.status_code != 200:
            logger.error(f"Anthropic API Error: {response.text}")
            return None
            
        data = response.json()
        content = data["content"][0]["text"]
        return _parse_json(content)

def _parse_json(text: str) -> Optional[Dict]:
    try:
        clean_json = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON: {e}")
        return None

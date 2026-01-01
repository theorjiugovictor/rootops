import logging
import json
import httpx
from typing import Dict, Optional, Any
from src.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Client for interacting with LLM providers (Gemini, OpenAI, Anthropic).
    """
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL

    async def enrich_commit_analysis(self, diff_content: str) -> Optional[Dict[str, Any]]:
        """
        Enrich commit analysis using the configured LLM provider.
        """
        if not self.api_key:
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

        try:
            if self.provider == "gemini":
                return await self._call_gemini(prompt)
            elif self.provider == "openai":
                return await self._call_openai(prompt)
            elif self.provider == "anthropic":
                return await self._call_anthropic(prompt)
            else:
                logger.error(f"Unknown LLM provider: {self.provider}")
                return None
                
        except Exception as e:
            logger.error(f"LLM Enrichment failed ({self.provider}): {e}")
            return None

    def complete(self, prompt: str) -> str:
        """
        Synchronous wrapper or direct call for text completion. 
        Note: Since we are in an async route, we should ideally use async, but for simplicity
        and given the requests usage in the original code, we'll implement a sync-blocking version
        using httpx.Client or just run async in a loop if needed.
        
        Wait, the usage in dashboard_routes.py was:
        response = llm.complete(prompt)
        
        Let's implement a synchronous version of 'complete' using httpx.Client()
        """
        if not self.api_key:
            return "AI Analysis Unavailable: No API Key."

        try:
            if self.provider == "gemini":
                return self._call_gemini_sync(prompt)
            elif self.provider == "openai":
                return self._call_openai_sync(prompt)
            # Add others if needed
            return "AI Analysis Unavailable: Provider not supported for sync."
            
        except Exception as e:
            logger.error(f"LLM Complete failed: {e}")
            return f"AI Analysis Failed: {str(e)}"

    async def _call_gemini(self, prompt: str) -> Optional[Dict]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            if response.status_code != 200: return None
            try:
                candidate = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                return self._parse_json(candidate)
            except (KeyError, IndexError): return None

    async def _call_openai(self, prompt: str) -> Optional[Dict]:
        base_url = settings.LLM_BASE_URL or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model or "gpt-4o",
            "messages": [{"role": "system", "content": "You are a DevOps Risk Analyst. Output JSON only."}, {"role": "user", "content": prompt}],
            "temperature": 0.2, "response_format": {"type": "json_object"}
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            if response.status_code != 200: return None
            return self._parse_json(response.json()["choices"][0]["message"]["content"])

    async def _call_anthropic(self, prompt: str) -> Optional[Dict]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        payload = {
            "model": self.model or "claude-3-sonnet-20240229", "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            if response.status_code != 200: return None
            return self._parse_json(response.json()["content"][0]["text"])

    def _call_gemini_sync(self, prompt: str) -> str:
        """Synchronous version for dashboard"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2} # Text mode
        }
        with httpx.Client() as client:
            response = client.post(url, json=payload, timeout=10.0)
            if response.status_code != 200: return f"Error: {response.text}"
            try:
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception: return "Error parsing Gemini response"

    def _call_openai_sync(self, prompt: str) -> str:
        base_url = settings.LLM_BASE_URL or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model or "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=10.0)
            content = response.json()["choices"][0]["message"]["content"]
            return content

    def _parse_json(self, text: str) -> Optional[Dict]:
        try:
            clean_json = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}")
            return None

# Backward compatibility for existing service calls if any use standalone functions
# We instance the client globally for them
_global_client = LLMClient()
async def enrich_commit_analysis(diff_content: str) -> Optional[Dict[str, Any]]:
    return await _global_client.enrich_commit_analysis(diff_content)

"""
RootOps — PR Review Backend Proxy

Server-side proxy for GitHub PR data. The GITHUB_TOKEN lives in the
server environment and is NEVER sent to or visible in the browser.

Security model:
  - No client-side authentication token of any kind.
  - GITHUB_TOKEN is read from server config (env var / .env file).
  - Unauthenticated requests still work against public repos (60 req/hr).
  - Authenticated requests (GITHUB_TOKEN set) get 5000 req/hr.

Endpoints:
  GET /api/pr-review/prs    — list open PRs for owner/repo
  GET /api/pr-review/diff   — get changed files + unified diff for a PR
  GET /api/pr-review/status — whether the GitHub token is configured
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Header, HTTPException, Query

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/pr-review", tags=["pr-review"])

_GITHUB_API = "https://api.github.com"


def _github_headers(token_override: str | None = None) -> dict[str, str]:
    """Build GitHub API headers.

    Priority: per-request token (X-GitHub-Token header) > server-side
    GITHUB_TOKEN env var > unauthenticated (public repos, 60 req/hr).
    """
    h: dict[str, str] = {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "RootOps/1.0",
    }
    token = token_override or settings.GITHUB_TOKEN
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def _gh_get(url: str, token_override: str | None = None) -> httpx.Response:
    """Execute a GET against the GitHub API with proper error handling."""
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            return await client.get(url, headers=_github_headers(token_override))
    except httpx.TimeoutException as exc:
        raise HTTPException(504, f"GitHub API timed out: {exc}") from exc
    except httpx.RequestError as exc:
        raise HTTPException(502, f"Cannot reach GitHub API: {exc}") from exc


def _raise_for_github_status(r: httpx.Response, context: str = "") -> None:
    """Raise an HTTPException with a helpful message for common GitHub errors."""
    if r.is_success:
        return
    if r.status_code == 401:
        raise HTTPException(401, "GitHub token is invalid or expired. Update GITHUB_TOKEN in .env.")
    if r.status_code == 403:
        remaining = r.headers.get("X-RateLimit-Remaining", "?")
        reset_ts = r.headers.get("X-RateLimit-Reset", "?")
        raise HTTPException(
            403,
            f"GitHub rate limit exceeded (remaining={remaining}, reset={reset_ts}). "
            "Set GITHUB_TOKEN in .env to increase the limit to 5000/hr.",
        )
    if r.status_code == 404:
        raise HTTPException(
            404,
            f"Repository not found or not accessible{' (' + context + ')' if context else ''}. "
            "Check the owner/repo names and ensure your GITHUB_TOKEN has read access.",
        )
    raise HTTPException(r.status_code, f"GitHub API error: {r.text[:300]}")


# ── Endpoints ─────────────────────────────────────────────────────

@router.get("/status")
async def pr_review_status():
    """Return whether the server-side GitHub token is configured."""
    return {
        "has_token": bool(settings.GITHUB_TOKEN),
        "note": (
            "GitHub token is configured — 5000 req/hr available."
            if settings.GITHUB_TOKEN
            else "No GitHub token configured. Set GITHUB_TOKEN in .env for private repos and higher rate limits."
        ),
    }


@router.get("/prs")
async def list_open_prs(
    owner: str = Query(..., description="GitHub repository owner (user or org)"),
    repo: str = Query(..., description="GitHub repository name"),
    x_github_token: str | None = Header(None, alias="X-GitHub-Token"),
):
    """List open pull requests for a repository.

    Authentication priority:
      1. X-GitHub-Token request header (per-request PAT from the browser)
      2. Server-side GITHUB_TOKEN env var
      3. Unauthenticated (public repos only, 60 req/hr)
    """
    token = x_github_token or None  # empty string → treat as None
    url = (
        f"{_GITHUB_API}/repos/{owner}/{repo}/pulls"
        "?state=open&per_page=30&sort=updated&direction=desc"
    )
    r = await _gh_get(url, token_override=token)
    _raise_for_github_status(r, context=f"{owner}/{repo}")

    rate_remaining = r.headers.get("X-RateLimit-Remaining", "unknown")
    logger.debug("GitHub rate limit remaining: %s", rate_remaining)

    return {
        "prs": r.json(),
        "rate_remaining": rate_remaining,
        "has_token": bool(token or settings.GITHUB_TOKEN),
    }


@router.get("/diff")
async def get_pr_diff(
    owner: str = Query(..., description="GitHub repository owner"),
    repo: str = Query(..., description="GitHub repository name"),
    pr: int = Query(..., ge=1, description="Pull request number"),
    x_github_token: str | None = Header(None, alias="X-GitHub-Token"),
):
    """Fetch the changed files and unified diff for a specific PR.

    Returns the files list and a concatenated unified diff string that
    can be fed directly into the RAG query engine for analysis.
    """
    token = x_github_token or None
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/pulls/{pr}/files?per_page=100"
    r = await _gh_get(url, token_override=token)
    _raise_for_github_status(r, context=f"{owner}/{repo}#{pr}")

    files = r.json()

    # Assemble a unified diff from per-file patches
    parts: list[str] = []
    for f in files:
        status = f.get("status", "modified")
        fname = f.get("filename", "unknown")
        parts.append("--- /dev/null" if status == "added" else f"--- a/{fname}")
        parts.append("+++ /dev/null" if status == "removed" else f"+++ b/{fname}")
        if f.get("patch"):
            parts.append(f["patch"])

    return {
        "files": files,
        "diff": "\n".join(parts),
        "file_count": len(files),
        "additions": sum(f.get("additions", 0) for f in files),
        "deletions": sum(f.get("deletions", 0) for f in files),
    }

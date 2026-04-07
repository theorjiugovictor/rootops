/**
 * RootOps — GitHub API Client
 *
 * Mirrors ui/utils/github.py.
 * Runs client-side — calls go directly to api.github.com.
 */

const GITHUB_API = "https://api.github.com";
const TIMEOUT = 10_000;

function headers(token?: string): HeadersInit {
  const h: Record<string, string> = {
    Accept: "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
  };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

export interface GitHubPR {
  number: number;
  title: string;
  body?: string;
  draft?: boolean;
  user?: { login: string; avatar_url?: string };
  labels?: { name: string; color: string }[];
  additions?: number;
  deletions?: number;
  changed_files?: number;
  updated_at?: string;
  created_at?: string;
  html_url?: string;
}

export async function getOpenPRs(
  owner: string,
  repo: string,
  token?: string,
): Promise<{ ok: boolean; prs: GitHubPR[]; rate_remaining?: number; error?: string }> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT);

    const url = `${GITHUB_API}/repos/${owner}/${repo}/pulls?state=open&per_page=30&sort=updated&direction=desc`;
    const res = await fetch(url, { headers: headers(token), signal: controller.signal });
    clearTimeout(timer);

    if (!res.ok) {
      if (res.status === 404) return { ok: false, prs: [], error: `Repo ${owner}/${repo} not found` };
      if (res.status === 403) return { ok: false, prs: [], error: "Rate limit exceeded or auth required" };
      return { ok: false, prs: [], error: `GitHub API: ${res.status}` };
    }

    const rate = parseInt(res.headers.get("X-RateLimit-Remaining") || "999", 10);
    return { ok: true, prs: await res.json(), rate_remaining: rate };
  } catch {
    return { ok: false, prs: [], error: "Cannot reach api.github.com" };
  }
}

export async function getPRFiles(
  owner: string,
  repo: string,
  prNumber: number,
  token?: string,
): Promise<{ ok: boolean; files: unknown[]; diff: string; error?: string }> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT);

    const url = `${GITHUB_API}/repos/${owner}/${repo}/pulls/${prNumber}/files?per_page=100`;
    const res = await fetch(url, { headers: headers(token), signal: controller.signal });
    clearTimeout(timer);

    if (!res.ok) return { ok: false, files: [], diff: "", error: `GitHub API: ${res.status}` };

    const files = await res.json();
    const parts: string[] = [];
    for (const f of files) {
      const status = f.status || "modified";
      const fname = f.filename || "unknown";
      parts.push(status === "added" ? "--- /dev/null" : `--- a/${fname}`);
      parts.push(status === "removed" ? "+++ /dev/null" : `+++ b/${fname}`);
      if (f.patch) parts.push(f.patch);
    }

    return { ok: true, files, diff: parts.join("\n") };
  } catch {
    return { ok: false, files: [], diff: "", error: "Cannot reach api.github.com" };
  }
}

export function formatAge(isoTimestamp: string): string {
  try {
    const dt = new Date(isoTimestamp);
    const s = Math.floor((Date.now() - dt.getTime()) / 1000);
    if (s < 60) return "just now";
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
  } catch {
    return "unknown";
  }
}

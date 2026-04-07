/**
 * RootOps — TypeScript API Client
 *
 * Mirrors every endpoint from ui/utils/api.py.
 * All functions return { ok: boolean, ... } — callers never catch.
 *
 * Runs client-side (browser) — requests go through Next.js rewrites
 * to the FastAPI backend so there are no CORS issues.
 */

const TIMEOUT_FAST = 5_000;
const TIMEOUT_QUERY = 120_000;
const TIMEOUT_INGEST = 300_000;
const TIMEOUT_HEAL = 120_000;
const TIMEOUT_PROFILES = 60_000;

// ── Internal fetch wrapper ──────────────────────────────────────

async function api<T = Record<string, unknown>>(
  path: string,
  opts: RequestInit & { timeout?: number } = {},
): Promise<T & { ok: boolean; error?: string }> {
  const { timeout = TIMEOUT_FAST, ...init } = opts;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(path, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...init.headers,
      },
    });
    clearTimeout(timer);

    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      return { ok: false, error: text } as T & { ok: false; error: string };
    }

    const data = await res.json();
    return { ok: true, ...data };
  } catch (err: unknown) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === "AbortError") {
      return { ok: false, error: "Request timed out" } as T & { ok: false; error: string };
    }
    const message = err instanceof Error ? err.message : String(err);
    return { ok: false, error: message } as T & { ok: false; error: string };
  }
}

// Variant for endpoints that return a bare JSON array (not an object).
// `api()` spreads the response object, which silently breaks for arrays.
async function apiList<T>(
  path: string,
  opts: RequestInit & { timeout?: number } = {},
): Promise<{ ok: boolean; data: T[]; error?: string }> {
  const { timeout = TIMEOUT_FAST, ...init } = opts;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(path, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...init.headers,
      },
    });
    clearTimeout(timer);

    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      return { ok: false, data: [], error: text };
    }

    const data: T[] = await res.json();
    return { ok: true, data: Array.isArray(data) ? data : [] };
  } catch (err: unknown) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === "AbortError") {
      return { ok: false, data: [], error: "Request timed out" };
    }
    const message = err instanceof Error ? err.message : String(err);
    return { ok: false, data: [], error: message };
  }
}


// ── Health & Status ─────────────────────────────────────────────

export async function getHealth() {
  return api("/health");
}

export async function getIngestStatus() {
  return api("/api/ingest/status");
}


// ── Code Repository Ingestion ───────────────────────────────────

export interface IngestPayload {
  repo_path?: string;
  repo_url?: string;
  branch?: string;
  max_commits?: number;
  name?: string;
  team?: string;
  tags?: string[];
  description?: string;
}

export async function triggerIngest(payload: IngestPayload) {
  return api("/api/ingest", {
    method: "POST",
    body: JSON.stringify(payload),
    timeout: TIMEOUT_INGEST,
  });
}


// ── Log Ingestion ───────────────────────────────────────────────

export async function ingestLogs(
  raw_text: string,
  service_name = "unknown",
  source = "raw",
) {
  return api("/api/ingest/logs", {
    method: "POST",
    body: JSON.stringify({ raw_text, service_name, source }),
    timeout: TIMEOUT_INGEST,
  });
}

export async function getLogStats() {
  return api("/api/ingest/logs/stats");
}

export async function getOtelReceiverStatus() {
  return api("/api/ingest/logs/otel/status");
}


// ── Query (Hybrid RAG) ─────────────────────────────────────────

export interface QueryPayload {
  question: string;
  top_k?: number;
  use_llm?: boolean;
  conversation_history?: { role: string; content: string }[];
  repo_ids?: string[];
}

export interface QuerySource {
  file_path: string;
  similarity: number;
  content: string;
  start_line?: number;
  end_line?: number;
  language?: string;
  commit_sha?: string;
  cross_referenced?: boolean;
}

export interface LogMatch {
  service_name: string;
  timestamp: string;
  level: string;
  message: string;
  parsed_error?: string;
  file_reference?: string;
  similarity: number;
}

export interface QueryResult {
  ok: boolean;
  query?: string;
  answer?: string;
  sources?: QuerySource[];
  log_matches?: LogMatch[];
  metadata?: Record<string, unknown>;
  error?: string;
}

export async function queryCosebase(payload: QueryPayload): Promise<QueryResult> {
  return api<QueryResult>("/api/query", {
    method: "POST",
    body: JSON.stringify(payload),
    timeout: TIMEOUT_QUERY,
  });
}

/**
 * Streaming RAG query — yields tokens via SSE.
 */
export async function* streamQuery(payload: QueryPayload) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_QUERY);

  try {
    const res = await fetch("/api/query/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, use_llm: true }),
      signal: controller.signal,
    });

    clearTimeout(timer);
    if (!res.ok || !res.body) return;

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const msg = JSON.parse(line);
          yield msg;
        } catch { /* skip malformed */ }
      }
    }
  } catch {
    yield { type: "error", data: "Stream connection failed" };
  }
}


// ── Repositories ────────────────────────────────────────────────

export interface Repository {
  id: string;
  name: string;
  url?: string;
  local_path?: string;
  team?: string;
  tags?: string[];
  description?: string;
  chunk_count: number;
  commit_count: number;
  last_ingested_at?: string;
}

export async function getRepositories(): Promise<{ ok: boolean; repos: Repository[] }> {
  const { ok, data } = await apiList<Repository>("/api/repos");
  return { ok, repos: data };
}

export async function getDependencyGraph() {
  return api("/api/repos/graph");
}

export async function deleteRepository(repoId: string) {
  return api(`/api/repos/${repoId}`, { method: "DELETE" });
}


// ── Auto-Healing ────────────────────────────────────────────────

export async function runHeal(serviceName?: string) {
  const params = serviceName ? `?service_name=${encodeURIComponent(serviceName)}` : "";
  return api(`/api/heal${params}`, {
    method: "POST",
    timeout: TIMEOUT_HEAL,
  });
}

export interface PendingFix {
  fix_id: string;
  error_message?: string;
  related_file?: string;
  diagnosis?: string;
  suggested_code?: string;
  similarity_score?: number;
}

export async function getFixes(): Promise<{ ok: boolean; fixes: PendingFix[] }> {
  const { ok, data } = await apiList<PendingFix>("/api/heal/fixes");
  return { ok, fixes: data };
}

export async function getFix(fixId: string) {
  return api(`/api/heal/fixes/${fixId}`);
}

export async function createHealPr(
  fixId: string,
  repoFullName: string,
  newContent: string,
  baseBranch = "main",
) {
  return api("/api/heal/pr", {
    method: "POST",
    body: JSON.stringify({
      fix_id: fixId,
      repo_full_name: repoFullName,
      new_content: newContent,
      base_branch: baseBranch,
    }),
    timeout: TIMEOUT_HEAL,
  });
}


// ── Developer Profiles ──────────────────────────────────────────

export interface ProfileSummary {
  author_name: string;
  author_email: string;
  commit_count: number;
  primary_languages: Record<string, number>;
  last_updated?: string;
}

export async function getProfiles(): Promise<{ ok: boolean; profiles: ProfileSummary[] }> {
  const { ok, data } = await apiList<ProfileSummary>("/api/profiles", { timeout: TIMEOUT_PROFILES });
  return { ok, profiles: data };
}

export interface ProfileDetail extends ProfileSummary {
  pattern_summary?: string;
  code_patterns?: Record<string, unknown>;
}

export async function getProfile(email: string): Promise<{ ok: boolean; error?: string } & Partial<ProfileDetail>> {
  return api(`/api/profiles/${encodeURIComponent(email)}`);
}

export async function buildProfiles() {
  return api("/api/profiles/build", {
    method: "POST",
    timeout: TIMEOUT_PROFILES,
  });
}

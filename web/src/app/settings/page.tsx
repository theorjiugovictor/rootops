"use client";

import { useEffect, useState } from "react";
import {
  PageHeader,
  Metric,
  Card,
  Button,
  ConnectionStatus,
  EmptyState,
  SectionTitle,
} from "@/components/ui";
import {
  getHealth,
  getDetailedHealth,
  getIngestStatus,
  getRepositories,
  triggerIngest,
  deleteRepository,
  type Repository,
} from "@/lib/api";
import { ChevronDown, GitBranch, Layers, Trash2, CheckCircle2, XCircle, AlertCircle, RefreshCw } from "lucide-react";

const INPUT_CLS =
  "w-full px-3.5 py-2.5 bg-bg-input border border-white/[0.09] rounded-xl text-[13px] text-text placeholder:text-text-dim focus:border-accent/40 focus:ring-2 focus:ring-accent/[0.07] outline-none transition-all";

interface DetailedHealth {
  ok: boolean;
  checks?: Record<string, { ok: boolean; detail?: string; [key: string]: unknown }>;
  error?: string;
}

export default function SettingsPage() {
  const [health, setHealth]   = useState<Record<string, unknown>>({});
  const [stats, setStats]     = useState<Record<string, number>>({});
  const [state, setState]     = useState("unknown");
  const [repos, setRepos]     = useState<Repository[]>([]);
  const [detailedHealth, setDetailedHealth] = useState<DetailedHealth | null>(null);
  const [healthLoading, setHealthLoading]   = useState(false);

  // Ingest form
  const [mode, setMode]               = useState<"path" | "url">("url");
  const [pathInput, setPathInput]     = useState("");
  const [urlInput, setUrlInput]       = useState("");
  const [branch, setBranch]           = useState("HEAD");
  const [maxCommits, setMaxCommits]   = useState(50);
  const [repoName, setRepoName]       = useState("");
  const [team, setTeam]               = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags]               = useState("");
  const [showMeta, setShowMeta]       = useState(false);
  const [ingesting, setIngesting]     = useState(false);
  const [ingestMsg, setIngestMsg]     = useState<{ ok: boolean; text: string } | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  function refresh() {
    getHealth().then(setHealth);
    getIngestStatus().then((s) => {
      setStats((s.stats as Record<string, number>) ?? {});
      setState((s.state as string) ?? "unknown");
    });
    getRepositories().then((r) => setRepos(r.repos));
  }

  async function fetchDetailedHealth() {
    setHealthLoading(true);
    const res = await getDetailedHealth().catch(() => ({ ok: false }));
    setDetailedHealth(res as DetailedHealth);
    setHealthLoading(false);
  }

  useEffect(() => {
    refresh();
    fetchDetailedHealth();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleIngest() {
    const input = mode === "url" ? urlInput : pathInput;
    if (!input.trim()) {
      setIngestMsg({ ok: false, text: `Enter a ${mode === "url" ? "Git URL" : "local path"} first.` });
      return;
    }
    setIngesting(true);
    setIngestMsg(null);
    const tagsList = tags.split(",").map((t) => t.trim()).filter(Boolean);
    try {
      const res = await triggerIngest({
        ...(mode === "path" ? { repo_path: pathInput } : { repo_url: urlInput }),
        branch,
        max_commits: maxCommits,
        name:        repoName      || undefined,
        team:        team          || undefined,
        tags:        tagsList.length ? tagsList : undefined,
        description: description   || undefined,
      });
      setIngestMsg({
        ok:   !!res.ok,
        text: res.ok ? (res.message as string) || "Done" : res.error || "Failed",
      });
      refresh();
    } catch (err) {
      setIngestMsg({ ok: false, text: err instanceof Error ? err.message : "Unexpected error" });
    } finally {
      setIngesting(false);
    }
  }

  async function handleDelete(repo: Repository) {
    if (!confirm(`Delete "${repo.name}"? This removes ALL associated data.`)) return;
    setDeleteError(null);
    const res = await deleteRepository(repo.id);
    if (res.ok) refresh();
    else setDeleteError(res.error || `Failed to delete ${repo.name}`);
  }

  const stateLabel: Record<string, string> = {
    idle:      "Ready",
    running:   "Ingesting…",
    completed: "Ready",
    failed:    "Failed",
  };

  return (
    <>
      <PageHeader
        title="Settings"
        subtitle="Repository management and ingestion configuration"
      />

      {/* Status row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-10">
        <ConnectionStatus
          ok={!!health.ok}
          extra={(process.env.NEXT_PUBLIC_API_URL || "localhost:8000").replace(/^https?:\/\//, "")}
        />
        <Metric label="State"  value={stateLabel[state] || "Unknown"} icon={<Layers size={11} />} />
        <Metric label="Chunks" value={(stats.chunks_ingested ?? 0).toLocaleString()} icon={<GitBranch size={11} />} />
      </div>

      {/* System status panel */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <SectionTitle>System Status</SectionTitle>
          <button
            type="button"
            onClick={fetchDetailedHealth}
            disabled={healthLoading}
            className="flex items-center gap-1.5 text-[11px] text-text-dim hover:text-text transition-colors disabled:opacity-40"
          >
            <RefreshCw size={11} className={healthLoading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>

        {detailedHealth ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {detailedHealth.checks &&
              Object.entries(detailedHealth.checks).map(([key, check]) => {
                const label =
                  key === "database"        ? "Database"
                  : key === "embedding"     ? "Embedding"
                  : key === "llm"           ? "LLM Backend"
                  : key === "github_token"  ? "GitHub Token"
                  : key;
                return (
                  <div
                    key={key}
                    className={`rounded-[12px] border p-3.5 flex flex-col gap-2 ${
                      check.ok
                        ? "border-success/[0.18] bg-success/[0.03]"
                        : "border-error/[0.18] bg-error/[0.03]"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {check.ok
                        ? <CheckCircle2 size={13} className="text-success shrink-0" />
                        : <XCircle      size={13} className="text-error   shrink-0" />
                      }
                      <span className="text-[12.5px] font-semibold text-text-bright">{label}</span>
                    </div>
                    {check.detail && (
                      <p className="text-[11px] text-text-dim leading-relaxed">{check.detail}</p>
                    )}
                  </div>
                );
              })
            }
            {!detailedHealth.checks && (
              <div className="sm:col-span-2 lg:col-span-4 flex items-center gap-2 text-[12.5px] text-error">
                <AlertCircle size={13} />
                {detailedHealth.error ?? "Could not reach health endpoint."}
              </div>
            )}
          </div>
        ) : healthLoading ? (
          <div className="text-[12px] text-text-dim animate-pulse">Checking system status…</div>
        ) : null}
      </div>

      {/* Ingest form */}
      <Card className="mb-8">
        <div className="text-[14px] font-semibold text-text-bright mb-1">Ingest Repository</div>
        <p className="text-[12px] text-text-dim mb-6">
          Add a repository to the platform. Metadata is optional and enriches topology graphs.
        </p>

        {/* Mode tabs */}
        <div className="flex gap-1 p-1 bg-white/[0.025] border border-white/[0.06] rounded-xl w-fit mb-6">
          {(["url", "path"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`px-4 py-1.5 text-[12px] font-semibold rounded-lg transition-all duration-150 ${
                mode === m
                  ? "bg-white/[0.07] text-text-bright shadow-sm"
                  : "text-text-dim hover:text-text"
              }`}
            >
              {m === "url" ? "Git URL" : "Local Path"}
            </button>
          ))}
        </div>

        {/* Main fields */}
        <div className="grid md:grid-cols-4 gap-3 mb-4">
          <div className="md:col-span-2">
            <label htmlFor="ingest-source" className="block text-[11px] font-medium text-text-dim mb-1.5">
              {mode === "url" ? "Repository URL" : "Local Path"}
            </label>
            <input
              id="ingest-source"
              type="text"
              placeholder={mode === "url" ? "https://github.com/org/repo.git" : "/repos/my-service"}
              value={mode === "url" ? urlInput : pathInput}
              onChange={(e) => mode === "url" ? setUrlInput(e.target.value) : setPathInput(e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label htmlFor="ingest-branch" className="block text-[11px] font-medium text-text-dim mb-1.5">Branch</label>
            <input
              id="ingest-branch"
              type="text"
              placeholder="HEAD"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label htmlFor="ingest-max-commits" className="block text-[11px] font-medium text-text-dim mb-1.5">Max commits</label>
            <input
              id="ingest-max-commits"
              type="number"
              min={10}
              max={500}
              value={maxCommits}
              onChange={(e) => setMaxCommits(Number(e.target.value))}
              className={INPUT_CLS}
            />
          </div>
        </div>

        {/* Optional metadata toggle */}
        <button
          type="button"
          onClick={() => setShowMeta(!showMeta)}
          className="flex items-center gap-2 text-[11.5px] font-medium text-text-dim hover:text-text transition-colors mb-4 group"
        >
          <ChevronDown
            size={13}
            className={`transition-transform duration-200 ${showMeta ? "rotate-180" : ""}`}
          />
          Optional metadata
        </button>

        {showMeta && (
          <div className="grid md:grid-cols-2 gap-3 mb-5 animate-fade-up">
            <div>
              <label htmlFor="meta-name" className="block text-[11px] font-medium text-text-dim mb-1.5">Service name</label>
              <input
                id="meta-name"
                type="text"
                placeholder="e.g. payment-service"
                value={repoName}
                onChange={(e) => setRepoName(e.target.value)}
                className={INPUT_CLS}
              />
            </div>
            <div>
              <label htmlFor="meta-team" className="block text-[11px] font-medium text-text-dim mb-1.5">Team</label>
              <input
                id="meta-team"
                type="text"
                placeholder="e.g. payments"
                value={team}
                onChange={(e) => setTeam(e.target.value)}
                className={INPUT_CLS}
              />
            </div>
            <div>
              <label htmlFor="meta-desc" className="block text-[11px] font-medium text-text-dim mb-1.5">Description</label>
              <textarea
                id="meta-desc"
                placeholder="What does this service do?"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className={`${INPUT_CLS} resize-none h-20`}
              />
            </div>
            <div>
              <label htmlFor="meta-tags" className="block text-[11px] font-medium text-text-dim mb-1.5">Tags</label>
              <input
                id="meta-tags"
                type="text"
                placeholder="api, payments, core (comma-separated)"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className={INPUT_CLS}
              />
            </div>
          </div>
        )}

        <div className="flex items-center gap-4">
          <Button type="button" onClick={handleIngest} disabled={ingesting}>
            {ingesting ? "Ingesting…" : `Ingest from ${mode === "url" ? "URL" : "path"}`}
          </Button>

          {ingestMsg && (
            <div
              className={`text-[12.5px] font-medium ${
                ingestMsg.ok ? "text-success" : "text-error"
              }`}
            >
              {ingestMsg.ok ? "✓ " : "✗ "}{ingestMsg.text}
            </div>
          )}
        </div>
      </Card>

      {/* Registered repos */}
      <div>
        <SectionTitle>Registered Repositories</SectionTitle>
        <p className="text-[12px] text-text-dim mb-5">
          Deleting a repository removes all associated chunks, commits, and profiles.
        </p>

        {deleteError && (
          <div className="mb-4 px-4 py-3 bg-error/[0.08] border border-error/[0.18] rounded-xl text-[12.5px] text-error">
            {deleteError}
          </div>
        )}

        {repos.length === 0 ? (
          <Card>
            <EmptyState
              title="No repositories ingested yet"
              description="Use the form above to add your first repository."
            />
          </Card>
        ) : (
          <div className="space-y-2.5">
            {repos.map((repo) => (
              <Card key={repo.id} className="group">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[13.5px] font-semibold text-text-bright">
                        {repo.name}
                      </span>
                      {repo.team && (
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-white/[0.04] border border-white/[0.07] text-text-dim">
                          {repo.team}
                        </span>
                      )}
                      {repo.tags && repo.tags.length > 0 && repo.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-accent/[0.06] border border-accent/[0.14] text-accent/70"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                    <div className="text-[11.5px] text-text-dim mt-1.5 flex items-center gap-2 flex-wrap">
                      <span>{repo.chunk_count.toLocaleString()} chunks</span>
                      <span className="text-text-dim/30">·</span>
                      <span>{repo.commit_count.toLocaleString()} commits</span>
                      {repo.last_ingested_at && (
                        <>
                          <span className="text-text-dim/30">·</span>
                          <span>last ingested {repo.last_ingested_at.slice(0, 10)}</span>
                        </>
                      )}
                    </div>
                    {repo.description && (
                      <div className="text-[11.5px] text-text-dim mt-1">{repo.description}</div>
                    )}
                  </div>
                  <Button
                    variant="danger"
                    size="sm"
                    type="button"
                    onClick={() => handleDelete(repo)}
                    className="shrink-0 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity"
                  >
                    <Trash2 size={12} />
                    Delete
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

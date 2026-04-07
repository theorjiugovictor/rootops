"use client";

import { useEffect, useState } from "react";
import { PageHeader, Metric, Card, Button, EmptyState, SectionTitle } from "@/components/ui";
import { SimilarityBar, RepoMetricsBar } from "@/components/charts";
import {
  getHealth,
  getIngestStatus,
  getLogStats,
  getRepositories,
  getDependencyGraph,
  queryCosebase,
  type Repository,
  type QuerySource,
} from "@/lib/api";
import { Search, Database, GitCommit, Layers, FileCode, ScrollText, Activity } from "lucide-react";

const STATE_LABELS: Record<string, string> = {
  idle:      "Ready",
  running:   "Ingesting",
  completed: "Ready",
  failed:    "Failed",
  unknown:   "–",
};

const CHIPS = [
  "Main entry points",
  "Authentication flow",
  "Error handling",
  "Database models",
  "Retry logic",
  "API endpoints",
  "Cross-service calls",
];

export default function DashboardPage() {
  const [health, setHealth]       = useState<Record<string, unknown>>({});
  const [stats, setStats]         = useState<Record<string, number>>({});
  const [state, setState]         = useState("unknown");
  const [repos, setRepos]         = useState<Repository[]>([]);
  const [logStats, setLogStats]   = useState<Record<string, unknown>>({});
  const [question, setQuestion]   = useState("");
  const [useLlm, setUseLlm]       = useState(true);
  const [searching, setSearching] = useState(false);
  const [result, setResult]       = useState<{
    answer?: string;
    sources?: QuerySource[];
  } | null>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => {});
    getIngestStatus().then((s) => {
      setStats((s.stats as Record<string, number>) ?? {});
      setState((s.state as string) ?? "unknown");
    }).catch(() => {});
    getLogStats().then(setLogStats).catch(() => {});
    getRepositories().then((r) => setRepos(r.repos)).catch(() => {});
    getDependencyGraph().catch(() => {});
  }, []);

  async function handleSearch() {
    if (!question.trim()) return;
    setSearching(true);
    const r = await queryCosebase({ question: question.trim(), top_k: 5, use_llm: useLlm });
    setResult(r);
    setSearching(false);
  }

  const repoCount  = repos.length;
  const stateLabel = STATE_LABELS[state] || state;

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle={`${repoCount} ${repoCount === 1 ? "repository" : "repositories"} · ${stateLabel}`}
        action={
          <div className="flex items-center gap-2 text-xs text-text-dim">
            <span
              className={`w-2 h-2 rounded-full ${
                health.ok
                  ? "bg-success shadow-[0_0_6px_rgba(16,185,129,0.5)]"
                  : "bg-error shadow-[0_0_6px_rgba(239,68,68,0.5)]"
              }`}
            />
            {health.ok ? "API connected" : "API offline"}
          </div>
        }
      />

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-10">
        <Metric label="Repositories" value={repoCount}
          icon={<Database size={12} />} />
        <Metric label="Commits"      value={(stats.commits_ingested ?? 0).toLocaleString()}
          icon={<GitCommit size={12} />} />
        <Metric label="Chunks"       value={(stats.chunks_ingested ?? 0).toLocaleString()}
          icon={<Layers size={12} />} />
        <Metric label="Files"        value={(stats.files_processed ?? 0).toLocaleString()}
          icon={<FileCode size={12} />} />
        <Metric
          label="Logs"
          value={logStats.ok ? ((logStats.total_entries as number) ?? 0).toLocaleString() : "–"}
          icon={<ScrollText size={12} />}
        />
        <Metric label="Status" value={stateLabel}
          icon={<Activity size={12} />}
          accent={state === "running"}
        />
      </div>

      {/* Two-column layout */}
      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left: Repos */}
        <div>
          {repos.length > 0 ? (
            <>
              <SectionTitle>Repositories</SectionTitle>
              <RepoMetricsBar repos={repos} />
            </>
          ) : (
            <Card>
              <EmptyState
                title="No repositories yet"
                description="Connect your first repository to start analysing code."
                action={
                  <a
                    href="/settings"
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-[12.5px] font-semibold bg-white/[0.05] border border-white/10 text-text hover:bg-white/[0.08] hover:border-white/[0.16] transition-all"
                  >
                    Go to Settings →
                  </a>
                }
              />
            </Card>
          )}
        </div>

        {/* Right: Search */}
        <div>
          <SectionTitle>Quick Search</SectionTitle>
          <p className="text-[12px] text-text-dim mb-4">
            Ask anything about your codebase — full conversations in{" "}
            <a href="/intelligence" className="text-accent/80 hover:text-accent transition-colors">
              Intelligence
            </a>
          </p>

          {/* Chips */}
          <div className="flex flex-wrap gap-1.5 mb-4">
            {CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => setQuestion(chip)}
                className="px-3 py-1.5 text-[11.5px] text-text-muted bg-white/[0.035] border border-white/[0.08] rounded-full hover:bg-accent-dim hover:border-accent/25 hover:text-accent transition-all duration-150"
              >
                {chip}
              </button>
            ))}
          </div>

          <div className="flex gap-2.5 mb-4">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-dim pointer-events-none" />
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="What does the payment processor do?"
                className="w-full pl-9 pr-4 py-2.5 bg-bg-input border border-white/[0.09] rounded-xl text-[13px] text-text placeholder:text-text-dim focus:border-accent/40 focus:ring-2 focus:ring-accent/[0.07] outline-none transition-all"
              />
            </div>
            <label className="flex items-center gap-2 text-[11.5px] text-text-muted cursor-pointer select-none shrink-0">
              <input
                type="checkbox"
                checked={useLlm}
                onChange={(e) => setUseLlm(e.target.checked)}
                className="accent-accent"
              />
              LLM
            </label>
          </div>

          <Button type="button" onClick={handleSearch} disabled={!question.trim() || searching}>
            {searching ? "Searching…" : "Search"}
          </Button>

          {result && (
            <div className="mt-6 space-y-4 animate-fade-up">
              {result.answer && (
                <Card className="border-accent/[0.15] bg-accent/[0.025]">
                  <div className="text-[13px] text-text leading-relaxed whitespace-pre-wrap">
                    {result.answer}
                  </div>
                </Card>
              )}
              {result.sources && result.sources.length > 0 && (
                <SimilarityBar sources={result.sources} title="Match Map" />
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

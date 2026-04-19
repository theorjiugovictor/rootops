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
  queryCodebase,
  type Repository,
  type QuerySource,
} from "@/lib/api";
import {
  Search,
  Database,
  GitCommit,
  Layers,
  FileCode,
  ScrollText,
  Activity,
  ArrowRight,
  GitBranch,
  Network,
} from "lucide-react";
import { Markdown } from "@/components/markdown";

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

interface GraphNode { id: string; name: string; team?: string; chunk_count: number; commit_count: number }
interface GraphEdge { id: string; source: string; target: string; source_name: string; target_name: string; dependency_type: string; confidence: number }

export default function DashboardPage() {
  const [health, setHealth]         = useState<Record<string, unknown>>({});
  const [stats, setStats]           = useState<Record<string, number>>({});
  const [state, setState]           = useState("unknown");
  const [repos, setRepos]           = useState<Repository[]>([]);
  const [logStats, setLogStats]     = useState<Record<string, unknown>>({});
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [question, setQuestion]     = useState("");
  const [useLlm, setUseLlm]         = useState(true);
  const [searching, setSearching]   = useState(false);
  const [result, setResult]         = useState<{ answer?: string; sources?: QuerySource[] } | null>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => {});
    getIngestStatus().then((s) => {
      setStats((s.stats as Record<string, number>) ?? {});
      setState((s.state as string) ?? "unknown");
    }).catch(() => {});
    getLogStats().then(setLogStats).catch(() => {});
    getRepositories().then((r) => setRepos(r.repos)).catch(() => {});
    getDependencyGraph().then((g) => {
      if (g.ok) {
        setGraphNodes((g.nodes as GraphNode[]) ?? []);
        setGraphEdges((g.edges as GraphEdge[]) ?? []);
      }
    }).catch(() => {});
  }, []);

  async function handleSearch() {
    if (!question.trim()) return;
    setSearching(true);
    const r = await queryCodebase({ question: question.trim(), top_k: 5, use_llm: useLlm });
    setResult(r);
    setSearching(false);
  }

  const repoCount  = repos.length;
  const stateLabel = STATE_LABELS[state] || state;
  const isBlank    = repoCount === 0 && state !== "running";

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

      {/* ── Onboarding wizard (shown only on fresh install) ─────── */}
      {isBlank && (
        <Card className="mb-8 border-accent/[0.18] bg-accent/[0.02]">
          <div className="text-[15px] font-semibold text-text-bright mb-1">
            Welcome to RootOps
          </div>
          <p className="text-[12.5px] text-text-dim mb-6 leading-relaxed">
            Follow these three steps to start getting AI-powered insights from your codebase.
          </p>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              {
                step: "1",
                title: "Connect a Repository",
                desc: "Go to Settings and paste a GitHub URL or local path.",
                href: "/settings",
                cta: "Go to Settings →",
              },
              {
                step: "2",
                title: "Ingest & Embed",
                desc: "RootOps chunks your code and builds a semantic vector index.",
                href: "/settings",
                cta: "Start Ingestion →",
              },
              {
                step: "3",
                title: "Ask Questions",
                desc: "Query your codebase in natural language or stream AI answers.",
                href: "/intelligence",
                cta: "Open Intelligence →",
              },
            ].map(({ step, title, desc, href, cta }) => (
              <div
                key={step}
                className="rounded-[12px] border border-white/[0.07] bg-white/[0.02] p-4 flex flex-col gap-3"
              >
                <div className="w-7 h-7 rounded-full bg-accent/[0.12] border border-accent/20 flex items-center justify-center text-[12px] font-bold text-accent">
                  {step}
                </div>
                <div>
                  <div className="text-[13px] font-semibold text-text-bright mb-1">{title}</div>
                  <p className="text-[12px] text-text-dim leading-relaxed">{desc}</p>
                </div>
                <a
                  href={href}
                  className="mt-auto inline-flex items-center gap-1 text-[12px] font-semibold text-accent hover:text-accent/80 transition-colors"
                >
                  {cta} <ArrowRight size={12} />
                </a>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ── Metrics ──────────────────────────────────────────────── */}
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

      {/* ── Two-column layout: repos + quick search ──────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-10">
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

        {/* Right: Quick Search */}
        <div>
          <SectionTitle>Quick Search</SectionTitle>
          <p className="text-[12px] text-text-dim mb-4">
            Ask anything about your codebase — full streaming conversations in{" "}
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
                  <div className="text-[13px] text-text leading-relaxed break-words">
                    <Markdown content={result.answer} />
                  </div>
                </Card>
              )}
              {result.sources && result.sources.length > 0 && (
                <SimilarityBar sources={result.sources} title="Source files" />
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Dependency Graph ─────────────────────────────────────── */}
      {graphNodes.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <SectionTitle>
              <span className="inline-flex items-center gap-1.5">
                <Network size={12} />
                Service Dependency Graph · {graphNodes.length} node{graphNodes.length !== 1 ? "s" : ""}
                {graphEdges.length > 0 && `, ${graphEdges.length} edge${graphEdges.length !== 1 ? "s" : ""}`}
              </span>
            </SectionTitle>
          </div>

          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
            {graphNodes.map((node) => {
              const outbound = graphEdges.filter((e) => e.source === node.id);
              const inbound  = graphEdges.filter((e) => e.target === node.id);

              return (
                <a
                  key={node.id}
                  href="/settings"
                  className="block rounded-[14px] border border-white/[0.07] bg-[rgba(8,8,12,0.8)] p-4 hover:border-accent/30 hover:bg-accent/[0.02] transition-all duration-150 group"
                >
                  <div className="flex items-start gap-3 mb-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent/20 to-info/20 border border-white/[0.08] flex items-center justify-center shrink-0">
                      <GitBranch size={13} className="text-accent/70" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[13px] font-semibold text-text-bright group-hover:text-accent transition-colors truncate">
                        {node.name}
                      </div>
                      {node.team && (
                        <div className="text-[10.5px] text-text-dim mt-0.5">{node.team}</div>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-3 text-[11px] text-text-dim mb-3">
                    <span>{node.chunk_count.toLocaleString()} chunks</span>
                    <span className="text-text-dim/30">·</span>
                    <span>{node.commit_count.toLocaleString()} commits</span>
                  </div>

                  {(outbound.length > 0 || inbound.length > 0) && (
                    <div className="space-y-1 pt-3 border-t border-white/[0.05]">
                      {outbound.slice(0, 3).map((e) => (
                        <div key={e.id} className="flex items-center gap-1.5 text-[11px]">
                          <span className="text-accent/50">→</span>
                          <span className="text-text-dim truncate">{e.target_name}</span>
                          <span className="ml-auto text-text-dim/50 shrink-0">{e.dependency_type}</span>
                        </div>
                      ))}
                      {inbound.slice(0, 2).map((e) => (
                        <div key={e.id} className="flex items-center gap-1.5 text-[11px]">
                          <span className="text-info/50">←</span>
                          <span className="text-text-dim truncate">{e.source_name}</span>
                        </div>
                      ))}
                      {(outbound.length + inbound.length) > 5 && (
                        <div className="text-[10.5px] text-text-dim/50">
                          +{outbound.length + inbound.length - 5} more
                        </div>
                      )}
                    </div>
                  )}
                </a>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}

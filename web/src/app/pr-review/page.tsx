"use client";

import { useState } from "react";
import { PageHeader, Card, Button, StatusBadge, EmptyState, SectionTitle } from "@/components/ui";
import { SimilarityBar, RiskScoreBar } from "@/components/charts";
import { getOpenPRs, getPRFiles, formatAge, type GitHubPR } from "@/lib/github";
import { queryCosebase, type QueryResult } from "@/lib/api";
import { ArrowLeft, GitPullRequest } from "lucide-react";

const DIMENSIONS = [
  { label: "Code Similarity",   prompt: "What code in the codebase is most similar to these changes?" },
  { label: "Known Bug Patterns", prompt: "Do these code changes introduce bugs, race conditions, or error-prone patterns?" },
  { label: "Idempotency",       prompt: "Could these changes cause duplicate operations or break idempotency?" },
  { label: "Data Integrity",    prompt: "Do these changes risk data consistency or incomplete rollbacks?" },
  { label: "Security",          prompt: "Are there security vulnerabilities — injection risks, auth bypasses, exposed secrets?" },
];

const INPUT_CLS =
  "w-full px-3.5 py-2.5 bg-bg-input border border-white/[0.09] rounded-xl text-[13px] text-text placeholder:text-text-dim focus:border-accent/40 focus:ring-2 focus:ring-accent/[0.07] outline-none transition-all";

export default function PRReviewPage() {
  const [owner, setOwner]   = useState("");
  const [repo, setRepo]     = useState("");
  const [token, setToken]   = useState("");
  const [prs, setPrs]       = useState<GitHubPR[]>([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");
  const [selectedPR, setSelectedPR] = useState<GitHubPR | null>(null);
  const [analysis, setAnalysis]   = useState<{
    dimensions: Record<string, QueryResult>;
    riskScore: number;
  } | null>(null);
  const [analysing, setAnalysing] = useState(false);
  const [useLlm, setUseLlm]       = useState(true);
  const [topK, setTopK]           = useState(4);

  async function fetchPRs() {
    if (!owner || !repo) return;
    setLoading(true);
    setError("");
    const res = await getOpenPRs(owner, repo, token || undefined);
    if (res.ok) setPrs(res.prs);
    else        setError(res.error || "Failed to fetch PRs");
    setLoading(false);
  }

  async function analyse(pr: GitHubPR) {
    setSelectedPR(pr);
    setAnalysing(true);
    setAnalysis(null);

    try {
      const filesRes = await getPRFiles(owner, repo, pr.number, token || undefined);
      if (!filesRes.ok) { setError(filesRes.error || "Failed to fetch PR files"); return; }

      const diffExcerpt = filesRes.diff.slice(0, 2000);
      const settled = await Promise.allSettled(
        DIMENSIONS.map((dim) =>
          queryCosebase({ question: `${dim.prompt}\n\n${diffExcerpt}`, top_k: topK, use_llm: useLlm }),
        ),
      );

      const results: Record<string, QueryResult> = {};
      DIMENSIONS.forEach((dim, i) => {
        const r = settled[i];
        results[dim.label] = r.status === "fulfilled" ? r.value : { ok: false };
      });

      const allSims = Object.values(results).flatMap((r) =>
        (r.sources || []).map((s) => s.similarity),
      );
      const raw = allSims.length
        ? Math.max(...allSims) * 60 + (allSims.reduce((a, b) => a + b, 0) / allSims.length) * 40
        : 0;

      setAnalysis({ dimensions: results, riskScore: Math.min(100, raw) });
    } finally {
      setAnalysing(false);
    }
  }

  // Analysis view
  if (selectedPR) {
    return (
      <>
        <PageHeader
          title="PR Review"
          subtitle="Semantic risk analysis on open pull requests"
          action={
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => { setSelectedPR(null); setAnalysis(null); setError(""); }}
            >
              <ArrowLeft size={13} />
              Back to list
            </Button>
          }
        />

        <Card className="mb-6">
          <div className="flex items-start gap-3">
            <GitPullRequest size={16} className="text-text-dim mt-0.5 shrink-0" />
            <div>
              <div className="text-[14.5px] font-semibold text-text-bright">
                #{selectedPR.number} {selectedPR.title}
              </div>
              <div className="text-[12px] text-text-dim mt-1 flex items-center gap-2 flex-wrap">
                <span>@{selectedPR.user?.login}</span>
                <span className="text-text-dim/30">·</span>
                <span>{formatAge(selectedPR.updated_at || "")}</span>
                {selectedPR.draft && <StatusBadge label="DRAFT" />}
              </div>
            </div>
          </div>
        </Card>

        {analysing && (
          <div className="text-[12.5px] text-text-dim animate-pulse mb-6">
            Running {DIMENSIONS.length}-dimension analysis…
          </div>
        )}

        {analysis && (
          <div className="space-y-5 animate-fade-up">
            <Card>
              <RiskScoreBar score={analysis.riskScore} />
            </Card>
            {Object.entries(analysis.dimensions).map(([label, res]) => (
              <Card key={label}>
                <div className="text-[13px] font-semibold text-text-bright mb-3">{label}</div>
                {res.answer && (
                  <div className="text-[12.5px] text-text-muted mb-4 whitespace-pre-wrap leading-relaxed">
                    {res.answer}
                  </div>
                )}
                {res.sources && res.sources.length > 0 && (
                  <SimilarityBar sources={res.sources} title="" />
                )}
              </Card>
            ))}
          </div>
        )}
      </>
    );
  }

  // PR list view
  return (
    <>
      <PageHeader
        title="PR Review"
        subtitle="Semantic risk analysis on open pull requests"
      />

      {/* Config */}
      <Card className="mb-7">
        <div className="grid md:grid-cols-3 gap-3">
          <div>
            <label className="block text-[11px] font-medium text-text-dim mb-1.5">Repository</label>
            <input
              type="text"
              placeholder="owner/repo"
              value={`${owner}${repo ? `/${repo}` : ""}`}
              onChange={(e) => {
                const parts = e.target.value.split("/");
                setOwner(parts[0] || "");
                setRepo(parts[1] || "");
              }}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-text-dim mb-1.5">GitHub token</label>
            <input
              type="password"
              placeholder="ghp_… (optional)"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div className="flex flex-col justify-end gap-3">
            <div className="flex items-center gap-3">
              <Button type="button" onClick={fetchPRs} disabled={loading || !owner || !repo}>
                {loading ? "Fetching…" : "Fetch PRs"}
              </Button>
              <label className="flex items-center gap-2 text-[12px] text-text-muted cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={useLlm}
                  onChange={(e) => setUseLlm(e.target.checked)}
                  className="accent-accent"
                />
                LLM
              </label>
              <div className="flex items-center gap-2 ml-auto">
                <span className="text-[11px] text-text-dim">k={topK}</span>
                <input
                  type="range"
                  min={2}
                  max={8}
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  aria-label="Number of sources"
                  className="w-16 accent-accent"
                />
              </div>
            </div>
          </div>
        </div>
      </Card>

      {error && (
        <div className="mb-6 px-4 py-3 bg-error/[0.08] border border-error/[0.18] rounded-xl text-[12.5px] text-error">
          {error}
        </div>
      )}

      {prs.length > 0 ? (
        <div className="space-y-2.5">
          <SectionTitle>{prs.length} open PR{prs.length > 1 ? "s" : ""} — {owner}/{repo}</SectionTitle>
          {prs.map((pr) => (
            <Card key={pr.number} className="group">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="text-[13.5px] font-semibold text-text-bright">
                      #{pr.number} {pr.title}
                    </span>
                    {pr.draft && <StatusBadge label="Draft" />}
                  </div>
                  <div className="text-[11.5px] text-text-dim flex items-center gap-1.5 flex-wrap">
                    <span>@{pr.user?.login}</span>
                    <span className="text-text-dim/30">·</span>
                    <span>{formatAge(pr.updated_at || "")}</span>
                    <span className="text-text-dim/30">·</span>
                    <span>{pr.changed_files ?? 0} file{pr.changed_files !== 1 ? "s" : ""}</span>
                    <span className="text-success">+{pr.additions ?? 0}</span>
                    <span className="text-error">−{pr.deletions ?? 0}</span>
                  </div>
                  {pr.labels && pr.labels.length > 0 && (
                    <div className="flex gap-1.5 mt-2 flex-wrap">
                      {pr.labels.map((l) => (
                        <span
                          key={l.name}
                          className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-white/[0.05] border border-white/[0.09] text-text-muted"
                        >
                          {l.name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <Button type="button" size="sm" onClick={() => analyse(pr)}>
                  Analyse
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : !loading && !error ? (
        <Card>
          <EmptyState
            title="No PRs loaded"
            description="Enter an owner/repo above and click Fetch PRs."
          />
        </Card>
      ) : null}
    </>
  );
}

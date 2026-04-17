"use client";

/**
 * RootOps — Chart / Visualisation Components
 *
 * Designed around what a developer actually needs:
 *   SimilarityBar  — expandable source file list showing which code was retrieved
 *   RepoMetricsBar — repo index summary with freshness + commit count
 *   RiskScoreBar   — codebase similarity gauge for PR analysis
 */

import { useEffect, useRef, useState } from "react";
import { FileCode, ChevronDown, GitBranch, Clock } from "lucide-react";
import { formatAge } from "@/lib/api";

// ── Similarity / Source List ────────────────────────────────────
// Replaces an opaque bar chart with an expandable list of the actual
// code chunks the RAG engine retrieved. Developers can read the code
// that generated the answer.

interface SourceItem {
  file_path: string;
  similarity: number;
  content?: string;
  start_line?: number;
  end_line?: number;
  language?: string;
  rerank_score?: number;
}

function scoreColor(sim: number): string {
  if (sim >= 0.7) return "text-success";
  if (sim >= 0.4) return "text-warning";
  return "text-text-dim";
}

function scoreBg(sim: number): string {
  if (sim >= 0.7) return "bg-success/[0.08] border-success/[0.18]";
  if (sim >= 0.4) return "bg-warning/[0.08] border-warning/[0.18]";
  return "bg-white/[0.03] border-white/[0.08]";
}

function SourceCard({ source }: { source: SourceItem }) {
  const [expanded, setExpanded] = useState(false);
  const pct = Math.round(source.similarity * 100);

  // Show only the last two path segments so long paths don't overflow
  const parts = source.file_path.replace(/\\/g, "/").split("/");
  const shortPath = parts.slice(-2).join("/");
  const fullPath  = source.file_path;

  return (
    <div className={`rounded-[10px] border overflow-hidden ${scoreBg(source.similarity)}`}>
      <button
        type="button"
        onClick={() => source.content ? setExpanded(!expanded) : undefined}
        className={`w-full flex items-center gap-2.5 px-3 py-2 text-left transition-colors ${
          source.content ? "hover:bg-white/[0.025] cursor-pointer" : "cursor-default"
        }`}
        title={fullPath}
      >
        <FileCode size={12} className="text-text-dim shrink-0" />

        {/* Path */}
        <span className="flex-1 text-[11.5px] font-mono text-text truncate" title={fullPath}>
          {shortPath}
        </span>

        {/* Line range */}
        {source.start_line != null && (
          <span className="text-[10.5px] text-text-dim shrink-0 tabular-nums">
            L{source.start_line}–{source.end_line ?? "?"}
          </span>
        )}

        {/* Score badge */}
        <span className={`text-[10.5px] font-bold shrink-0 tabular-nums ${scoreColor(source.similarity)}`}>
          {pct}%
        </span>

        {/* Expand toggle — only if there's content to show */}
        {source.content && (
          <ChevronDown
            size={11}
            className={`text-text-dim shrink-0 transition-transform duration-150 ${expanded ? "rotate-180" : ""}`}
          />
        )}
      </button>

      {/* Expandable code preview */}
      {expanded && source.content && (
        <pre className="text-[10.5px] text-text-muted font-mono leading-relaxed px-3 py-3 border-t border-white/[0.06] overflow-x-auto max-h-56 bg-[#06060A]">
          {source.content.trimEnd()}
        </pre>
      )}
    </div>
  );
}

export function SimilarityBar({
  sources,
  title = "Source files",
}: {
  sources: SourceItem[];
  title?: string;
}) {
  if (!sources.length) {
    return (
      <p className="text-[11.5px] text-text-dim py-2">No source files retrieved.</p>
    );
  }

  return (
    <div>
      {title && (
        <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim mb-2">
          {title}
        </div>
      )}
      <div className="space-y-1.5">
        {sources.map((s, i) => (
          <SourceCard key={i} source={s} />
        ))}
      </div>
      {sources.some((s) => s.content) && (
        <p className="text-[10px] text-text-dim/50 mt-1.5">
          Click a file to preview the retrieved code segment.
        </p>
      )}
    </div>
  );
}


// ── Repository Index Summary ────────────────────────────────────
// Replaces a "chunks vs commits" bar chart (meaningless to devs)
// with a plain list showing: repo name, commits indexed, index age.

interface RepoItem {
  name: string;
  chunk_count: number;
  commit_count: number;
  last_ingested_at?: string;
  team?: string;
}

export function RepoMetricsBar({ repos }: { repos: RepoItem[] }) {
  if (!repos.length) return null;

  return (
    <div className="space-y-2">
      {repos.map((r) => (
        <div
          key={r.name}
          className="flex items-center gap-3 px-3.5 py-2.5 rounded-[12px] border border-white/[0.07] bg-white/[0.01]"
        >
          {/* Icon */}
          <div className="w-7 h-7 rounded-lg bg-accent/[0.08] border border-accent/[0.12] flex items-center justify-center shrink-0">
            <GitBranch size={12} className="text-accent/60" />
          </div>

          {/* Name + team */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[13px] font-semibold text-text-bright truncate">
                {r.name}
              </span>
              {r.team && (
                <span className="px-1.5 py-0.5 rounded text-[9.5px] font-medium bg-white/[0.04] border border-white/[0.07] text-text-dim">
                  {r.team}
                </span>
              )}
            </div>
            <div className="text-[11px] text-text-dim mt-0.5 flex items-center gap-1.5 flex-wrap">
              <span>{r.commit_count.toLocaleString()} commits indexed</span>
              <span className="text-text-dim/30">·</span>
              <span>{r.chunk_count.toLocaleString()} segments</span>
            </div>
          </div>

          {/* Freshness */}
          {r.last_ingested_at && (
            <div className="flex items-center gap-1 text-[10.5px] text-text-dim shrink-0">
              <Clock size={10} />
              {formatAge(r.last_ingested_at)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}


// ── PR Codebase Similarity Gauge ────────────────────────────────
// Renamed from "Risk Score" — this measures how similar the PR diff
// is to existing indexed code, not an independent risk assessment.

export function RiskScoreBar({ score }: { score: number }) {
  const isHigh = score >= 70;
  const isMid  = score >= 40;

  const textCls = isHigh ? "text-error" : isMid ? "text-warning" : "text-success";
  const bgCls   = isHigh ? "bg-error"   : isMid ? "bg-warning"   : "bg-success";

  const label =
    isHigh
      ? "High similarity — touches well-trodden or sensitive code paths"
      : isMid
      ? "Moderate similarity — some overlap with existing patterns"
      : "Low similarity — mostly new code with little prior context";

  // Set --progress-w via ref so no inline `style` attribute is needed
  // (globals.css: .progress-fill { width: var(--progress-w, 0%) })
  const barRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    barRef.current?.style.setProperty("--progress-w", `${Math.min(100, Math.round(score))}%`);
  }, [score]);

  return (
    <div>
      <div className="flex items-baseline gap-2 mb-1">
        <span className={`text-2xl font-bold tabular-nums ${textCls}`}>
          {Math.round(score)}
        </span>
        <span className="text-[11px] text-text-dim">/ 100 codebase similarity</span>
      </div>
      <p className="text-[11px] text-text-dim mb-3 leading-relaxed">
        {label}. Measures how closely this diff resembles patterns already in
        your indexed codebase — not an independent security or risk verdict.
      </p>
      <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
        <div ref={barRef} className={`progress-fill h-full rounded-full transition-all duration-500 ${bgCls}`} />
      </div>
    </div>
  );
}

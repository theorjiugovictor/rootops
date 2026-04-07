/**
 * RootOps — Chart Components
 *
 * Recharts equivalents of ui/utils/charts.py Plotly figures.
 */

"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { similarityColor } from "@/lib/theme";

// ── Similarity Bar Chart ────────────────────────────────────────

interface SourceItem {
  file_path: string;
  similarity: number;
  start_line?: number;
  end_line?: number;
}

function shortenPath(fp: string): string {
  const parts = fp.replace(/\\/g, "/").split("/");
  return parts.slice(-2).join("/");
}

export function SimilarityBar({
  sources,
  title = "Source Match Map",
}: {
  sources: SourceItem[];
  title?: string;
}) {
  if (!sources.length) {
    return (
      <div className="text-center text-sm text-text-dim py-8">
        No sources retrieved
      </div>
    );
  }

  const data = sources.map((s) => ({
    name: shortenPath(s.file_path),
    score: Math.round(s.similarity * 100 * 10) / 10,
    range: `L${s.start_line ?? "?"}–${s.end_line ?? "?"}`,
    raw: s.similarity,
  }));

  return (
    <div>
      <div className="text-[13px] font-semibold text-text mb-3">{title}</div>
      <ResponsiveContainer width="100%" height={Math.max(180, sources.length * 44)}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 30 }}>
          <XAxis type="number" domain={[0, 100]} tick={{ fill: "#6B7280", fontSize: 11 }} />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: "#E2E8F0", fontSize: 11 }}
            width={160}
          />
          <Tooltip
            contentStyle={{
              background: "#121216",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value: number) => [`${value}%`, "Similarity"]}
          />
          <Bar dataKey="score" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={similarityColor(d.raw)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Repository Metrics Bar ──────────────────────────────────────

interface RepoItem {
  name: string;
  chunk_count: number;
  commit_count: number;
}

export function RepoMetricsBar({ repos }: { repos: RepoItem[] }) {
  if (!repos.length) return null;

  const data = repos.map((r) => ({
    name: r.name,
    chunks: r.chunk_count,
    commits: r.commit_count,
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, repos.length * 48)}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 30 }}>
        <XAxis type="number" tick={{ fill: "#6B7280", fontSize: 11 }} />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fill: "#E2E8F0", fontSize: 11 }}
          width={120}
        />
        <Tooltip
          contentStyle={{
            background: "#121216",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Bar dataKey="chunks" fill="#3B82F6" radius={[0, 4, 4, 0]} name="Chunks" />
        <Bar dataKey="commits" fill="#10B981" radius={[0, 4, 4, 0]} name="Commits" />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Risk Score Bar ──────────────────────────────────────────────

export function RiskScoreBar({ score }: { score: number }) {
  const color =
    score >= 70 ? "#EF4444" : score >= 40 ? "#F59E0B" : "#10B981";

  return (
    <div>
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-2xl font-bold" style={{ color }}>
          {Math.round(score)}
        </span>
        <span className="text-xs text-text-dim">/ 100 risk score</span>
      </div>
      <div className="h-2 bg-white/[0.06] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(100, score)}%`, background: color }}
        />
      </div>
    </div>
  );
}

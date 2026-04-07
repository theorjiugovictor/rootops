/**
 * RootOps — Design tokens & utility constants
 *
 * Mirrors ui/utils/theme.py colour maps.
 */

export const COLORS = {
  text: "#E2E8F0",
  muted: "#94A3B8",
  border: "rgba(255,255,255,0.08)",
  borderHover: "rgba(255,255,255,0.18)",
  bg: "#050505",
  bgCard: "rgba(18, 18, 22, 0.85)",
  bgInput: "rgba(255,255,255,0.04)",
  accent: "#00E5FF",
  accentDim: "rgba(0, 229, 255, 0.12)",
  accentGlow: "rgba(0, 229, 255, 0.35)",
  success: "#10B981",
  warning: "#F59E0B",
  error: "#EF4444",
  info: "#3B82F6",
} as const;

export const LEVEL_COLORS: Record<string, string> = {
  ERROR: "#EF4444",
  WARN: "#F59E0B",
  WARNING: "#F59E0B",
  INFO: "#3B82F6",
  DEBUG: "#64748B",
  TRACE: "#475569",
  FATAL: "#7F1D1D",
  CRITICAL: "#7F1D1D",
};

export const LANG_COLORS: Record<string, string> = {
  python: "#3B82F6",
  javascript: "#F59E0B",
  typescript: "#3B82F6",
  go: "#10B981",
  rust: "#F97316",
  java: "#EF4444",
  sql: "#8B5CF6",
  shell: "#94A3B8",
};

export function similarityColor(score: number): string {
  if (score >= 0.7) return COLORS.success;
  if (score >= 0.4) return COLORS.warning;
  return COLORS.error;
}

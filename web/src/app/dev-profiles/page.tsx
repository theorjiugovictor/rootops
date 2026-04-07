"use client";

import { useEffect, useState } from "react";
import { PageHeader, Card, Button, Metric, LangBadge, EmptyState, SectionTitle } from "@/components/ui";
import {
  getProfiles,
  getProfile,
  buildProfiles,
  getIngestStatus,
  type ProfileSummary,
  type ProfileDetail,
} from "@/lib/api";
import { ArrowLeft, Users } from "lucide-react";

export default function DevProfilesPage() {
  const [profiles, setProfiles]         = useState<ProfileSummary[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<string | null>(null);
  const [detail, setDetail]             = useState<ProfileDetail | null>(null);
  const [building, setBuilding]         = useState(false);
  const [buildMsg, setBuildMsg]         = useState<string | null>(null);
  const [chunks, setChunks]             = useState(0);
  const [detailError, setDetailError]   = useState<string | null>(null);

  function refresh() {
    getProfiles().then((r) => setProfiles(r.profiles));
    getIngestStatus().then((s) =>
      setChunks((s.stats as Record<string, number>)?.chunks_ingested ?? 0),
    );
  }

  useEffect(refresh, []);

  useEffect(() => {
    if (!selectedEmail) return;
    setDetailError(null);
    setDetail(null);
    getProfile(selectedEmail)
      .then((d) => {
        if (d.ok) setDetail(d as ProfileDetail);
        else      setDetailError(d.error || "Failed to load profile");
      })
      .catch((err) => setDetailError(err instanceof Error ? err.message : "Unexpected error"));
  }, [selectedEmail]);

  async function handleBuild() {
    setBuilding(true);
    setBuildMsg(null);
    try {
      const res = await buildProfiles();
      setBuildMsg(
        res.ok
          ? `Built ${(res.profiles_built as number) ?? 0} profile(s).`
          : res.error || "Failed",
      );
      refresh();
    } catch (err) {
      setBuildMsg(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setBuilding(false);
    }
  }

  // ── Loading / error state ──────────────────────────────────────
  if (selectedEmail && !detail) {
    return (
      <>
        <PageHeader title="Developer Profiles" subtitle="Coding DNA extracted from git history" />
        <Button type="button" variant="ghost" size="sm" onClick={() => { setSelectedEmail(null); setDetailError(null); }} className="mb-6">
          <ArrowLeft size={13} /> Back to team
        </Button>
        {detailError ? (
          <div className="px-4 py-3 bg-error/[0.08] border border-error/[0.18] rounded-xl text-[12.5px] text-error">
            {detailError}
          </div>
        ) : (
          <div className="text-[12.5px] text-text-dim animate-pulse">Loading profile…</div>
        )}
      </>
    );
  }

  // ── Detail view ────────────────────────────────────────────────
  if (selectedEmail && detail) {
    const langs     = (detail.primary_languages ?? {}) as Record<string, number>;
    const raw       = detail as unknown as Record<string, unknown>;
    const files     = ((raw.files_touched ?? {}) as Record<string, number>);
    const patterns  = detail.code_patterns ?? {};
    const totalLang = Object.values(langs).reduce((a, b) => a + b, 0);

    return (
      <>
        <PageHeader
          title={detail.author_name || selectedEmail}
          subtitle={`${detail.author_email} · ${detail.commit_count} commits · updated ${(detail.last_updated ?? "").slice(0, 10)}`}
          action={
            <Button type="button" variant="ghost" size="sm" onClick={() => { setSelectedEmail(null); setDetail(null); }}>
              <ArrowLeft size={13} /> Back
            </Button>
          }
        />

        {/* Stats + languages */}
        <div className="flex items-start gap-6 mb-8 flex-wrap">
          <div className="flex gap-3">
            <Metric label="Commits" value={detail.commit_count} />
            <Metric label="Files"   value={Object.keys(files).length} />
          </div>
          {Object.keys(langs).length > 0 && (
            <div className="flex gap-1.5 flex-wrap pt-1">
              {Object.keys(langs).slice(0, 8).map((l) => (
                <LangBadge key={l} lang={l} />
              ))}
            </div>
          )}
        </div>

        {/* Style fingerprint */}
        {detail.pattern_summary && (
          <div className="mb-8">
            <SectionTitle>Style Fingerprint</SectionTitle>
            <Card variant="inset">
              <div className="text-[13px] text-text-muted leading-relaxed whitespace-pre-wrap">
                {detail.pattern_summary}
              </div>
            </Card>
          </div>
        )}

        {/* Code patterns */}
        {Object.keys(patterns).length > 0 && (
          <div className="mb-8">
            <SectionTitle>Code Patterns</SectionTitle>
            <div className="grid md:grid-cols-2 gap-3">
              {Object.entries(patterns).map(([key, val]) => (
                <Card key={key} variant="inset">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-text-dim mb-2">
                    {key.replace(/_/g, " ")}
                  </div>
                  <div className="text-[12.5px] text-text-muted leading-relaxed">
                    {Array.isArray(val) ? (
                      <ul className="list-disc list-inside space-y-0.5">
                        {(val as string[]).map((item, i) => <li key={i}>{String(item)}</li>)}
                      </ul>
                    ) : typeof val === "object" && val != null ? (
                      <ul className="space-y-0.5">
                        {Object.entries(val as Record<string, unknown>).map(([k, v]) => (
                          <li key={k}><strong className="text-text-muted/80">{k}:</strong> {String(v)}</li>
                        ))}
                      </ul>
                    ) : (
                      String(val)
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Languages */}
        {Object.keys(langs).length > 0 && (
          <div className="mb-8">
            <SectionTitle>Languages</SectionTitle>
            <div className="space-y-3 max-w-lg">
              {Object.entries(langs)
                .sort(([, a], [, b]) => b - a)
                .map(([lang, count]) => {
                  const pct = totalLang ? Math.round((count / totalLang) * 100) : 0;
                  return (
                    <div key={lang} className="flex items-center gap-3">
                      <div className="w-20 shrink-0">
                        <LangBadge lang={lang} />
                      </div>
                      <div className="flex-1 h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                        <div
                          className="progress-fill h-full bg-gradient-to-r from-[#00C2DC] to-[#1B44C8] rounded-full"
                          style={{"--progress-w": `${pct}%`} as React.CSSProperties}
                        />
                      </div>
                      <span className="text-[11px] text-text-dim w-16 text-right shrink-0">
                        {count} ({pct}%)
                      </span>
                    </div>
                  );
                })}
            </div>
          </div>
        )}

        {/* Most-touched files */}
        {Object.keys(files).length > 0 && (
          <div>
            <SectionTitle>Most-Touched Files</SectionTitle>
            <div className="space-y-3 max-w-2xl">
              {Object.entries(files)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 15)
                .map(([fp, touches]) => {
                  const maxT  = Math.max(...Object.values(files));
                  const pct   = maxT ? Math.round((touches / maxT) * 100) : 0;
                  const short = fp.replace(/\\/g, "/").split("/").slice(-3).join("/");
                  return (
                    <div key={fp}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11.5px] text-text-dim font-mono truncate max-w-xs">{short}</span>
                        <span className="text-[10.5px] text-text-dim shrink-0 ml-3">{touches} commit{touches !== 1 ? "s" : ""}</span>
                      </div>
                      <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden">
                        <div
                          className="progress-fill h-full bg-accent/50 rounded-full"
                          style={{"--progress-w": `${pct}%`} as React.CSSProperties}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        )}
      </>
    );
  }

  // ── Team overview ──────────────────────────────────────────────
  return (
    <>
      <PageHeader
        title="Developer Profiles"
        subtitle="Coding patterns and language fingerprints extracted from git history"
        action={
          <div className="flex items-center gap-3">
            <Button type="button" onClick={handleBuild} disabled={building || !chunks}>
              <Users size={13} />
              {building ? "Building…" : "Build Profiles"}
            </Button>
            {buildMsg && (
              <span className="text-[12px] text-text-muted">{buildMsg}</span>
            )}
          </div>
        }
      />

      {!chunks && (
        <div className="mb-6 px-4 py-3 bg-white/[0.02] border border-white/[0.06] rounded-xl text-[12.5px] text-text-dim">
          Ingest a repository first before building profiles.
        </div>
      )}

      {profiles.length === 0 ? (
        <Card>
          <EmptyState
            title="No profiles yet"
            description="Click Build Profiles to analyse git history and generate developer coding fingerprints."
            action={
              <Button type="button" onClick={handleBuild} disabled={building || !chunks}>
                {building ? "Building…" : "Build Profiles"}
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="space-y-2.5">
          <SectionTitle>{profiles.length} developer{profiles.length > 1 ? "s" : ""}</SectionTitle>
          {profiles.map((p) => {
            const langs = p.primary_languages ?? {};
            return (
              <Card key={p.author_email} className="group">
                <div className="flex items-center gap-4">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-accent/20 to-info/20 border border-white/[0.08] flex items-center justify-center shrink-0 text-[13px] font-bold text-text-muted">
                    {(p.author_name || p.author_email).charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[13.5px] font-semibold text-text-bright">
                      {p.author_name}
                    </div>
                    <div className="text-[11.5px] text-text-dim mt-0.5 flex items-center gap-2">
                      <span className="truncate max-w-[200px]">{p.author_email}</span>
                      <span className="text-text-dim/30">·</span>
                      <span>{(p.last_updated ?? "").slice(0, 10)}</span>
                    </div>
                    {Object.keys(langs).length > 0 && (
                      <div className="flex gap-1 mt-1.5">
                        {Object.keys(langs).slice(0, 5).map((l) => (
                          <LangBadge key={l} lang={l} />
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <div className="text-center hidden sm:block">
                      <div className="text-[18px] font-bold text-text-bright">{p.commit_count}</div>
                      <div className="text-[9.5px] uppercase tracking-wide text-text-dim">Commits</div>
                    </div>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => setSelectedEmail(p.author_email)}
                    >
                      View
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}

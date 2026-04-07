"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader, Card, Button, LevelBadge, EmptyState } from "@/components/ui";
import { SimilarityBar } from "@/components/charts";
import {
  queryCosebase,
  getRepositories,
  type QueryPayload,
  type QueryResult,
  type Repository,
} from "@/lib/api";
import { Send, Trash2, SlidersHorizontal } from "lucide-react";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  result?: QueryResult;
}

const SUGGESTED = [
  "How are the services connected?",
  "What are the main entry points?",
  "How is error handling implemented?",
  "What database models exist?",
  "How do services communicate?",
  "Trace a request end-to-end",
  "What events are published?",
  "Where is authentication handled?",
];

export default function IntelligencePage() {
  const [messages, setMessages]       = useState<ChatMessage[]>([]);
  const [input, setInput]             = useState("");
  const [loading, setLoading]         = useState(false);
  const [repos, setRepos]             = useState<Repository[]>([]);
  const [scopedIds, setScopedIds]     = useState<string[]>([]);
  const [useLlm, setUseLlm]           = useState(true);
  const [topK, setTopK]               = useState(5);
  const [showConfig, setShowConfig]   = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getRepositories().then((r) => setRepos(r.repos));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const buildHistory = useCallback(
    (msgs: ChatMessage[]): QueryPayload["conversation_history"] =>
      msgs.slice(-10).map((m) => ({
        role:    m.role,
        content: m.role === "assistant" ? m.result?.answer || m.content : m.content,
      })),
    [],
  );

  async function send(text?: string) {
    const q = (text || input).trim();
    if (!q) return;
    setInput("");
    setLoading(true);

    const userMsg: ChatMessage = { role: "user", content: q };
    const current = [...messages, userMsg];
    setMessages(current);

    try {
      const res = await queryCosebase({
        question:             q,
        top_k:                topK,
        use_llm:              useLlm,
        conversation_history: buildHistory(current),
        repo_ids:             scopedIds.length ? scopedIds : undefined,
      });

      const answer = res.ok
        ? res.answer || ""
        : `Error: ${res.error || "Query failed"}`;

      setMessages([
        ...current,
        { role: "assistant", content: answer, result: res.ok ? res : undefined },
      ]);
    } catch (err) {
      setMessages([
        ...current,
        { role: "assistant", content: `Error: ${err instanceof Error ? err.message : "Unexpected error"}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="System Intelligence"
        subtitle="Hybrid RAG across code and logs — semantically searched, synthesised by LLM"
        action={
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setMessages([])}
              >
                <Trash2 size={12} />
                Clear
              </Button>
            )}
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setShowConfig(!showConfig)}
            >
              <SlidersHorizontal size={12} />
              Config
            </Button>
          </div>
        }
      />

      {/* Config panel (toggled) */}
      {showConfig && (
        <Card className="mb-6 animate-fade-up">
          <div className="flex flex-wrap gap-8">
            {repos.length > 0 && (
              <div>
                <div className="text-[11px] font-semibold text-text-dim uppercase tracking-wider mb-2">
                  Scope
                </div>
                <div className="flex flex-wrap gap-x-5 gap-y-1.5">
                  {repos.map((r) => (
                    <label key={r.id} className="flex items-center gap-2 text-[12.5px] text-text-muted cursor-pointer">
                      <input
                        type="checkbox"
                        checked={scopedIds.includes(r.id)}
                        onChange={(e) =>
                          setScopedIds(e.target.checked
                            ? [...scopedIds, r.id]
                            : scopedIds.filter((id) => id !== r.id)
                          )
                        }
                        className="accent-accent"
                      />
                      {r.name}
                    </label>
                  ))}
                </div>
              </div>
            )}
            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2 text-[12.5px] text-text-muted cursor-pointer">
                <input
                  type="checkbox"
                  checked={useLlm}
                  onChange={(e) => setUseLlm(e.target.checked)}
                  className="accent-accent"
                />
                LLM synthesis
              </label>
              <div className="flex items-center gap-3">
                <span className="text-[11px] text-text-dim">Sources: {topK}</span>
                <input
                  type="range"
                  min={1}
                  max={15}
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  aria-label="Number of sources"
                  className="w-24 accent-accent"
                />
              </div>
            </div>
          </div>
        </Card>
      )}

      <div className="flex gap-6">
        {/* Suggestions sidebar */}
        <aside className="hidden lg:block w-44 shrink-0">
          <div className="text-[10px] font-semibold tracking-widest uppercase text-text-dim/60 mb-2 px-1">
            Suggestions
          </div>
          <div className="space-y-px">
            {SUGGESTED.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => send(q)}
                className="w-full text-left px-3 py-2 text-[12px] text-[#4E5E72] hover:text-text-muted hover:bg-white/[0.03] rounded-lg transition-all duration-150 leading-snug"
              >
                {q}
              </button>
            ))}
          </div>
        </aside>

        {/* Chat */}
        <div className="flex-1 min-w-0 flex flex-col">
          {messages.length === 0 && (
            <Card className="mb-6 bg-white/[0.015]">
              <EmptyState
                title="Ask anything about your codebase."
                description="Search semantically across code and logs. Scope to a specific repo or ask globally."
              />
            </Card>
          )}

          <div className="space-y-4 mb-5">
            {messages.map((msg, i) => (
              <div key={i} className="flex gap-3 animate-fade-up">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-[10px] font-bold mt-0.5 ${
                    msg.role === "user"
                      ? "bg-info/20 text-info border border-info/20"
                      : "bg-accent/[0.1] text-accent border border-accent/20"
                  }`}
                >
                  {msg.role === "user" ? "U" : "◆"}
                </div>
                <div className="flex-1 min-w-0">
                  <Card className={msg.role === "user" ? "bg-white/[0.025]" : ""}>
                    <div className="text-[13px] text-text leading-relaxed whitespace-pre-wrap">
                      {msg.content || (
                        <span className="text-text-dim italic">No LLM answer — sources below.</span>
                      )}
                    </div>

                    {msg.result?.sources && msg.result.sources.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-white/[0.06]">
                        <SimilarityBar
                          sources={msg.result.sources}
                          title={`${msg.result.sources.length} source${msg.result.sources.length > 1 ? "s" : ""}`}
                        />
                      </div>
                    )}

                    {msg.result?.log_matches && msg.result.log_matches.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-white/[0.06]">
                        <div className="text-[10px] font-semibold uppercase tracking-widest text-text-dim mb-3">
                          {msg.result.log_matches.length} correlated log{msg.result.log_matches.length > 1 ? "s" : ""}
                        </div>
                        {msg.result.log_matches.map((lm, j) => (
                          <div key={j} className="mb-3">
                            <div className="flex items-center gap-2 mb-1.5">
                              <LevelBadge level={lm.level} />
                              <span className="text-[12px] font-semibold text-text">{lm.service_name}</span>
                              <span className="text-[11px] text-text-dim ml-auto">
                                {lm.timestamp?.slice(0, 19)} · {Math.round(lm.similarity * 100)}%
                              </span>
                            </div>
                            <pre className="text-[11px] text-text-muted bg-[#06060A] border border-white/[0.06] rounded-lg p-3 overflow-x-auto font-mono">
                              {lm.message}
                            </pre>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 animate-fade-up">
                <div className="w-7 h-7 rounded-full bg-accent/[0.1] text-accent border border-accent/20 flex items-center justify-center text-[10px] font-bold mt-0.5 animate-pulse">
                  ◆
                </div>
                <Card className="flex-1 bg-white/[0.015]">
                  <div className="flex items-center gap-2 text-[13px] text-text-dim">
                    <span className="animate-pulse">Thinking</span>
                    <span className="flex gap-1">
                      <span className="w-1 h-1 rounded-full bg-text-dim animate-bounce [animation-delay:0ms]" />
                      <span className="w-1 h-1 rounded-full bg-text-dim animate-bounce [animation-delay:150ms]" />
                      <span className="w-1 h-1 rounded-full bg-text-dim animate-bounce [animation-delay:300ms]" />
                    </span>
                  </div>
                </Card>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <div className="flex gap-2.5 sticky bottom-0 pt-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
              placeholder="Ask about your codebase…"
              className="flex-1 px-4 py-3 bg-bg-input border border-white/[0.09] rounded-xl text-[13px] text-text placeholder:text-text-dim focus:border-accent/40 focus:ring-2 focus:ring-accent/[0.07] outline-none transition-all"
              disabled={loading}
            />
            <Button
              type="button"
              onClick={() => send()}
              disabled={loading || !input.trim()}
            >
              <Send size={14} />
              Send
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader, Card, Button, LevelBadge, EmptyState } from "@/components/ui";
import { SimilarityBar } from "@/components/charts";
import {
  streamQuery,
  getRepositories,
  type QueryResult,
  type Repository,
} from "@/lib/api";
import { Send, Trash2, SlidersHorizontal } from "lucide-react";
import { Markdown } from "@/components/markdown";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
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

const LS_MESSAGES_KEY  = "rootops-intel-messages";
const LS_SCOPED_KEY    = "rootops-intel-scoped";
const LS_TOP_K_KEY     = "rootops-intel-topk";
const MAX_STORED_MSGS  = 50;

export default function IntelligencePage() {
  const [messages, setMessages]     = useState<ChatMessage[]>([]);
  const [input, setInput]           = useState("");
  const [streaming, setStreaming]   = useState(false);
  const [repos, setRepos]           = useState<Repository[]>([]);
  const [scopedIds, setScopedIds]   = useState<string[]>([]);
  const [useLlm]                    = useState(true);
  const [topK, setTopK]             = useState(5);
  const [showConfig, setShowConfig] = useState(false);
  const endRef  = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  // ── Restore state from localStorage ──────────────────────────
  useEffect(() => {
    try {
      const saved = localStorage.getItem(LS_MESSAGES_KEY);
      if (saved) {
        const parsed: ChatMessage[] = JSON.parse(saved);
        // Strip streaming flags from persisted messages
        setMessages(parsed.map((m) => ({ ...m, isStreaming: false })));
      }
    } catch { /* ignore parse errors */ }

    try {
      const savedIds = localStorage.getItem(LS_SCOPED_KEY);
      if (savedIds) setScopedIds(JSON.parse(savedIds));
    } catch { /* ignore */ }

    try {
      const savedK = localStorage.getItem(LS_TOP_K_KEY);
      if (savedK) setTopK(Number(savedK));
    } catch { /* ignore */ }
  }, []);

  // ── Persist messages (non-streaming only) ────────────────────
  useEffect(() => {
    const stable = messages.filter((m) => !m.isStreaming);
    if (stable.length === 0) return;
    try {
      localStorage.setItem(
        LS_MESSAGES_KEY,
        JSON.stringify(stable.slice(-MAX_STORED_MSGS)),
      );
    } catch { /* storage quota exceeded — silently skip */ }
  }, [messages]);

  // ── Persist config ────────────────────────────────────────────
  useEffect(() => {
    try { localStorage.setItem(LS_SCOPED_KEY, JSON.stringify(scopedIds)); } catch { /* ignore */ }
  }, [scopedIds]);

  useEffect(() => {
    try { localStorage.setItem(LS_TOP_K_KEY, String(topK)); } catch { /* ignore */ }
  }, [topK]);

  // ── Load repos ────────────────────────────────────────────────
  useEffect(() => {
    getRepositories().then((r) => setRepos(r.repos)).catch(() => {});
  }, []);

  // ── Auto-scroll ───────────────────────────────────────────────
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Build conversation history from prior messages ────────────
  const buildHistory = useCallback(
    (msgs: ChatMessage[]) =>
      msgs
        .filter((m) => !m.isStreaming)
        .slice(-10)
        .map((m) => ({
          role:    m.role,
          content: m.role === "assistant" ? m.result?.answer ?? m.content : m.content,
        })),
    [],
  );

  // ── Send a message (streaming) ────────────────────────────────
  async function send(text?: string) {
    const q = (text ?? input).trim();
    if (!q || streaming) return;
    setInput("");
    setStreaming(true);

    // Add user message
    const userMsg: ChatMessage = { role: "user", content: q };
    const priorMessages = [...messages, userMsg];
    setMessages(priorMessages);

    // Optimistic assistant placeholder
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", isStreaming: true },
    ]);

    let fullAnswer = "";
    let streamResult: QueryResult | undefined;
    let aborted = false;

    // Expose an abort handle so the Stop button can cancel
    const abortController = new AbortController();
    abortRef.current = () => {
      aborted = true;
      abortController.abort();
    };

    try {
      const gen = streamQuery({
        question:             q,
        top_k:                topK,
        use_llm:              useLlm,
        conversation_history: buildHistory(priorMessages),
        repo_ids:             scopedIds.length ? scopedIds : undefined,
      });

      for await (const event of gen) {
        if (aborted) break;

        if (event.type === "metadata") {
          streamResult = {
            ok:          true,
            sources:     event.data?.sources,
            log_matches: event.data?.log_matches,
            metadata:    event.data?.metadata,
          };
          // Show sources immediately, before tokens arrive
          setMessages((prev) => [
            ...prev.slice(0, -1),
            { role: "assistant", content: fullAnswer, isStreaming: true, result: streamResult },
          ]);
        } else if (event.type === "token") {
          fullAnswer += event.data ?? "";
          setMessages((prev) => [
            ...prev.slice(0, -1),
            { role: "assistant", content: fullAnswer, isStreaming: true, result: streamResult },
          ]);
        } else if (event.type === "error") {
          fullAnswer = `⚠️ ${event.data ?? "Stream error"}`;
          break;
        }
      }
    } catch {
      if (!aborted) fullAnswer = fullAnswer || "⚠️ Stream connection failed.";
    } finally {
      abortRef.current = null;
      setStreaming(false);
      // Finalise the assistant message (mark not-streaming so it persists)
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: "assistant",
          content: fullAnswer || "(no answer)",
          isStreaming: false,
          result: streamResult,
        },
      ]);
    }
  }

  function handleStop() {
    abortRef.current?.();
  }

  function clearHistory() {
    setMessages([]);
    try { localStorage.removeItem(LS_MESSAGES_KEY); } catch { /* ignore */ }
  }

  return (
    <>
      <PageHeader
        title="System Intelligence"
        subtitle="Streaming RAG across code and logs — real-time token-by-token synthesis"
        action={
          <div className="flex items-center gap-2">
            {streaming ? (
              <Button type="button" variant="danger" size="sm" onClick={handleStop}>
                Stop
              </Button>
            ) : messages.length > 0 ? (
              <Button type="button" variant="ghost" size="sm" onClick={clearHistory}>
                <Trash2 size={12} />
                Clear
              </Button>
            ) : null}
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

      {/* Config panel */}
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
                            : scopedIds.filter((id) => id !== r.id))
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
              <div className="flex items-center gap-3">
                <span className="text-[11px] text-text-dim">Sources: {topK}</span>
                <input
                  type="range" min={1} max={15} value={topK}
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
                disabled={streaming}
                className="w-full text-left px-3 py-2 text-[12px] text-[#4E5E72] hover:text-text-muted hover:bg-white/[0.03] rounded-lg transition-all duration-150 leading-snug disabled:opacity-40 disabled:cursor-not-allowed"
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
                description="Responses stream token-by-token. Scope to a specific repo or ask globally. Conversation history is preserved across page refreshes."
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
                    <div className="text-[13px] text-text leading-relaxed">
                      {msg.content ? (
                        msg.role === "assistant" ? (
                          <Markdown content={msg.content} />
                        ) : (
                          <span className="whitespace-pre-wrap">{msg.content}</span>
                        )
                      ) : (
                        msg.isStreaming
                          ? <span className="flex items-center gap-1.5 text-text-dim">
                              <span className="animate-pulse">Thinking</span>
                              <span className="flex gap-1">
                                {(["[animation-delay:0ms]", "[animation-delay:150ms]", "[animation-delay:300ms]"] as const).map((delay) => (
                                  <span
                                    key={delay}
                                    className={`w-1 h-1 rounded-full bg-text-dim animate-bounce ${delay}`}
                                  />
                                ))}
                              </span>
                            </span>
                          : <span className="text-text-dim italic">No answer</span>
                      )}
                      {/* Streaming cursor */}
                      {msg.isStreaming && msg.content && (
                        <span className="inline-block w-0.5 h-4 bg-accent/80 ml-0.5 animate-pulse align-middle" />
                      )}
                    </div>

                    {/* Code sources */}
                    {msg.result?.sources && msg.result.sources.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-white/[0.06]">
                        <SimilarityBar
                          sources={msg.result.sources}
                          title={`${msg.result.sources.length} source${msg.result.sources.length > 1 ? "s" : ""}`}
                        />
                      </div>
                    )}

                    {/* Correlated log entries */}
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
            <div ref={endRef} />
          </div>

          {/* Input bar */}
          <div className="flex gap-2.5 sticky bottom-0 pt-2 pb-1">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
              placeholder="Ask about your codebase…"
              disabled={streaming}
              className="flex-1 px-4 py-3 bg-bg-input border border-white/[0.09] rounded-xl text-[13px] text-text placeholder:text-text-dim focus:border-accent/40 focus:ring-2 focus:ring-accent/[0.07] outline-none transition-all disabled:opacity-60"
            />
            <Button
              type="button"
              onClick={() => send()}
              disabled={streaming || !input.trim()}
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

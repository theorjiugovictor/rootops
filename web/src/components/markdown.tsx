"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

const customTheme = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...oneDark['pre[class*="language-"]'],
    background: "#06060A",
    margin: "0",
    padding: "1rem",
    borderRadius: "0.5rem",
    fontSize: "12px",
    lineHeight: "1.6",
  },
  'code[class*="language-"]': {
    ...oneDark['code[class*="language-"]'],
    background: "transparent",
    fontSize: "12px",
  },
};

/**
 * Renders markdown content with syntax-highlighted code blocks,
 * GFM tables, and styling that matches the RootOps dark theme.
 */
export function Markdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // ── Code blocks & inline code ─────────────────────────
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const text = String(children).replace(/\n$/, "");

          // Fenced code block (has language class from parent <pre>)
          if (match) {
            return (
              <SyntaxHighlighter
                style={customTheme}
                language={match[1]}
                PreTag="div"
              >
                {text}
              </SyntaxHighlighter>
            );
          }

          // Multi-line code without language — still use highlighter
          if (text.includes("\n")) {
            return (
              <SyntaxHighlighter
                style={customTheme}
                language="text"
                PreTag="div"
              >
                {text}
              </SyntaxHighlighter>
            );
          }

          // Inline code
          return (
            <code
              className="px-1.5 py-0.5 rounded bg-white/[0.06] text-accent text-[12px] font-mono"
              {...props}
            >
              {children}
            </code>
          );
        },

        // ── Suppress <pre> wrapper (SyntaxHighlighter handles it) ─
        pre({ children }) {
          return <>{children}</>;
        },

        // ── Headings ──────────────────────────────────────────────
        h1: ({ children }) => (
          <h3 className="text-[15px] font-bold text-text mt-5 mb-2 first:mt-0">{children}</h3>
        ),
        h2: ({ children }) => (
          <h4 className="text-[13.5px] font-semibold text-text mt-4 mb-1.5 first:mt-0">{children}</h4>
        ),
        h3: ({ children }) => (
          <h5 className="text-[13px] font-semibold text-text-muted mt-3 mb-1 first:mt-0">{children}</h5>
        ),

        // ── Paragraphs ───────────────────────────────────────────
        p: ({ children }) => (
          <p className="text-[13px] text-text leading-relaxed mb-2.5 last:mb-0">{children}</p>
        ),

        // ── Lists ─────────────────────────────────────────────────
        ul: ({ children }) => (
          <ul className="list-disc list-outside ml-5 mb-2.5 space-y-1 text-[13px] text-text">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-outside ml-5 mb-2.5 space-y-1 text-[13px] text-text">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="leading-relaxed">{children}</li>
        ),

        // ── Tables (GFM) ──────────────────────────────────────────
        table: ({ children }) => (
          <div className="overflow-x-auto mb-3 rounded-lg border border-white/[0.08]">
            <table className="w-full text-[12px]">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-white/[0.04] text-text-dim">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left font-semibold text-[11px] uppercase tracking-wider border-b border-white/[0.08]">{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2 text-text-muted border-b border-white/[0.04]">{children}</td>
        ),

        // ── Block quotes ──────────────────────────────────────────
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-accent/40 pl-4 my-2.5 text-text-muted italic">{children}</blockquote>
        ),

        // ── Horizontal rule ───────────────────────────────────────
        hr: () => <hr className="border-white/[0.08] my-4" />,

        // ── Bold / emphasis ───────────────────────────────────────
        strong: ({ children }) => (
          <strong className="font-semibold text-text">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="text-text-muted">{children}</em>
        ),

        // ── Links ─────────────────────────────────────────────────
        a: ({ href, children }) => (
          <a href={href} className="text-accent hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

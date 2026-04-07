"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Brain,
  GitPullRequest,
  FileText,
  Zap,
  Users,
  Settings,
  Hexagon,
} from "lucide-react";
import { clsx } from "clsx";

const NAV_SECTIONS = [
  {
    label: "Core",
    items: [
      { href: "/",             label: "Dashboard",    icon: LayoutDashboard },
      { href: "/intelligence", label: "Intelligence", icon: Brain },
      { href: "/pr-review",    label: "PR Review",    icon: GitPullRequest },
    ],
  },
  {
    label: "Tools",
    items: [
      { href: "/logs",         label: "Log Ingest",   icon: FileText },
      { href: "/auto-heal",    label: "Auto-Heal",    icon: Zap },
      { href: "/dev-profiles", label: "Dev Profiles", icon: Users },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex w-[216px] shrink-0 flex-col border-r border-white/[0.055] bg-[#05050A] relative overflow-hidden">
      {/* Top ambient glow */}
      <div className="absolute top-0 left-0 right-0 h-32 bg-gradient-to-b from-[rgba(0,217,245,0.04)] to-transparent pointer-events-none" />

      {/* Brand */}
      <div className="relative px-5 pt-6 pb-5">
        <div className="flex items-center gap-3">
          <div className="relative w-8 h-8 rounded-[9px] bg-gradient-to-br from-[#00C8E8] to-[#1B44C8] flex items-center justify-center shrink-0 shadow-[0_0_14px_rgba(0,200,232,0.35)]">
            <Hexagon size={14} className="text-white" fill="rgba(255,255,255,0.15)" strokeWidth={2.5} />
          </div>
          <div>
            <div className="text-[14px] font-bold tracking-tight text-text-bright leading-none">
              RootOps
            </div>
            <div className="text-[10px] text-text-dim leading-none mt-[5px]">
              AI-Native Platform
            </div>
          </div>
        </div>
      </div>

      <div className="h-px bg-white/[0.05] mx-4" />

      {/* Navigation */}
      <nav className="relative flex-1 px-3 py-4 space-y-5 overflow-y-auto">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <div className="px-3 mb-1.5 text-[9.5px] font-bold tracking-[0.14em] uppercase text-text-dim/60 select-none">
              {section.label}
            </div>
            <div className="space-y-px">
              {section.items.map(({ href, label, icon: Icon }) => {
                const active =
                  href === "/" ? pathname === "/" : pathname.startsWith(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    className={clsx(
                      "relative flex items-center gap-2.5 px-3 py-[7px] rounded-lg text-[12.5px] font-medium transition-all duration-150",
                      active
                        ? "bg-accent/[0.08] text-accent"
                        : "text-[#4E5E72] hover:text-[#9AAABB] hover:bg-white/[0.03]"
                    )}
                  >
                    {active && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[2.5px] h-[18px] bg-accent rounded-r-full shadow-[0_0_6px_rgba(0,217,245,0.6)]" />
                    )}
                    <Icon
                      size={14}
                      strokeWidth={active ? 2.2 : 1.8}
                      className="shrink-0"
                    />
                    {label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="h-px bg-white/[0.05] mx-4" />

      {/* Footer */}
      <div className="px-5 py-3.5">
        <div className="text-[10px] font-mono text-text-dim/40 truncate">
          {process.env.NEXT_PUBLIC_API_URL || "localhost:8000"}
        </div>
      </div>
    </aside>
  );
}

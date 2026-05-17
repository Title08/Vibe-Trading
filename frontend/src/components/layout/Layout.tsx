import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useSearchParams } from "react-router-dom";
import {
  BarChart3,
  Bot,
  Moon,
  Sun,
  Plus,
  Trash2,
  Pencil,
  MessageSquare,
  ChevronsLeft,
  ChevronsRight,
  Settings,
  Layers,
  GitCompare,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { useDarkMode } from "@/hooks/useDarkMode";
import { api, type SessionItem } from "@/lib/api";
import { useAgentStore } from "@/stores/agent";
import { ConnectionBanner } from "@/components/layout/ConnectionBanner";

// Bump on each release; one place keeps the footer in sync with package.json.
const APP_VERSION = "v0.1.8";

// NAV entries: `key` looks up label in i18n; `label` overrides (used for "Alpha Zoo").
const NAV = [
  { to: "/agent", icon: Bot, key: "agent" as const, label: null },
  { to: "/", icon: BarChart3, key: "home" as const, label: null },
  {
    to: "/compare",
    icon: GitCompare,
    key: "strategyComparison" as const,
    label: null,
  },
  {
    to: "/alpha-zoo",
    icon: Layers,
    key: "alphaZoo" as const,
    label: "Alpha Zoo",
  },
  {
    to: "/correlation",
    icon: Activity,
    key: "correlation" as const,
    label: null,
  },
  { to: "/settings", icon: Settings, key: "settings" as const, label: null },
];

export function Layout() {
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const { t } = useI18n();
  const { dark, toggle } = useDarkMode();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const sseStatus = useAgentStore((s) => s.sseStatus);
  const sseRetryAttempt = useAgentStore((s) => s.sseRetryAttempt);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("qa-sidebar") === "collapsed",
  );

  const activeSessionId = searchParams.get("session");

  useEffect(() => {
    localStorage.setItem("qa-sidebar", collapsed ? "collapsed" : "expanded");
  }, [collapsed]);

  const loadSessions = () => {
    api
      .listSessions()
      .then((list) => setSessions(Array.isArray(list) ? list : []))
      .catch(() => {})
      .finally(() => setSessionsLoading(false));
  };

  // Load sessions on mount. Also refresh when navigating TO /agent or when
  // the active session changes (covers new session creation from Agent).
  const isAgentPage = pathname.startsWith("/agent");
  useEffect(() => {
    loadSessions();
  }, [isAgentPage, activeSessionId]);

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [renameTarget, setRenameTarget] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const deleteSession = async (sid: string) => {
    try {
      await api.deleteSession(sid);
      setSessions((prev) => prev.filter((s) => s.session_id !== sid));
    } catch {
      /* ignore */
    }
    setDeleteTarget(null);
  };

  const renameSession = async (sid: string) => {
    if (!renameValue.trim()) {
      setRenameTarget(null);
      return;
    }
    try {
      await api.renameSession(sid, renameValue.trim());
      setSessions((prev) =>
        prev.map((s) =>
          s.session_id === sid ? { ...s, title: renameValue.trim() } : s,
        ),
      );
    } catch {
      /* ignore */
    }
    setRenameTarget(null);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* Sidebar */}
      <aside
        className={cn(
          "glass-panel-soft z-20 flex shrink-0 flex-col border-y-0 border-l-0 transition-all duration-200",
          collapsed ? "w-12" : "w-14 sm:w-64",
        )}
      >
        {/* Brand */}
        <div
          className={cn(
            "border-b border-border/60",
            collapsed ? "p-2 flex justify-center" : "p-4",
          )}
        >
          <Link
            to="/agent"
            className={cn(
              "flex items-center font-bold tracking-tight",
              collapsed ? "justify-center" : "gap-3",
            )}
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-primary/30 bg-primary/15 shadow-[0_0_28px_-12px_hsl(var(--primary))]">
              <BarChart3 className="h-4 w-4 text-primary" />
            </span>
            {!collapsed && (
              <span className="hidden min-w-0 sm:block">
                <span className="block text-sm leading-tight text-foreground">
                  Vibe-Trading
                </span>
                <span className="block text-[10px] font-medium uppercase tracking-[0.18em] text-signal">
                  Agent Desk
                </span>
              </span>
            )}
          </Link>
        </div>

        {/* Nav */}
        <nav className={cn("space-y-1", collapsed ? "p-1.5" : "p-2.5")}>
          {NAV.map(({ to, icon: Icon, key, label }) => {
            const text = label ?? t[key];
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  "group flex items-center rounded-lg text-sm transition-colors cursor-pointer",
                  collapsed
                    ? "justify-center p-2"
                    : "justify-center p-2 sm:justify-start sm:gap-3 sm:px-3 sm:py-2.5",
                  (to === "/" ? pathname === "/" : pathname.startsWith(to))
                    ? "border border-primary/25 bg-primary/15 text-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] font-medium"
                    : "border border-transparent text-muted-foreground hover:border-border/70 hover:bg-muted/40 hover:text-foreground",
                )}
                title={collapsed ? text : undefined}
              >
                <Icon
                  className="h-4 w-4 shrink-0 transition-colors group-hover:text-primary"
                  aria-hidden="true"
                />
                {!collapsed && <span className="hidden sm:inline">{text}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Sessions — hidden when collapsed */}
        {!collapsed && (
          <div className="mt-2 hidden flex-1 flex-col overflow-auto border-t border-border/60 sm:flex">
            <div className="flex items-center justify-between px-4 py-3">
              <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <MessageSquare className="h-3.5 w-3.5" />
                {t.sessions}
              </span>
              <Link
                to="/agent"
                className="flex items-center gap-1 rounded-md p-1 text-xs text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary cursor-pointer"
                title={t.newChat}
              >
                <Plus className="h-3.5 w-3.5" />
              </Link>
            </div>

            <div className="flex-1 space-y-1 overflow-auto px-2 pb-3">
              {sessionsLoading ? (
                <div className="space-y-1.5 px-2 py-1">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-8 rounded-lg bg-muted/50 animate-pulse"
                    />
                  ))}
                </div>
              ) : sessions.length === 0 ? (
                <p className="px-3 py-2 text-xs text-muted-foreground/60">
                  {t.noSessions}
                </p>
              ) : null}
              {sessions.map((s) => {
                const isActive = s.session_id === activeSessionId;
                const isDeleting = deleteTarget === s.session_id;
                const isRenaming = renameTarget === s.session_id;
                return (
                  <div
                    key={s.session_id}
                    className="group relative flex items-center"
                  >
                    {isRenaming ? (
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") renameSession(s.session_id);
                          if (e.key === "Escape") setRenameTarget(null);
                        }}
                        onBlur={() => renameSession(s.session_id)}
                        className="min-w-0 flex-1 rounded-lg border border-primary bg-background px-3 py-1.5 text-xs outline-none"
                      />
                    ) : (
                      <Link
                        to={`/agent?session=${s.session_id}`}
                        className={cn(
                          "block min-w-0 flex-1 rounded-lg border px-3 py-2 pr-14 text-xs transition-colors truncate cursor-pointer",
                          isActive
                            ? "border-primary/30 bg-primary/10 text-primary font-medium"
                            : "border-transparent text-muted-foreground hover:border-border/60 hover:bg-muted/40 hover:text-foreground",
                        )}
                        title={s.title || s.session_id}
                      >
                        <span className="flex items-center gap-1.5">
                          <span
                            className={cn(
                              "h-1.5 w-1.5 rounded-full shrink-0 shadow-[0_0_14px_currentColor]",
                              s.status === "failed"
                                ? "bg-danger"
                                : isActive
                                  ? "bg-warning"
                                  : "bg-success/60",
                            )}
                          />
                          {s.title || s.session_id.slice(0, 16)}
                        </span>
                      </Link>
                    )}
                    {!isRenaming && isDeleting ? (
                      <div className="absolute right-0.5 flex items-center gap-0.5">
                        <button
                          onClick={() => deleteSession(s.session_id)}
                          className="rounded p-1 text-[10px] font-medium text-danger hover:bg-danger/10 cursor-pointer"
                        >
                          {t.confirmDelete}
                        </button>
                        <button
                          onClick={() => setDeleteTarget(null)}
                          className="rounded p-1 text-[10px] text-muted-foreground hover:bg-muted cursor-pointer"
                        >
                          {t.cancelDelete}
                        </button>
                      </div>
                    ) : !isRenaming ? (
                      <div className="absolute right-1 opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setRenameTarget(s.session_id);
                            setRenameValue(s.title || "");
                          }}
                          className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer"
                          title="Rename"
                        >
                          <Pencil className="h-3 w-3" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setDeleteTarget(s.session_id);
                          }}
                          className="rounded p-1 text-muted-foreground hover:bg-danger/10 hover:text-danger cursor-pointer"
                          title={t.deleteConfirm}
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Spacer when collapsed */}
        {collapsed && <div className="flex-1" />}
        {!collapsed && <div className="flex-1 sm:hidden" />}

        {/* Footer */}
        <div
          className={cn(
            "border-t border-border/60",
            collapsed
              ? "p-1 flex flex-col items-center gap-1"
              : "p-1 sm:p-3 sm:space-y-2",
          )}
        >
          {collapsed ? (
            <>
              <button
                onClick={toggle}
                className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground cursor-pointer"
                title={dark ? t.lightMode : t.darkMode}
              >
                {dark ? (
                  <Sun className="h-3.5 w-3.5" />
                ) : (
                  <Moon className="h-3.5 w-3.5" />
                )}
              </button>
              <button
                onClick={() => setCollapsed(false)}
                className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground cursor-pointer"
                title="Expand"
              >
                <ChevronsRight className="h-3.5 w-3.5" />
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <button
                  onClick={toggle}
                  className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground cursor-pointer"
                >
                  {dark ? (
                    <Sun className="h-3.5 w-3.5" />
                  ) : (
                    <Moon className="h-3.5 w-3.5" />
                  )}
                  <span className="hidden sm:inline">
                    {dark ? t.lightMode : t.darkMode}
                  </span>
                </button>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setCollapsed(true)}
                    className="rounded p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground cursor-pointer"
                    title="Collapse"
                  >
                    <ChevronsLeft className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              <p className="hidden px-2 text-xs text-muted-foreground/60 sm:block">
                {APP_VERSION}
              </p>
            </>
          )}
        </div>
      </aside>

      {/* Main */}
      <div className="relative flex w-[calc(100vw-3.5rem)] min-w-0 flex-1 flex-col overflow-hidden sm:w-auto">
        <ConnectionBanner status={sseStatus} retryAttempt={sseRetryAttempt} />
        <main className="min-w-0 flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

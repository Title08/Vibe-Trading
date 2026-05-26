import { memo, useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { BarChart3, Code2, FileText, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { AgentAvatar } from "./AgentAvatar";
import { MetricsCard } from "./MetricsCard";
import { MiniEquityChart } from "@/components/charts/MiniEquityChart";
import { PineScriptViewer } from "./PineScriptViewer";
import type { AgentMessage } from "@/types/agent";

interface Props {
  msg: AgentMessage;
}

export const RunCompleteCard = memo(function RunCompleteCard({ msg }: Props) {
  const [metrics, setMetrics] = useState(msg.metrics);
  const [curve, setCurve] = useState(msg.equityCurve);
  const [pineCode, setPineCode] = useState<string | null>(null);
  const [pineLoading, setPineLoading] = useState(false);
  const [showPine, setShowPine] = useState(false);
  const [pineChecked, setPineChecked] = useState(false);
  const [pineExists, setPineExists] = useState(false);

  useEffect(() => {
    if (msg.metrics) setMetrics(msg.metrics);
  }, [msg.metrics]);

  useEffect(() => {
    if (msg.equityCurve) setCurve(msg.equityCurve);
  }, [msg.equityCurve]);

  useEffect(() => {
    if ((!metrics || !curve) && msg.runId) {
      api.getRun(msg.runId).then(r => {
        if (!metrics && r.metrics) setMetrics(r.metrics);
        if (!curve && r.equity_curve) setCurve(r.equity_curve.map(e => ({ time: e.time, equity: e.equity })));
      }).catch(() => {});
    }
  }, [msg.runId, metrics, curve]);

  // Check if Pine Script exists for this run (skip for shadow-only cards with no runId)
  useEffect(() => {
    if (!msg.runId) {
      setPineChecked(true);
      return;
    }
    if (!pineChecked) {
      api.getRunPine(msg.runId).then(r => {
        setPineChecked(true);
        if (r.exists && r.content) {
          setPineExists(true);
          setPineCode(r.content);
        }
      }).catch(() => { setPineChecked(true); });
    }
  }, [msg.runId, pineChecked]);

  const handlePineClick = useCallback(async () => {
    if (pineCode) {
      setShowPine(true);
      return;
    }
    if (!msg.runId) return;
    setPineLoading(true);
    try {
      const r = await api.getRunPine(msg.runId);
      if (r.exists && r.content) {
        setPineCode(r.content);
        setPineExists(true);
        setShowPine(true);
      }
    } catch { /* ignore */ }
    finally { setPineLoading(false); }
  }, [pineCode, msg.runId]);

  return (
    <div className="flex gap-3">
      <AgentAvatar />
      <div className="glass-panel-soft min-w-0 flex-1 space-y-3 rounded-xl p-3">
        {metrics && Object.keys(metrics).length > 0 && (
          <MetricsCard metrics={metrics} compact />
        )}
        {curve && curve.length > 1 && (
          <MiniEquityChart data={curve} height={80} />
        )}
        <div className="flex flex-wrap items-center gap-2">
          {msg.runId && (
            <Link
              to={`/runs/${msg.runId}`}
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-primary/25 bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-primary/15"
            >
              <BarChart3 className="h-3.5 w-3.5" />
              Full Report →
            </Link>
          )}
          {pineExists && (
            <button
              onClick={handlePineClick}
              disabled={pineLoading}
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-emerald-500/25 bg-emerald-500/10 px-3 py-1.5 text-sm font-medium text-emerald-600 transition-colors hover:bg-emerald-500/15 disabled:cursor-not-allowed disabled:opacity-50 dark:text-emerald-400"
            >
              {pineLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Code2 className="h-3.5 w-3.5" />}
              Pine Script
            </button>
          )}
          {msg.shadowId && (
            <a
              href={`/shadow-reports/${encodeURIComponent(msg.shadowId)}?format=html`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-signal/25 bg-signal/10 px-3 py-1.5 text-sm font-medium text-signal transition-colors hover:bg-signal/15"
            >
              <FileText className="h-3.5 w-3.5" />
              Shadow Report
            </a>
          )}
        </div>
        {showPine && pineCode && (
          <PineScriptViewer code={pineCode} onClose={() => setShowPine(false)} />
        )}
      </div>
    </div>
  );
});

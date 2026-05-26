import { WifiOff, RefreshCw } from "lucide-react";
import type { SSEStatus } from "@/hooks/useSSE";

interface Props {
  status: SSEStatus;
  retryAttempt?: number;
}

export function ConnectionBanner({ status, retryAttempt }: Props) {
  if (status === "connected" || status === "disconnected") return null;

  return (
    <div className="flex items-center gap-2 border-b border-warning/30 bg-warning/15 px-4 py-2 text-xs text-warning backdrop-blur-xl">
      {status === "reconnecting" ? (
        <>
          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
          <span>Connection lost, reconnecting (attempt {retryAttempt || 1})…</span>
        </>
      ) : (
        <>
          <WifiOff className="h-3.5 w-3.5" />
          <span>Connection lost</span>
        </>
      )}
    </div>
  );
}

import { memo, useState, useCallback } from "react";
import { User, XCircle, RefreshCw, Copy, Check } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { formatTimestamp } from "@/lib/formatters";
import type { AgentMessage } from "@/types/agent";
import { AgentAvatar } from "./AgentAvatar";
import { RunCompleteCard } from "./RunCompleteCard";

const remarkPlugins = [remarkGfm];
const rehypePlugins = [rehypeHighlight];

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, [text]);
  return (
    <button
      onClick={handleCopy}
      className="absolute right-2 top-2 cursor-pointer rounded-md border border-border/60 bg-background/80 p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-foreground group-hover:opacity-100"
      title={copied ? "Copied" : "Copy"}
    >
      {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

function getRetryHint(content: string): string {
  const lower = content.toLowerCase();
  if (lower.includes("timeout") || lower.includes("timed out")) {
    return "Execution timed out. Try simplifying the strategy or reducing the number of assets.";
  }
  if (lower.includes("api") || lower.includes("rate limit") || lower.includes("429") || lower.includes("500") || lower.includes("502") || lower.includes("503")) {
    return "API call failed. Please retry later.";
  }
  return "Execution failed. Click to retry.";
}

function providerLabel(provider: string): string {
  const labels: Record<string, string> = {
    "openrouter": "OpenRouter",
    "groq": "Groq",
    "openai-codex": "OpenAI Codex",
    "openai": "OpenAI",
    "deepseek": "DeepSeek",
    "gemini": "Gemini",
    "moonshot": "Moonshot",
    "minimax": "MiniMax",
    "zai": "Z.ai",
    "ollama": "Ollama",
  };
  return labels[provider] ?? provider;
}

interface Props {
  msg: AgentMessage;
  onRetry?: (msg: AgentMessage) => void;
}

export const MessageBubble = memo(function MessageBubble({ msg, onRetry }: Props) {
  const ts = msg.timestamp ? formatTimestamp(msg.timestamp) : null;
  const source = msg.provider && msg.model ? `Sent via ${providerLabel(msg.provider)} · ${msg.model}` : null;

  if (msg.type === "user") {
    return (
      <div className="group flex justify-end gap-3">
        <div className="max-w-[78%] rounded-2xl rounded-tr-sm border border-primary/30 bg-primary/95 px-4 py-2.5 text-sm leading-relaxed text-primary-foreground shadow-[0_18px_44px_-28px_hsl(var(--primary))] whitespace-pre-wrap">
          {msg.content}
          {ts && <span className="block text-[9px] opacity-50 text-right mt-1">{ts}</span>}
        </div>
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border/70 bg-muted/60">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (msg.type === "answer") {
    return (
      <div className="group flex gap-3">
        <AgentAvatar />
        <div className="glass-panel-soft relative min-w-0 flex-1 rounded-xl px-4 py-3">
          <CopyButton text={msg.content} />
          <div className="prose prose-sm max-w-none leading-relaxed dark:prose-invert prose-table:border prose-table:border-border/50 prose-th:bg-muted/30 prose-th:px-3 prose-th:py-1.5 prose-td:px-3 prose-td:py-1.5 prose-th:text-left prose-th:text-xs prose-th:font-medium prose-td:text-xs">
            <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins}>{msg.content}</ReactMarkdown>
          </div>
          {(source || ts) && (
            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-muted-foreground/45">
              {source && <span>{source}</span>}
              {source && ts && <span className="text-muted-foreground/25">·</span>}
              {ts && <span className="opacity-0 transition-opacity group-hover:opacity-100">{ts}</span>}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (msg.type === "run_complete" && msg.runId) {
    return <RunCompleteCard msg={msg} />;
  }

  if (msg.type === "error") {
    const hint = getRetryHint(msg.content);
    return (
      <div className="flex gap-3">
        <AgentAvatar />
        <div className="space-y-2">
          <div className="flex items-start gap-2 rounded-xl border border-danger/30 bg-danger/5 px-4 py-3 shadow-[0_18px_44px_-32px_hsl(var(--danger))]">
            <XCircle className="h-4 w-4 text-danger shrink-0 mt-0.5" />
            <p className="text-sm text-danger leading-relaxed">{msg.content}</p>
          </div>
          {onRetry && (
            <button
              onClick={() => onRetry(msg)}
              className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-transparent px-3 py-1.5 text-xs text-muted-foreground transition-all hover:border-border hover:bg-muted/80 hover:text-foreground"
              title={hint}
            >
              <RefreshCw className="h-3 w-3" />
              <span>{hint}</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  // Fallback: show content for any unhandled message type
  if (msg.content) {
    return (
      <div className="flex gap-3">
        <AgentAvatar />
        <p className="text-sm text-muted-foreground leading-relaxed">{msg.content}</p>
      </div>
    );
  }

  return null;
});

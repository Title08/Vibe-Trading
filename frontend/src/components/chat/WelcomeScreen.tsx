import { Activity, BarChart3, Bot, Globe, NotebookPen, ShieldCheck, Sparkles, TrendingUp, UserCircle2, Users, Zap } from "lucide-react";
import { useI18n } from "@/lib/i18n";

interface Example {
  title: string;
  desc: string;
  prompt: string;
}

interface Category {
  label: string;
  icon: React.ReactNode;
  color: string;
  examples: Example[];
}

const CATEGORIES: Category[] = [
  {
    label: "Multi-Market Backtest",
    icon: <TrendingUp className="h-4 w-4" />,
    color: "text-red-400 border-red-500/30 hover:border-red-500/60 hover:bg-red-500/5",
    examples: [
      {
        title: "Cross-Market Portfolio",
        desc: "A-shares + crypto + US equities with risk-parity optimizer",
        prompt: "Backtest a risk-parity portfolio of 000001.SZ, BTC-USDT, and AAPL for full-year 2024, compare against equal-weight baseline",
      },
      {
        title: "BTC 5-Min MACD Strategy",
        desc: "Minute-level crypto backtest with real-time OKX data",
        prompt: "Backtest BTC-USDT 5-minute MACD strategy, fast=12 slow=26 signal=9, last 30 days",
      },
      {
        title: "US Tech Max Diversification",
        desc: "Portfolio optimizer across FAANG+ via yfinance",
        prompt: "Backtest AAPL, MSFT, GOOGL, AMZN, NVDA with max_diversification portfolio optimizer, full-year 2024",
      },
    ],
  },
  {
    label: "Research & Analysis",
    icon: <Sparkles className="h-4 w-4" />,
    color: "text-amber-400 border-amber-500/30 hover:border-amber-500/60 hover:bg-amber-500/5",
    examples: [
      {
        title: "Multi-Factor Alpha Model",
        desc: "IC-weighted factor synthesis across 300 stocks",
        prompt: "Build a multi-factor alpha model using momentum, reversal, volatility, and turnover on CSI 300 constituents with IC-weighted factor synthesis, backtest 2023-2024",
      },
      {
        title: "Options Greeks Analysis",
        desc: "Black-Scholes pricing with Delta/Gamma/Theta/Vega",
        prompt: "Calculate option Greeks using Black-Scholes: spot=100, strike=105, risk-free rate=3%, vol=25%, expiry=90 days, analyze Delta/Gamma/Theta/Vega",
      },
    ],
  },
  {
    label: "Swarm Teams",
    icon: <Users className="h-4 w-4" />,
    color: "text-violet-400 border-violet-500/30 hover:border-violet-500/60 hover:bg-violet-500/5",
    examples: [
      {
        title: "Investment Committee Review",
        desc: "Multi-agent debate: long vs short, risk review, PM decision",
        prompt: "[Swarm Team Mode] Use the investment_committee preset to evaluate whether to go long or short on NVDA given current market conditions",
      },
      {
        title: "Quant Strategy Desk",
        desc: "Screening to factor research to backtest to risk audit",
        prompt: "[Swarm Team Mode] Use the quant_strategy_desk preset to find and backtest the best momentum strategy on CSI 300 constituents",
      },
    ],
  },
  {
    label: "Document & Web Research",
    icon: <Globe className="h-4 w-4" />,
    color: "text-blue-400 border-blue-500/30 hover:border-blue-500/60 hover:bg-blue-500/5",
    examples: [
      {
        title: "Analyze an Earnings Report PDF",
        desc: "Upload a PDF and ask questions about the financials",
        prompt: "Summarize the key financial metrics, risks, and outlook from the uploaded earnings report",
      },
      {
        title: "Web Research: Macro Outlook",
        desc: "Read live web sources for macro analysis",
        prompt: "Read the latest Fed meeting minutes and summarize the key takeaways for equity and crypto markets",
      },
    ],
  },
  {
    label: "Trade Journal",
    icon: <NotebookPen className="h-4 w-4" />,
    color: "text-orange-400 border-orange-500/30 hover:border-orange-500/60 hover:bg-orange-500/5",
    examples: [
      {
        title: "Analyze My Broker Export",
        desc: "Parse journal CSV with holding stats and PnL behavior",
        prompt: "Analyze the trade journal I just uploaded - full profile with holding stats, win rate, top symbols, and hourly distribution",
      },
      {
        title: "Diagnose My Behavior Biases",
        desc: "Disposition, overtrading, chasing, anchoring",
        prompt: "Run the 4 behavior diagnostics on my trade journal (disposition, overtrading, chasing, anchoring) and tell me which bias hurts my PnL most",
      },
    ],
  },
  {
    label: "Shadow Account",
    icon: <UserCircle2 className="h-4 w-4" />,
    color: "text-emerald-400 border-emerald-500/30 hover:border-emerald-500/60 hover:bg-emerald-500/5",
    examples: [
      {
        title: "Train My Shadow from Journal",
        desc: "Extract your strategy rules from a broker CSV",
        prompt: "Train my shadow account from the trading journal I just uploaded - show the extracted rules and confirm they look like my behavior",
      },
      {
        title: "How Much Am I Leaving on the Table?",
        desc: "Backtest your shadow strategy and attribute the delta",
        prompt: "Run a shadow backtest for the last 90 days on the US market and break down where my PnL diverged from the shadow (rule violations, early exits, missed signals)",
      },
      {
        title: "Generate Shadow Report",
        desc: "Equity curve, per-market Sharpe, attribution waterfall",
        prompt: "Render the shadow report and give me the URL - lead with the you-vs-shadow delta",
      },
    ],
  },
];

const CAPABILITY_CHIPS = [
  "70 Finance Skills",
  "29 Swarm Presets",
  "32 Agent Tools",
  "A-Share / Crypto / HK-US",
  "Minute to Daily Timeframes",
  "4 Portfolio Optimizers",
  "Options & Derivatives",
  "Factor Analysis & ML",
];

interface Props {
  onExample: (s: string) => void;
}

export function WelcomeScreen({ onExample }: Props) {
  const { t } = useI18n();

  return (
    <div className="mx-auto flex min-h-[64vh] w-full min-w-0 max-w-5xl flex-col gap-6 py-6">
      <section className="glass-panel min-w-0 max-w-full overflow-hidden rounded-xl">
        <div className="market-grid grid min-w-0 gap-6 p-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)] lg:p-7">
          <div className="min-w-0 space-y-5 text-left">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-primary/30 bg-primary/15 text-primary shadow-[0_0_44px_-18px_hsl(var(--primary))]">
                <Bot className="h-6 w-6" />
              </div>
              <div className="min-w-0">
                <h2 className="break-words text-xl font-semibold tracking-tight sm:text-2xl">Vibe-Trading Agent Desk</h2>
                <p className="text-sm text-muted-foreground">{t.describeStrategy}</p>
              </div>
            </div>

            <div className="grid min-w-0 gap-3 sm:grid-cols-3">
              <div className="min-w-0 rounded-lg border border-signal/25 bg-signal/10 p-3">
                <Activity className="mb-2 h-4 w-4 text-signal" />
                <div className="text-lg font-semibold tabular-nums">3</div>
                <div className="text-xs text-muted-foreground">market data lanes</div>
              </div>
              <div className="min-w-0 rounded-lg border border-ai/25 bg-ai/10 p-3">
                <Users className="mb-2 h-4 w-4 text-ai" />
                <div className="text-lg font-semibold tabular-nums">29</div>
                <div className="text-xs text-muted-foreground">swarm presets</div>
              </div>
              <div className="min-w-0 rounded-lg border border-primary/25 bg-primary/10 p-3">
                <ShieldCheck className="mb-2 h-4 w-4 text-primary" />
                <div className="text-lg font-semibold tabular-nums">15+</div>
                <div className="text-xs text-muted-foreground">risk metrics</div>
              </div>
            </div>
          </div>

          <div className="min-w-0 overflow-hidden rounded-xl border border-border/60 bg-background/50 p-4 shadow-inner">
            <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              <Zap className="h-3.5 w-3.5 text-primary" />
              Mission presets
            </div>
            <div className="flex flex-wrap gap-2">
              {CAPABILITY_CHIPS.map((chip) => (
                <span
                  key={chip}
                  className="min-w-0 rounded-full border border-border/70 bg-muted/30 px-2.5 py-1 text-xs text-muted-foreground"
                >
                  {chip}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="w-full space-y-4 text-left">
        <div className="flex items-center justify-between gap-3 px-1">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">{t.examples}</p>
          <div className="hidden items-center gap-1.5 text-xs text-muted-foreground sm:flex">
            <BarChart3 className="h-3.5 w-3.5 text-signal" />
            Backtest, research, compare, report
          </div>
        </div>
        <div className="grid min-w-0 grid-cols-1 gap-3 lg:grid-cols-3">
          {CATEGORIES.map((cat) => (
            <div key={cat.label} className="glass-panel-soft min-w-0 space-y-2 rounded-xl p-3">
              <div className={`flex items-center gap-1.5 px-1 text-xs font-semibold ${cat.color.split(" ").filter(c => c.startsWith("text-")).join(" ")}`}>
                {cat.icon}
                <span>{cat.label}</span>
              </div>
              <div className="space-y-1.5">
                {cat.examples.map((ex) => (
                  <button
                    key={ex.title}
                    onClick={() => onExample(ex.prompt)}
                    className={`block w-full min-w-0 cursor-pointer rounded-lg border bg-background/30 px-3 py-2.5 text-left transition-colors ${cat.color}`}
                  >
                    <span className="text-sm font-medium leading-snug text-foreground">
                      {ex.title}
                    </span>
                    <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">
                      {ex.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

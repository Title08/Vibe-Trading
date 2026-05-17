# Vibe-Trading AI Agents

Vibe-Trading utilizes a sophisticated multi-agent system (Swarm) to handle complex financial research and trading tasks. Agents are organized into specialized teams (presets) that work together to deliver comprehensive analysis.

## Agent Teams (Presets)

Below are the specialized teams available in the system:

### 📊 Quant & Strategy
- **Quant Strategy Desk**: Stock screening → factor research → backtest → risk audit.
- **ML Quant Lab**: Feature engineering → model training → signal generation → validation.
- **Factor Research Committee**: Alpha mining, IC testing, and factor combination.
- **Statistical Arbitrage Desk**: Pairs/basket discovery, cointegration testing, and mean-reversion.
- **Pairs Research Lab**: Identifying and testing cointegrated pairs for market-neutral trading.

### 📈 Market & Asset Specialized
- **Equity Research Team**: Sector-specific fundamental and technical analysis.
- **Crypto Trading Desk**: On-chain data + exchange liquidity + sentiment for crypto markets.
- **Commodity Research Team**: Supply/demand balance, macro drivers, and futures curve analysis.
- **Convertible Bond Team**: Credit analysis + equity optionality + arbitrage opportunities.
- **ETF Allocation Desk**: Macro screening, fund selection, and portfolio optimization.

### 🌐 Global & Macro
- **Macro Strategy Forum**: Rates, inflation, and liquidity analysis across major economies.
- **Global Allocation Committee**: Cross-asset (stocks, bonds, gold) portfolio optimization.
- **Macro Rates & FX Desk**: Interest rate curves and currency pair strategy.
- **Geopolitical War Room**: Event-impact analysis on markets (sanctions, conflicts, elections).

### 🔍 Specialized Research
- **Earnings Research Desk**: Post-earnings drift, transcript sentiment, and guidance analysis.
- **Event-Driven Task Force**: M&A, dividends, share buybacks, and regulatory catalysts.
- **Sentiment Intelligence Team**: Social media + news + alternative data sentiment signals.
- **Technical Analysis Panel**: Pattern recognition, multi-timeframe indicators, and volume profile.

### 🛡️ Risk & Governance
- **Risk Committee**: Stress testing, VaR analysis, and exposure limits.
- **Investment Committee**: Final strategy review, capital allocation, and performance attribution.
- **Portfolio Review Board**: Periodic rebalancing and drawdown attribution.

## Agent Roles

Within these teams, agents play specific roles such as:
- **Screener**: Identifying candidates based on criteria.
- **Researcher**: Deep dives into specific symbols or factors.
- **Backtester**: Implementing and testing strategies.
- **Auditor**: Reviewing risk and quality.
- **Macro Analyst**: Analyzing top-down drivers.

## Customizing Agents

You can find the definitions for these teams in `agent/src/swarm/presets/*.yaml`. You can create your own team by adding a new YAML file to this directory.

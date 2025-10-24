
# AGENT.md — Stock “Missed Opportunity” Analyzer + Smart Advisor
**Date:** 2025-10-24  
**Owner:** Mahmoud’s Family  
**Timezone:** Asia/Dubai (all “today/close” references use this tz)  
**Base Currency (default):** USD

---

## 0) Document Purpose
This file is a **builder-ready specification** for an agent/service that:
1) Reconstructs positions and cost basis from your trades,  
2) Computes **hypothetical liquidation P&L per day** (what if you sold that day),  
3) Quantifies **missed opportunities** (regret metrics), and  
4) Adds a **Smart Advisor Layer**: rules-based market signals, news/analyst sentiment, a 30‑day **Next Best Move Predictor**, narrative reports, macro overlays, advanced alerts, and an enhanced scenario simulator.

You can implement this as a single service with batch jobs, or as multi-services connected by a message bus.

---

## 1) Primary Outcomes (What You See)
- **Per-symbol timeline** from first buy → today:
  - **Hypothetical Liquidation P&L** (core), **Unrealized P&L**, **Realized P&L to date**.
  - **Day-level Opportunity** (“regret if you didn’t sell that day”).  
- **Visuals**: time-series with sentiment background, calendar heatmap, **Top Missed Days**, drawdown strips, lot contribution waterfall.  
- **Smart Advisor** outputs:
  - Daily **Signals** from user rules (technical) + aggregated **News Sentiment** + **Analyst Insights** (AI-verified when confirmed by tech+news).
  - **30‑day Predictor**: P(re-taking last peak), expected regret if selling vs holding today, with drivers.  
  - **Narratives** (daily/weekly): leaders & laggards, signals, sentiment, macro context, nudges.  
  - **Macro** overlays (FOMC/CPI/NFP/ISM/etc.), impact markers, rolling beta/correlation.  
  - **Alerts** with short AI explanations.  
  - **Scenario Simulator** for “alternate universe” P&L (ghost timelines).  
  - **Regret–Risk–Reward Dashboard** with ERI (Emotional Risk Index).

---

## 2) Scope
In-scope: equities/ETFs initially; daily bars (with adjusted close); USD base (configurable); CSV/API ingest; per‑day snapshots; dashboards and APIs.  
Out-of-scope (v1): intraday execution, options, futures, tax advice.

---

## 3) Core Definitions
### 3.1 Positions & Lots
- Track **lots** (each buy is a distinct lot).
- Position on date *d* = sum of open lot shares EOD *d*.
- Realized P&L uses FIFO/LIFO/Specific-ID (configurable). Hypothetical liquidation ignores lot method (assumes sell all open shares).

### 3.2 Prices & FX
- Use **adjusted close** for splits/dividends.  
- Multi-currency: convert to portfolio base currency via daily close FX.

### 3.3 P&L
- MarketValue(d) = Shares_open(d) × AdjClose(d).  
- CostBasis_open(d) = Σ open lots (qty × adj cost + fees alloc).  
- UnrealizedP&L(d) = MarketValue(d) − CostBasis_open(d).

### 3.4 Hypothetical Liquidation P&L (core)
Let **Realized_to_date(d)** be realized P&L up to EOD *d*.  
Let **HypoProceeds(d)** = Shares_open(d) × AdjClose(d) − est. sell fees/taxes.  
**HypoLiquidP&L(d)** = Realized_to_date(d) + [HypoProceeds(d) − CostBasis_open(d)].

### 3.5 Missed Opportunity Metrics
- **DayOpp(d)** = max(0, HypoLiquidP&L(d) − Realized_to_date(d)).  
- **Peak Hypo P&L** = max_d HypoLiquidP&L(d).  
- **Regret Today** = max(0, Peak − HypoLiquidP&L(today)).

Edge cases: no open shares ⇒ HypoLiquidP&L(d)=Realized_to_date(d), DayOpp(d)=0.

---

## 4) User Stories (selected)
- **Import & Rebuild**: upload CSV/APIs → build lots, realized P&L.  
- **View Timeline**: see Hypo P&L, Unrealized P&L, price, and DayOpp.  
- **Top Missed Days**: sortable table with Δ vs today.  
- **Signals & Sentiment**: rule triggers + sentiment/analyst badges on charts.  
- **Predictor**: “If you sold today, expected regret in 30d: –3.4%.”  
- **Simulator**: “Sell half on last signal,” “Re-enter at X,” show ghost line.  
- **Narratives**: daily/weekly summaries with nudges.  
- **Macro Overlays**: see events and impact flags.  
- **Alerts**: drawdown explanations; signal triggers; macro proximity.  
- **Exports**: CSV/PNG/PDF and JSON API responses.

---

## 5) Data Ingest & Normalization
### 5.1 Transactions (CSV/API)
Columns: `date, type{BUY|SELL|DIVIDEND|FEE|SPLIT}, symbol, quantity, price, fee, tax, currency, broker_id`  
- Deduplicate; reconcile partial fills; validate non-negative balances.  
- Apply split adjustments consistently (or use adjusted prices).

### 5.2 Market Data
- Daily adjusted close, volume (per listing currency); corporate actions.  
- FX daily closes to base currency.

### 5.3 News & Analyst
- News sources (e.g., Reuters/SA/MarketBeat), dedupe by URL hash; summarize + classify ∈ {bearish, neutral, bullish} with score [−1,+1].  
- Analyst notes: normalize to `{rating, target_price, horizon_days, source}`.

### 5.4 Macro Calendar
- FOMC/CPI/NFP/ISM/GDP events with UTC timestamps & importance.

---

## 6) Data Model
### 6.1 Core
- **Portfolio**: `base_currency`, `timezone`  
- **Transaction**: `id, symbol, type, qty, price, fee, tax, currency, datetime`  
- **Lot** (derived): `lot_id, symbol, open_datetime, qty_open, cost_per_share_adj, fees_alloc`  
- **DailyBar**: `symbol, date, adj_close, volume, currency`  
- **FXRate**: `date, from_ccy, to_ccy, rate_close`  
- **DailyPortfolioSnapshot** (per symbol):  
  `date, shares_open, market_value_base, cost_basis_open_base, unrealized_pl_base, realized_pl_to_date_base, hypo_liquidation_pl_base, day_opportunity_base, peak_hypo_pl_to_date_base, drawdown_from_peak_pct`

### 6.2 Smart Advisor Additions
- **SignalEvent**: `id, symbol, date, rule_id, signal_type, severity, payload, cooldown_until`  
- **TickerSentimentDaily**: `symbol, date, score, class, top_headlines[]`  
- **AnalystSnapshot**: `symbol, date, rating, target_price, horizon_days, source, verified`  
- **ForecastDaily**: `symbol, asof, prob_retake_peak_30d, exp_regret_sell_now_30d, exp_regret_hold_now_30d, drivers[]`  
- **MacroEvent**: `event_id, type, time_utc, importance, symbol_impact_tags[]`  
- **DashboardKPI**: `date, metric_key, symbol?, value`

---

## 7) Algorithms (concise)
### 7.1 Lot Builder & P&L
- Build lots from buys; close with sells via FIFO/LIFO/SpecID.  
- Daily loop d: compute shares_open, market value, cost basis, realized_to_date; compute HypoLiquidP&L(d) & DayOpp(d); update peaks & drawdowns.

### 7.2 Indicators (cached)
- `sma_n, ema_n, rsi_14, macd(12,26,9), atr_14, volume_multiple_20d, momentum_20/60d, gap stats`.

### 7.3 Rule Engine (technical triggers)
- Evaluate boolean expression trees over indicator arrays; enforce `cooldown_days` per `rule_id` per symbol; de-duplicate same-day multi-triggers.

**Technical Rule JSON (example)**
```json
{
  "id": "rule_path_reentry_1720",
  "name": "PATH closes > 17.20 w/1.5x vol",
  "scope": {"symbols": ["PATH"], "active": true},
  "when": {"all": [
    {"ind": "close", "op": ">", "value": 17.20},
    {"ind": "volume_multiple_20d", "op": ">=", "value": 1.5}
  ]},
  "then": {"signal_type": "REENTRY", "severity": "info", "tags": ["breakout"]},
  "cooldown_days": 2,
  "valid_session": "regular"
}
```

### 7.4 Sentiment
- Per-article LLM classification → z-score by source → time decay → **daily ticker score** in [−1,+1].

### 7.5 Analyst “AI-verified”
- `verified = True` iff analyst direction agrees with both: (a) technical momentum (e.g., `RSI>60` or `SMA20>SMA50`) and (b) sentiment score > +0.2 (or < −0.2 for bearish).

### 7.6 Predictor (30‑day)
- Model: gradient-boosted trees (weekly recalibration).  
- Features: behavior (missed-opportunity history), tech, flow, sentiment, analyst, macro proximity, beta/corr to indices/10Y/oil.  
- Targets:  
  - `P(High_{t+30} ≥ last_peak_price)`  
  - `E[Regret_30d | sell_now]`, `E[Regret_30d | hold_now]`.  
- Explainability: normalized SHAP → `drivers[]` ~ sum to 1.

### 7.7 Macro Impact
- Event windows [−3d,+3d]; compute return/vol deciles vs rolling baseline; flag top decile as impact markers.  
- Rolling `beta_60d`, `corr_60d` to NASDAQ/S&P/sector ETF/10Y/oil.

### 7.8 ERI (Emotional Risk Index)
1) Identify post-peak windows;  
2) Count instances where holding persisted through ≥20% reversal;  
3) ERI=100×(held_through / total_post_peak_windows).

---

## 8) UI/UX
- **Main Chart**: Hypo Liquidation P&L (thick), Unrealized P&L (thin), price (secondary). Background gradient by daily **sentiment score**. Hover shows: date, price, shares_open, hypo P&L, DayOpp, realized_to_date, sentiment, signal tags.  
- **Calendar Heatmap**: DayOpp intensity; click to jump in chart.  
- **Top Missed Days**: Date, Hypo P&L, DayOpp, Price, Shares, “Δ vs Today”.  
- **Lot Waterfall**: contribution to the best missed day.  
- **Predictor Panel**: prob_retake_peak_30d; expected regret sell vs hold; drivers.  
- **Scenario Simulator**: define actions (SELL/BUY/TRAIL STOP), assumptions; render ghost timeline and Δ metrics.  
- **Macro Overlays**: badges on chart; hover for event details & impact.  
- **Dashboard**: KPI cards for %DaysMissed10, AvgDD_after_best, ERI, PeakRegretNow, SignalFollow‑Through.

**Architecture Diagram (SVG)**: [smart_advisor_architecture.svg](smart_advisor_architecture.svg)  
(Chat download link: `sandbox:/mnt/data/smart_advisor_architecture.svg`)

---

## 9) APIs
**Full OpenAPI (YAML)**: [smart_advisor_openapi.yaml](smart_advisor_openapi.yaml)  
(Chat download link: `sandbox:/mnt/data/smart_advisor_openapi.yaml`)

### 9.1 Selected Endpoints
- `GET /symbols/{symbol}/timeline?from&to` → `DailyPortfolioSnapshot[]`  
- `GET /symbols/{symbol}/top-missed?limit=10`  
- `POST /simulate` → create alternate timeline (ghost)  
- **Signals & Sentiment**:  
  - `GET /signals/{symbol}?from&to`  
  - `POST /signals/rules` (upsert technical rules)  
  - `GET /sentiment/{symbol}?from&to`  
  - `GET /analyst/{symbol}?from&to`  
- **Forecasts**: `GET /forecast/{symbol}?asof`  
- **Narratives**: `GET /narratives/daily?date=YYYY-MM-DD`, `GET /narratives/weekly?week=YYYY-Www`  
- **Alerts**: `GET /alerts?date=YYYY-MM-DD`, `POST /alerts/test`  
- **Macro**: `GET /macro/events?from&to&type=…`, `GET /macro/impact/{symbol}?from&to`  
- **Dashboard**: `GET /dashboard/kpis?date=YYYY-MM-DD`

**Seed JSON for quick start**: [smart_advisor_seed.json](smart_advisor_seed.json)  
(Chat download link: `sandbox:/mnt/data/smart_advisor_seed.json`)

---

## 10) Scenario Simulator API
```http
POST /simulate
{
  "symbol":"HPE",
  "base_timeline_id":"current",
  "what_if":[
    {"type":"SELL","date":"2025-09-10","qty_pct":0.5,"price":"mkt_close"},
    {"type":"BUY","date":"2025-09-24","qty_pct":0.5,"price":15.50}
  ],
  "assumptions":{"fee_bps":5,"fx_sigma_pct":1.2,"tax_rate_pct":15}
}
→ {"timeline_id":"sim_abc123","diff_vs_base":{"pnl_delta": "...", "max_dd_delta":"..." }}
```

---

## 11) Alerts & Reason Engine
- Types: **Drawdown++**, **Signal Trigger**, **Macro Proximity**, **New Peak**.  
- Rationale templatization with structured facts and historical analogues.

**Drawdown template (example)**
```json
{
  "template":"drawdown_explain_v1",
  "vars":{
    "symbol":"HPE",
    "magnitude_pct":-3.8,
    "cause":"post-Investor Day guidance",
    "analogue_window":"2022–2023",
    "recovery_days_range":"9–14"
  }
}
```

---

## 12) Narratives
- **Daily** (post-close): leaders/laggards by unrealized Δ, missed-opportunity trend, triggered rules, sentiment & analyst badges, macro proximity, and **nudges** from the Predictor.  
- **Weekly**: condensed overview + notable macro and ERI movement.

**Sample nugget**
> “TSLA +2.1% unrealized led; LAC −3.6% weighed. HPE re-entry fired; volume 1.6× 20D. Analyst sentiment on TSLA bullish ($600 target; verified).”

---

## 13) Non‑Functional: Ops, SLO, Security
- **SLOs**: Signals < **2 min** after close; Narratives < **5 min**.  
- **Idempotency**: Upserts keyed by `(symbol, date, source)`.  
- **Explainability**: Persist feature snapshots and SHAP artifacts 90 days.  
- **Privacy**: Encrypt broker files; redact account numbers; store only `source_url_hash` for news; API keys in secret manager.  
- **Audit**: Reasoning traces (OpenAI Agents SDK) per symbol/day across stages (ingest → signal → forecast → narrative → alert id).  
- **Testing**: golden datasets with splits/dividends; unit tests for lot math, rule firing, predictor calibration (Brier vs baseline).

---

## 14) Acceptance Criteria (End‑to‑End)
1) Importing a minimal CSV (see Appendix) builds lots & daily snapshots.  
2) Hypo P&L and DayOpp reconcile on seed dataset; **Top Missed Days** matches maxima.  
3) PATH sample rule fires only when `close>17.20` and `vol≥1.5×20D`, with 2‑day cooldown.  
4) Sentiment background follows `TickerSentimentDaily.score`.  
5) Analyst `verified=true` only when tech momentum **and** sentiment agree.  
6) Predictor returns calibrated `prob_retake_peak_30d`; drivers provided.  
7) Simulator generates ghost timeline consistent with assumptions.  
8) Macro overlays render and impact markers appear on top‑decile events.  
9) Alerts include explanation text; “drawdown” alert cites analogue window.  
10) Dashboard computes ERI, %DaysMissed10, AvgDD_after_best correctly.

---

## 15) Implementation Notes
- Columnar snapshots (Parquet) for fast charting; vectorized numpy/pandas for indicators; caching for prices/FX/news.  
- Batch recompute per symbol on new trades or config changes.  
- Message bus (optional) for Signals → Predictor → Narratives → Alerts.  
- Configurable fee/tax models; per‑exchange holiday calendars; EOD consolidation job keyed to Asia/Dubai.  
- Observability: traces + metrics (rule eval time, alert throughput, narrative latency).

---

## 16) Appendix
### 16.1 Example Trades (USD)
- 2024‑03‑01 BUY 100 @ 10.00, fee 5  
- 2024‑07‑01 BUY 50 @ 12.00, fee 5  
- 2024‑09‑15 SELL 50 @ 15.00, fee 5

**On 2024‑09‑10**  
- Shares_open=150; AdjClose=14.00 → MarketValue=2100  
- CostBasis_open=1610; Realized_to_date=0  
- Unrealized P&L=490; HypoLiquidP&L=485; DayOpp=485

### 16.2 CSV Template (import)
```csv
date,type,symbol,quantity,price,fee,tax,currency,broker_id,notes
2024-03-01,BUY,PATH,100,10.00,5,0,USD,BRK1,
2024-07-01,BUY,PATH,50,12.00,5,0,USD,BRK1,
2024-09-15,SELL,PATH,-50,15.00,5,0,USD,BRK1,
```

### 16.3 Starter Content
- **Rules & Mock Data**: `smart_advisor_seed.json`  
- **API Spec**: `smart_advisor_openapi.yaml`  
- **Architecture Diagram**: `smart_advisor_architecture.svg`

> If you place these files next to this AGENT.md, the relative links above will work. In chat, use the provided sandbox links.

---

## 17) Changelog
- **v0.1** — Initial end‑to‑end spec with Smart Advisor extensions, APIs, and seeds.

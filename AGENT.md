
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

## 7) Algorithms (concise + operational detail)
### 7.1 Lot Builder & P&L
- Build lots from buys; close with sells via FIFO/LIFO/Specific-ID (configurable).
- Daily loop `d`: compute shares_open, market value, cost basis, realized_to_date; derive HypoLiquidP&L(d), DayOpp(d), rolling peaks, and drawdowns.

### 7.2 Indicator Cache
- Pre-compute and persist `close, open, high, low, volume, sma_n, ema_n, rsi_14, macd(12,26,9), atr_n, volume_multiple_20d, momentum_20/60d, gap stats, bollinger bands (upper/lower_n)`.
- Cache keyed by `(symbol, date, indicator_id)` to support both batch signal runs and interactive charting.

### 7.3 Rule Engine (technical triggers)
- Evaluate boolean expression trees over indicator arrays; enforce `cooldown_days` per `(rule_id, symbol)`; suppress duplicate fire within same session.
- JSON schema aligns with the user-defined rule format below; `valid_session` filters out pre/post sessions.

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

**Indicator dictionary (minimum viable)**
`close, open, high, low, volume, sma_{n}, ema_{n}, rsi_{n}, macd(12,26,9), volume_multiple_20d, atr_{n}, bb_upper_{n}, bb_lower_{n}`.

### 7.4 Sentiment pipeline
- Fetch → dedupe by URL hash → LLM summarize (headline plus 1–2 bullet takeaways) → classify into `{bearish, neutral, bullish}` with score in `[-1, +1]`.
- Daily aggregate: volume-weighted mean by publisher weight with exponential decay; materialize as `TickerSentimentDaily`.

### 7.5 Analyst insight verification
- Normalize upstream sources (SeekingAlpha, MarketBeat, TradingView Analysts, Reuters) into `{rating, target_price, horizon_days, note}`.
- Set `verified=True` when analyst direction aligns with both technical momentum (`RSI>60` or `SMA20>SMA50`) and `sentiment_daily.score > 0.2` (or < -0.2 for bearish cases).

### 7.6 Predictor (30-day Next Best Move)
- Baseline: gradient boosted trees retrained weekly; handles class imbalance via focal loss where applicable and calibrated via Platt scaling or isotonic regression.
- Outputs `P(High_{t+30} ≥ last_peak_price)`, `E[Regret_{30d} | sell_now]`, `E[Regret_{30d} | hold_now]`, plus SHAP-based drivers summing to ~1.

### 7.7 Macro impact and correlation
- Event windows `[−3d, +3d]`; compute return/vol deciles vs rolling history; flag top decile as impact markers.
- Maintain rolling `beta_60d` and `corr_60d` to NASDAQ, S&P, sector ETF, US 10Y, and Brent/WTI.

### 7.8 Emotional Risk Index (ERI)
1. Detect post-peak windows;  
2. Count episodes with ≥20% reversal while position remained open;  
3. `ERI = 100 × (count_held_through / total_post_peak_windows)`.

### 7.9 Reason engine scaffolding
- Assemble templated narratives from structured facts to power alerts, daily reports, and simulator explanations.

---

## 8) UI/UX
- Main chart: Hypo Liquidation P&L (primary), Unrealized P&L (secondary), price overlay; background gradient follows `sentiment_daily.score`.
- Calendar heatmap: DayOpp intensity; clicking synchronizes the main chart cursor.
- Top Missed Days table: date, Hypo P&L, DayOpp, price, shares, delta vs today.
- Lot waterfall: contribution to best missed day.
- Predictor panel: probability of retaking peak, expected regret if selling vs holding, top drivers with directionality.
- Scenario simulator: define SELL/BUY/TRAIL STOP actions, assumptions; render ghost timeline and deltas.
- Macro overlays: event markers on chart; hover reveals event metadata and impact classification.
- Dashboard cards: `%DaysMissed10`, `AvgDD_after_best`, `ERI`, `PeakRegretNow`, `SignalFollow-Through` with drill-through navigation.

**Architecture Diagram (SVG)**: [smart_advisor_architecture.svg](smart_advisor_architecture.svg)  
(Download: `sandbox:/mnt/data/smart_advisor_architecture.svg`)

---

## 9) APIs
**Full OpenAPI (YAML)**: [smart_advisor_openapi.yaml](smart_advisor_openapi.yaml)  
(Download: `sandbox:/mnt/data/smart_advisor_openapi.yaml`)

### 9.1 Selected endpoints
- `GET /symbols/{symbol}/timeline?from&to` → `DailyPortfolioSnapshot[]`
- `GET /symbols/{symbol}/top-missed?limit=10`
- `POST /symbols/{symbol}/refresh` → runs ingest + snapshot recompute
- `POST /simulate` → create alternate (ghost) timeline

### 9.2 Extended roadmap endpoints
- Signals & Sentiment:  
  - `GET /signals/{symbol}?from&to`  
  - `POST /signals/rules` (create/update JSON rules)  
  - `GET /sentiment/{symbol}?from&to`  
  - `GET /analyst/{symbol}?from&to`
- Forecasts:  
  - `GET /forecast/{symbol}?asof`  
  - `POST /forecast/retrain` (admin)
- Narratives:  
  - `GET /narratives/daily?date=YYYY-MM-DD`  
  - `GET /narratives/weekly?week=YYYY-Www`
- Alerts:  
  - `GET /alerts?date=YYYY-MM-DD`  
  - `POST /alerts/test`
- Macro:  
  - `GET /macro/events?from&to&type=FOMC|CPI|NFP`  
  - `GET /macro/impact/{symbol}?from&to`
- Dashboard:  
  - `GET /dashboard/kpis?date=YYYY-MM-DD`

### 9.3 Simulator API example
```json
POST /simulate
{
  "symbol": "HPE",
  "base_timeline_id": "current",
  "what_if": [
    {"type": "SELL", "date": "2025-09-10", "qty_pct": 0.5, "price": "mkt_close"},
    {"type": "BUY", "date": "2025-09-24", "qty_pct": 0.5, "price": 15.50}
  ],
  "assumptions": {"fee_bps": 5, "fx_sigma_pct": 1.2, "tax_rate_pct": 15}
}
→ {
  "timeline_id": "sim_abc123",
  "diff_vs_base": { "...": "..." }
}
```

---

## 10) Market intelligence & signal integration
### 10.1 Daily signal engine
- Schedule: run after price/news ingest per trading day (timezone Asia/Dubai).
- Inputs: `DailyBar`, News items, Analyst notes, `IndicatorCache`.
- Outputs: `SignalEvent[]`, `TickerSentimentDaily`, `AnalystSnapshot`.

### 10.1.1 Technical rule schema
See Section 7.3 for schema; ensure rules include scope, conditions (`all`/`any`), actions, cooldown, and valid session metadata.

### 10.1.2 Indicator dictionary
Minimum set: `close, open, high, low, volume, sma_{n}, ema_{n}, rsi_{n}, macd(12,26,9), volume_multiple_20d, atr_{n}, bb_upper_{n}, bb_lower_{n}`.

### 10.2 News sentiment (headline to daily score)
- Pipeline: fetch → dedupe → LLM summarise (headline plus 1-2 bullet takeaways) → classify into `{bearish, neutral, bullish}` with score in `[-1, +1]`.
- Daily aggregate: volume-weighted mean with publisher weights and recency decay → persisted as `sentiment_daily`.
- Payload example:
```json
{
  "symbol": "HPE",
  "date": "2025-10-23",
  "score": 0.34,
  "class": "bullish",
  "top_headlines": [
    {"src": "Reuters", "summary": "Guidance raised on AI servers; margin intact"}
  ]
}
```
- Chart integration: color P&L chart background by sentiment score gradient.

### 10.3 Analyst insights
- Sources (pluggable): SeekingAlpha, MarketBeat, TradingView Analysts, Reuters.
- Normalized fields: `rating` (bearish→bullish scale), `target_price`, `horizon_days`, `note`, `source`.
- AI-verified tag set when analyst direction matches technical momentum and sentiment thresholds (Section 7.5).

---

## 11) Smart Opportunity Forecasting (Next Best Move Predictor)
### 11.1 Objective
Estimate near-term timing risk: probability of exceeding last peak within 30 days and expected regret if selling or holding today.

### 11.2 Feature sets
- Behavioural: distance from prior peak missed days, DayOpp distribution.
- Technical: RSI, MACD histogram trend, SMA crossovers, ATR percentage, 20/60 day momentum.
- Flow: abnormal volume, gap statistics.
- News/Analyst: `sentiment_daily.score`, `verified_analyst_bullish`.
- Event: macro proximity (FOMC/CPI/NFP ±3 days), sector/index beta.

### 11.3 Modelling notes
- Baseline model: gradient boosted trees refreshed weekly; apply focal loss or class-weighting to balance positive events; calibrate with Platt scaling.

### 11.4 Output contract
```json
{
  "symbol": "PATH",
  "asof": "2025-10-24",
  "prob_retake_peak_30d": 0.41,
  "exp_regret_sell_now_30d": -0.034,
  "exp_regret_hold_now_30d": 0.018,
  "drivers": [
    {"feature": "sentiment_score", "direction": "+", "contrib": 0.22},
    {"feature": "rsi_14", "direction": "+", "contrib": 0.18}
  ]
}
```

### 11.5 UI copy
Display examples such as: `If you sold today, expected regret over 30 days: -3.4%.`

---

## 12) Daily and weekly narrative reports
### 12.1 Generation windows
- Produce daily report at market close and weekly report at Friday close (Asia/Dubai buckets).

### 12.2 Content blocks
- Leaders and laggards (unrealized P&L delta day-over-day).
- Missed opportunity trend (delta vs peak; new peaks).
- Signals summary (triggered rules, cooldown state).
- Sentiment and analyst snippets with verified badges.
- Actionable nudges sourced from predictor thresholds.

### 12.3 Narrative payload example
```json
{
  "date": "2025-10-24",
  "highlights": [
    "TSLA +2.1% unrealized led gains; LAC -3.6% weighed on P&L.",
    "HPE flagged REENTRY; volume 1.6x 20D avg (cooldown clear)."
  ],
  "missed_opportunity": {
    "new_peak_symbols": ["PATH"],
    "top_regret_today": [{"symbol": "LAC", "regret_delta_pct": 2.8}]
  },
  "sentiment": [{"symbol": "TSLA", "score": 0.45, "class": "bullish", "analyst_verified": true}],
  "actions": [{"symbol": "HPE", "suggestion": "add/trim review", "reason": "REENTRY + sentiment>0.2"}]
}
```

---

## 13) Scenario simulator enhancements
### 13.1 Actions
- Sell half on last signal, re-enter at price X on date D, trail stop at Y × ATR.

### 13.2 Assumptions panel
- Fee model, FX volatility model (±sigma scenarios), trade tax rates, slippage percentage.

### 13.3 API contract
See Section 9.3 for request/response; ensure ghost timeline reconciles fees and taxes.

---

## 14) Macro integration layer
### 14.1 Overlays
- Economic calendar events: FOMC, CPI, PPI, NFP, GDP advance/revision, PMI/ISM.
- Impact markers: flag when absolute return or volatility is in top decile within ±2 days of event.

### 14.2 Auto-correlation metrics
- Rolling beta and correlation to NASDAQ, S&P, sector ETF, US 10Y, Brent/WTI; expose on hover and in narratives.

---

## 15) Advanced alerts and AI explanations
### 15.1 Alert types
- Drawdown++ threshold crossed with reason.
- Signal trigger summary (e.g., "PATH re-entry condition; vol 1.6x 20D").
- Macro proximity alerts (e.g., "CPI tomorrow; high beta names: TSLA, LAC").
- New peak detection ("New all-time Hypo P&L peak on PATH").

### 15.2 Reason engine template
```json
{
  "type": "drawdown",
  "symbol": "HPE",
  "magnitude_pct": -3.8,
  "cause": "post-Investor Day guidance",
  "historical_analogue": {"window": "2022-2023", "median_recovery_days": [9, 14]}
}
```
Renders to: `HPE fell 3.8% post-Investor Day guidance. Similar events in 2022-2023 saw recovery in 9-14 days.`

---

## 16) Regret–risk–reward dashboard
### 16.1 KPI definitions
- `%DaysMissed10`: share of days where DayOpp ≥ +10%.
- `AvgDD_after_best`: average max drawdown after top missed days.
- `Emotional Risk Index (ERI)`: see Section 7.8.
- `PeakRegretNow`: `Peak Hypo P&L - Today Hypo P&L`.
- `SignalFollow-Through`: percent of signals that led to +X% within Y days.

### 16.2 Layout and drill-through
- KPI cards with sparkline mini-charts per symbol; drill-through reveals day-level detail and associated narratives.

---

## 17) Multi-agent and API extensions
### 17.1 Data connectors
- TradingView and Yahoo Finance for live bars and fundamentals.
- News feeds: Reuters, SeekingAlpha, MarketBeat via rate-limited queue.

### 17.2 OpenAI Agents SDK integration
- Maintain per-ticker daily reasoning traces (signals → forecast → narrative).
- Auto-annotations: agent writes inline notes onto charts with source snippets.
- Toolchain: `tool:get_prices`, `tool:get_news`, `tool:emit_signal`, `tool:write_narrative`, `tool:push_alert`.

---

## 18) Technical architecture (Smart Advisor layer)
```
[Connectors]
  ├─ Price/FX (TV/YF) ─┐
  ├─ News/Analyst -----┼─────────┐
  └─ Macro Calendar ---┘         │
                                 ▼
                     [Data Normalization & Cache]
                                 ▼
                        [Daily Signal Engine]
                     (tech rules + sentiment + analysts)
                                 ▼
               ┌───────────────[Feature Store]───────────────┐
               │ tech, flow, sentiment, macro, behaviour     │
               └──────────────────────┬──────────────────────┘
                                      ▼
                          [Next Best Move Predictor]
                                      ▼
                           [Narrative Generator]
                                      ▼
                        [Alerts/Reason Engine + Bus]
                                      ▼
                    [Missed Opp UI + Simulator + API]
```

---

## 19) Data model additions
Canonical definitions remain in Section 6.2. This section highlights the Smart Advisor layer tables for quick reference:
- `SignalEvent (id, symbol, date, rule_id, signal_type, severity, payload, cooldown_until)`
- `TickerSentimentDaily (symbol, date, score, class, top_headlines[])`
- `AnalystSnapshot (symbol, date, rating, target_price, horizon_days, source, verified)`
- `ForecastDaily (symbol, asof, prob_retake_peak_30d, exp_regret_sell_now_30d, exp_regret_hold_now_30d, drivers[])`
- `MacroEvent (event_id, type, time_utc, importance, symbol_impact_tags[])`
- `DashboardKPI (date, metric_key, symbol?, value)`

---

## 20) Algorithm cross-check
- Signal evaluation: vectorised indicator evaluation with cooldown enforcement.
- Sentiment: article classification → z-score/decay → daily score; keep source list.
- Forecast: rolling 3-5 year training window; calibration ensures Brier score ≤ baseline.
- ERI: refer to Section 7.8.
- Macro impact: event windows with decile-based thresholding.

---

## 21) Acceptance criteria (additions)
- Signals: sample PATH rule fires when `close > 17.20` and `volume_multiple_20d ≥ 1.5`, respects 2-day cooldown.
- Sentiment overlay: background gradient follows `sentiment_daily.score`.
- Analyst verified flag set only when technical momentum and sentiment agree with analyst direction.
- Predictor: returns calibrated `prob_retake_peak_30d`; drivers list sums to ~1.
- Narratives: daily output includes leaders/laggards, signals, sentiment, and recommended nudges.
- Simulator: "sell half on last signal" action yields ghost timeline matching fee/tax assumptions.
- Macro: CPI and FOMC overlays render; impact markers appear for top decile events.
- Alerts: drawdown alert includes cause plus historical analogue window.
- Dashboard: ERI, `%DaysMissed10`, `AvgDD_after_best` compute correctly on seed datasets.

---

## 22) Ops, SLOs, and audit
- SLOs: signal engine completes <2 minutes after market close; narratives <5 minutes.
- Retry/backfill: idempotent upserts keyed by `(symbol, date, source)`.
- Explainability: retain feature snapshots and SHAP artefacts for 90 days.
- Privacy: redact API keys; store `source_url_hash` instead of raw URLs.
- Tracing: use OpenAI Agents SDK traces per symbol/day (ingest → signal → forecast → narrative → alert id).

---

## 23) Seed content (samples)
### 23.1 PATH re-entry rule
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
  "cooldown_days": 2
}
```

### 23.2 Alert template (drawdown)
```json
{
  "template": "drawdown_explain_v1",
  "vars": {
    "symbol": "HPE",
    "magnitude_pct": -3.8,
    "cause": "post-Investor Day guidance",
    "analogue_window": "2022-2023",
    "recovery_days_range": "9-14"
  }
}
```

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

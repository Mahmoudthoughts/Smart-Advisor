# AI Timing Microservice

This FastAPI microservice turns intraday bar data into lightweight timing insights for the Smart Advisor apps. It clusters low/high times, summarizes intraday momentum, and optionally asks an LLM to turn those features into a short recommendation.

## Endpoints

### `GET /health`
Returns basic service status and the current cache size.

### `POST /timing`
Accepts intraday bars and returns best buy/sell windows plus supporting citations and features.

- **Request model**
  - `symbol` (str): Ticker symbol.
  - `symbol_name` (str | null): Optional display name for prompt context.
  - `bar_size` (str): Human-readable bar size (e.g., `5 mins`, `15 mins`, `1 hour`).
  - `duration_days` (int): Number of trading days represented by `bars` (1–60).
  - `timezone` (str | null): Overrides the default session timezone (`AI_TIMING_DEFAULT_TZ`).
  - `use_rth` (bool): Whether bars are regular trading hours only; used in the cache key.
  - `session_summaries` (list[SessionSummaryPayload] | null): Optional precomputed session stats (currently unused; `bars` are required).
  - `bars` (list[IntradayBar]): Chronological or unsorted intraday bars.
    - IntradayBar fields: `date` (ISO timestamp), `open`, `high`, `low`, `close`, `volume` (optional).
  - `force_refresh` (bool): Skip cache lookup and recompute.
  - `llm` (object | null): Overrides for the LLM call.
    - `provider` (str | null): Provider name (defaults to `openai`).
    - `api_key` (str | null): API key; when omitted and provider is `openai`, uses `OPENAI_API_KEY` from settings.
    - `base_url` (str | null): Custom base URL for OpenAI-compatible endpoints (auto retries with and without `/v1`).
    - `model` (str | null): Model name override (defaults to `OPENAI_MODEL`).

- **Response model** (`TimingResponse`)
  - `summary` (str): Short, citation-backed recommendation text.
  - `best_buy_window` (str): Time window label (e.g., `10:00-10:30`).
  - `best_sell_window` (str): Time window label for exits.
  - `confidence` (float): Heuristic confidence between 0–0.95.
  - `citations` (list[{id, text}]): Generated per-feature callouts.
  - `features` (dict): Machine-readable feature payload (see below).

## Feature Model
Features are derived from the incoming bars grouped by session date (respecting the provided or default timezone):

- `session_count`: Number of sessions with at least one bar.
- `median_low_time` / `median_high_time`: Median minutes of day for lows/highs (HH:MM).
- `best_buy_window` / `best_sell_window`: Sliding windows (≈30 minutes worth of buckets) with lowest/highest average z-score vs session mean.
- `bar_minutes`: Parsed minute length for each bucket.
- `avg_pct_from_open_by_bucket`: Average close % vs. session open per minute bucket.
- `avg_zscore_by_bucket`: Average z-score vs. session mean per bucket.
- `symbol`, `symbol_name`, `bar_size`, `duration_days`, `timezone` for traceability.

## Caching
Responses are cached per `(symbol, bar_size, duration_days, timezone, use_rth, bar_count, first_ts, last_ts, llm provider/model/base_url)` for `AI_TIMING_CACHE_TTL_SEC` seconds (default 900). Set `force_refresh=true` to bypass the cache.

## LLM Flow
- If `OPENAI_API_KEY` is unset and the provider is `openai`, the service falls back to a deterministic summary built from features and citations.
- When `base_url` is provided, the service calls that endpoint first and retries with `/v1` trimmed or appended if a `NotFound` error occurs.
- Output parsing accepts raw JSON, fenced JSON code blocks, or free text and normalizes older response shapes (`timing_recommendation`, `time_windows`) when present.

## Command-Line Helpers
- Run locally: `uvicorn main:app --host 0.0.0.0 --port 8300 --reload`
- Health check: `curl http://localhost:8300/health`
- Sample timing request (truncated payload):

```bash
curl -X POST http://localhost:8300/timing \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "SPY",
    "bar_size": "15 mins",
    "duration_days": 5,
    "bars": [
      {"date": "2024-03-01T14:30:00Z", "open": 500, "high": 501, "low": 499, "close": 500.5},
      {"date": "2024-03-01T14:45:00Z", "open": 500.5, "high": 501.2, "low": 500.2, "close": 501.1}
    ]
  }'
```

Environment defaults live in `config.py`: `OPENAI_MODEL`, `OPENAI_API_KEY`, `AI_TIMING_CACHE_TTL_SEC`, and `AI_TIMING_DEFAULT_TZ`.

"""FastAPI entrypoint for the AI timing service."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, status
from openai import OpenAI
from pydantic import BaseModel, Field

from config import get_settings

logger = logging.getLogger("services.ai_timing")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Smart Advisor AI Timing Service", version="0.1.0")


class IntradayBar(BaseModel):
    date: str = Field(..., description="ISO timestamp")
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class SessionSummaryPayload(BaseModel):
    date: str
    bars: int
    open: float | None = None
    midday_low: float | None = None
    close: float | None = None
    drawdown_pct: float | None = None
    recovery_pct: float | None = None


class TimingRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    bar_size: str = Field(..., description="e.g., 5 mins, 15 mins")
    duration_days: int = Field(..., ge=1, le=60)
    timezone: str | None = Field(default=None, description="Timezone for session grouping")
    use_rth: bool = Field(default=True)
    symbol_name: str | None = None
    session_summaries: list[SessionSummaryPayload] | None = None
    bars: list[IntradayBar]


class Citation(BaseModel):
    id: str
    text: str


class TimingResponse(BaseModel):
    summary: str
    best_buy_window: str
    best_sell_window: str
    confidence: float
    citations: list[Citation]
    features: dict[str, Any]


@dataclass
class CacheEntry:
    expires_at: datetime
    payload: dict[str, Any]


_cache: dict[str, CacheEntry] = {}


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "cache_entries": len(_cache)}


@app.post("/timing", response_model=TimingResponse)
async def timing(payload: TimingRequest) -> TimingResponse:
    if not payload.bars:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bars are required.")

    settings = get_settings()
    tz_name = payload.timezone or settings.timezone_default
    cache_key = build_cache_key(payload, tz_name)
    cached = get_cached(cache_key)
    if cached:
        return TimingResponse(**cached)

    features = build_features(payload, tz_name)
    citations = build_citations(features)

    llm_response = await call_llm(payload, features, citations)
    response = {
        "summary": llm_response.get("summary", ""),
        "best_buy_window": llm_response.get("best_buy_window", features["best_buy_window"]),
        "best_sell_window": llm_response.get("best_sell_window", features["best_sell_window"]),
        "confidence": llm_response.get("confidence", features["confidence"]),
        "citations": llm_response.get("citations", citations),
        "features": features,
    }

    set_cache(cache_key, response, settings.cache_ttl_seconds)
    return TimingResponse(**response)


def build_cache_key(payload: TimingRequest, tz_name: str) -> str:
    dates = [bar.date for bar in payload.bars]
    first = min(dates)
    last = max(dates)
    return "|".join(
        [
            payload.symbol.upper(),
            payload.bar_size,
            str(payload.duration_days),
            tz_name,
            "rth" if payload.use_rth else "all",
            str(len(payload.bars)),
            first,
            last,
        ]
    )


def get_cached(key: str) -> dict[str, Any] | None:
    entry = _cache.get(key)
    if not entry:
        return None
    if entry.expires_at < datetime.now(timezone.utc):
        _cache.pop(key, None)
        return None
    return entry.payload


def set_cache(key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
    _cache[key] = CacheEntry(
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        payload=payload,
    )


def build_features(payload: TimingRequest, tz_name: str) -> dict[str, Any]:
    tz = ZoneInfo(tz_name)
    sessions: dict[str, list[dict[str, Any]]] = {}
    for bar in payload.bars:
        dt = parse_datetime(bar.date).astimezone(tz)
        session_key = dt.date().isoformat()
        entry = {
            "dt": dt,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        sessions.setdefault(session_key, []).append(entry)

    session_keys = sorted(sessions.keys())
    bar_minutes = parse_bar_size(payload.bar_size)

    per_session = []
    minute_buckets: dict[int, list[float]] = {}
    zscore_buckets: dict[int, list[float]] = {}
    for session_key in session_keys:
        items = sorted(sessions[session_key], key=lambda x: x["dt"])
        if not items:
            continue
        open_price = items[0]["open"]
        closes = [item["close"] for item in items]
        mean_close = mean(closes)
        std_close = (sum((c - mean_close) ** 2 for c in closes) / len(closes)) ** 0.5
        std_close = std_close if std_close > 0 else 1.0

        low_item = min(items, key=lambda x: x["low"])
        high_item = max(items, key=lambda x: x["high"])
        low_minute = minutes_since_midnight(low_item["dt"])
        high_minute = minutes_since_midnight(high_item["dt"])

        per_session.append(
            {
                "date": session_key,
                "low_time": low_minute,
                "high_time": high_minute,
            }
        )

        for item in items:
            minute = minutes_since_midnight(item["dt"])
            bucket = (minute // bar_minutes) * bar_minutes
            pct_from_open = (item["close"] - open_price) / open_price if open_price else 0.0
            zscore = (item["close"] - mean_close) / std_close
            minute_buckets.setdefault(bucket, []).append(pct_from_open)
            zscore_buckets.setdefault(bucket, []).append(zscore)

    if not per_session:
        return {
            "best_buy_window": "n/a",
            "best_sell_window": "n/a",
            "confidence": 0.0,
            "session_count": 0,
        }

    median_low = median([s["low_time"] for s in per_session])
    median_high = median([s["high_time"] for s in per_session])

    bucket_minutes = sorted(minute_buckets.keys())
    zscore_by_bucket = [mean(zscore_buckets[bucket]) for bucket in bucket_minutes]

    window_size = max(1, int(round(30 / bar_minutes)))
    best_buy_idx = sliding_argmin(zscore_by_bucket, window_size)
    best_sell_idx = sliding_argmax(zscore_by_bucket, window_size)

    buy_window = minute_window_label(bucket_minutes, best_buy_idx, window_size, bar_minutes)
    sell_window = minute_window_label(bucket_minutes, best_sell_idx, window_size, bar_minutes)

    confidence = compute_confidence(
        session_count=len(per_session),
        buy_strength=abs(zscore_by_bucket[best_buy_idx]),
        sell_strength=abs(zscore_by_bucket[best_sell_idx]),
    )

    return {
        "symbol": payload.symbol.upper(),
        "symbol_name": payload.symbol_name,
        "bar_size": payload.bar_size,
        "duration_days": payload.duration_days,
        "timezone": tz_name,
        "session_count": len(per_session),
        "median_low_time": format_minute(median_low),
        "median_high_time": format_minute(median_high),
        "best_buy_window": buy_window,
        "best_sell_window": sell_window,
        "confidence": confidence,
        "bar_minutes": bar_minutes,
        "avg_pct_from_open_by_bucket": {
            format_minute(bucket): mean(values) for bucket, values in minute_buckets.items()
        },
        "avg_zscore_by_bucket": {format_minute(bucket): mean(values) for bucket, values in zscore_buckets.items()},
    }


def build_citations(features: dict[str, Any]) -> list[Citation]:
    sessions = features.get("session_count", 0)
    return [
        Citation(
            id="C1",
            text=f"Median low time across {sessions} sessions: {features.get('median_low_time', 'n/a')}.",
        ),
        Citation(
            id="C2",
            text=f"Median high time across {sessions} sessions: {features.get('median_high_time', 'n/a')}.",
        ),
        Citation(
            id="C3",
            text=f"Lowest z-score window: {features.get('best_buy_window', 'n/a')}.",
        ),
        Citation(
            id="C4",
            text=f"Highest z-score window: {features.get('best_sell_window', 'n/a')}.",
        ),
    ]


async def call_llm(
    payload: TimingRequest, features: dict[str, Any], citations: list[Citation]
) -> dict[str, Any]:
    if features.get("session_count", 0) < 2:
        return {
            "summary": "Not enough sessions to estimate reliable intraday timing.",
            "best_buy_window": features.get("best_buy_window", "n/a"),
            "best_sell_window": features.get("best_sell_window", "n/a"),
            "confidence": 0.0,
            "citations": [c.dict() for c in citations],
        }

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    prompt = {
        "symbol": payload.symbol.upper(),
        "symbol_name": payload.symbol_name,
        "bar_size": payload.bar_size,
        "duration_days": payload.duration_days,
        "timezone": features.get("timezone"),
        "best_buy_window": features.get("best_buy_window"),
        "best_sell_window": features.get("best_sell_window"),
        "confidence": features.get("confidence"),
        "features": {
            "median_low_time": features.get("median_low_time"),
            "median_high_time": features.get("median_high_time"),
            "session_count": features.get("session_count"),
        },
        "citations": [c.dict() for c in citations],
    }

    logger.info("AI timing prompt: %s", json.dumps(prompt, ensure_ascii=True))

    schema = {
        "name": "timing_response",
        "schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "best_buy_window": {"type": "string"},
                "best_sell_window": {"type": "string"},
                "confidence": {"type": "number"},
                "citations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
                        "required": ["id", "text"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["summary", "best_buy_window", "best_sell_window", "confidence", "citations"],
            "additionalProperties": False,
        },
    }

    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a trading assistant. Provide educational, non-financial advice. "
                        "Use only the provided citations in square brackets like [C1]. "
                        "Do not mention you are an AI. Keep it concise."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Using the provided intraday feature summary, write a short recommendation "
                        "for day-trading timing. Use citations for every factual claim. "
                        "Return JSON matching the schema."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
            ],
            response_format={"type": "json_schema", "json_schema": schema},
        )
        parsed = json.loads(response.output_text)
        logger.info("AI timing response: %s", json.dumps(parsed, ensure_ascii=True))
        return parsed
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("AI timing call failed: %s", exc)
        return {
            "summary": (
                "Based on the recent sessions, the intraday lows tend to cluster around "
                f"{features.get('median_low_time')} and highs around {features.get('median_high_time')}. "
                f"Consider the buy window {features.get('best_buy_window')} and sell window "
                f"{features.get('best_sell_window')} as the most consistent timing bands. "
                "Use these as a timing reference, not a guarantee."
            ),
            "best_buy_window": features.get("best_buy_window", "n/a"),
            "best_sell_window": features.get("best_sell_window", "n/a"),
            "confidence": features.get("confidence", 0.0),
            "citations": [c.dict() for c in citations],
        }


def parse_datetime(value: str) -> datetime:
    cleaned = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_bar_size(value: str) -> int:
    value = value.strip().lower()
    parts = value.split()
    if not parts:
        return 15
    number = int(parts[0])
    unit = parts[1] if len(parts) > 1 else "mins"
    if unit.startswith("hour"):
        return number * 60
    return number


def minutes_since_midnight(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def median(values: Iterable[int]) -> int:
    sorted_vals = sorted(values)
    if not sorted_vals:
        return 0
    mid = len(sorted_vals) // 2
    if len(sorted_vals) % 2 == 0:
        return int((sorted_vals[mid - 1] + sorted_vals[mid]) / 2)
    return sorted_vals[mid]


def format_minute(minute: int) -> str:
    hour = minute // 60
    minute = minute % 60
    return f"{hour:02d}:{minute:02d}"


def minute_window_label(
    buckets: list[int], idx: int, window_size: int, bar_minutes: int
) -> str:
    start = buckets[idx]
    end = start + window_size * bar_minutes
    return f"{format_minute(start)}–{format_minute(end)}"


def sliding_argmin(values: list[float], window: int) -> int:
    best_idx = 0
    best_score = float("inf")
    for i in range(0, max(1, len(values) - window + 1)):
        score = mean(values[i : i + window])
        if score < best_score:
            best_score = score
            best_idx = i
    return best_idx


def sliding_argmax(values: list[float], window: int) -> int:
    best_idx = 0
    best_score = float("-inf")
    for i in range(0, max(1, len(values) - window + 1)):
        score = mean(values[i : i + window])
        if score > best_score:
            best_score = score
            best_idx = i
    return best_idx


def compute_confidence(session_count: int, buy_strength: float, sell_strength: float) -> float:
    base = min(0.6, session_count / 10)
    strength = min(0.35, (abs(buy_strength) + abs(sell_strength)) / 6)
    return round(min(0.95, base + strength), 2)

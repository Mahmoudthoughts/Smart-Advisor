"""Rule evaluation engine for Smart Advisor signals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable, List

import pandas as pd

from app.schemas.signals import SignalRuleDefinition

COMPARATORS = {
    ">": lambda lhs, rhs: lhs > rhs,
    ">=": lambda lhs, rhs: lhs >= rhs,
    "<": lambda lhs, rhs: lhs < rhs,
    "<=": lambda lhs, rhs: lhs <= rhs,
    "==": lambda lhs, rhs: lhs == rhs,
    "!=": lambda lhs, rhs: lhs != rhs,
}


@dataclass
class SignalCandidate:
    symbol: str
    rule_id: str
    date: date
    payload: dict[str, Any]


def _resolve_value(df: pd.DataFrame, token: Any) -> Any:
    if isinstance(token, str) and token in df.columns:
        return df[token]
    return token


def _evaluate_expression(df: pd.DataFrame, expression: dict[str, Any]) -> pd.Series:
    if "all" in expression:
        series = [
            _evaluate_expression(df, clause)
            if isinstance(clause, dict)
            else clause
            for clause in expression["all"]
        ]
        return pd.concat(series, axis=1).all(axis=1)
    if "any" in expression:
        series = [
            _evaluate_expression(df, clause)
            if isinstance(clause, dict)
            else clause
            for clause in expression["any"]
        ]
        return pd.concat(series, axis=1).any(axis=1)
    if "not" in expression:
        return ~_evaluate_expression(df, expression["not"])
    indicator = expression.get("indicator")
    op = expression.get("op")
    value = expression.get("value")
    if indicator is None or op not in COMPARATORS:
        raise ValueError(f"Invalid rule expression leaf: {expression}")
    lhs = _resolve_value(df, indicator)
    rhs = _resolve_value(df, value)
    comparator = COMPARATORS[op]
    if isinstance(lhs, pd.Series) and isinstance(rhs, pd.Series):
        return comparator(lhs, rhs)
    if isinstance(lhs, pd.Series):
        return comparator(lhs, rhs)
    if isinstance(rhs, pd.Series):
        return comparator(lhs, rhs)
    return pd.Series([comparator(lhs, rhs)] * len(df), index=df.index)


def evaluate_rule(symbol: str, df: pd.DataFrame, rule: SignalRuleDefinition) -> List[SignalCandidate]:
    """Evaluate a single rule over indicator dataframe."""

    mask = _evaluate_expression(df, rule.expression)
    mask = mask.fillna(False)
    cooldown = rule.cooldown_days
    cooldown_until: date | None = None
    candidates: list[SignalCandidate] = []
    for idx, triggered in mask.items():
        if not triggered:
            continue
        trigger_date = pd.to_datetime(idx).date()
        if cooldown_until and trigger_date <= cooldown_until:
            continue
        cooldown_until = trigger_date + timedelta(days=cooldown)
        payload = {"rule_id": rule.rule_id, "symbol": symbol}
        candidates.append(SignalCandidate(symbol=symbol, rule_id=rule.rule_id, date=trigger_date, payload=payload))
    return candidates


def evaluate_rules(symbol: str, df: pd.DataFrame, rules: Iterable[SignalRuleDefinition]) -> List[SignalCandidate]:
    """Evaluate multiple rules and return deduplicated candidates."""

    seen: set[tuple[str, date]] = set()
    results: list[SignalCandidate] = []
    for rule in rules:
        for candidate in evaluate_rule(symbol, df, rule):
            key = (rule.rule_id, candidate.date)
            if key in seen:
                continue
            seen.add(key)
            results.append(candidate)
    return results


__all__ = ["evaluate_rule", "evaluate_rules", "SignalCandidate"]

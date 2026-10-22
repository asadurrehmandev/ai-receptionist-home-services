"""Latency rollups for the dashboard and the scenario suite."""

from __future__ import annotations

import math


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[low])
    weight = rank - low
    return float(ordered[low] * (1 - weight) + ordered[high] * weight)


def summarize(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "avg_ms": None, "p50_ms": None, "p95_ms": None, "max_ms": None}
    return {
        "count": len(values),
        "avg_ms": round(sum(values) / len(values), 2),
        "p50_ms": round(percentile(values, 0.50) or 0, 2),
        "p95_ms": round(percentile(values, 0.95) or 0, 2),
        "max_ms": round(max(values), 2),
    }

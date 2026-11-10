"""Glucose / CGM analysis.

Operates on :class:`GlucoseReading` records (mg/dL). Produces clinically-labeled
summary statistics. NOTE: estimated A1c is a math conversion of mean glucose
(ADAG), not a lab value, and nothing here is medical advice.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List

from ..models import GlucoseReading

# ADAG conversion: A1c(%) = (mean_mgdl + 46.7) / 28.7  (eAG formula reversed)
# A1c(mmol/mol) = (A1c% - 2.15) * 10.929


def glucose_metrics(readings: List[GlucoseReading], hypo: float = 70.0,
                    target_low: float = 70.0, target_high: float = 180.0) -> Dict:
    if not readings:
        return {"has_data": False}
    vals = [r.value for r in readings]
    n = len(vals)
    below = sum(1 for v in vals if v < hypo)
    in_range = sum(1 for v in vals if target_low <= v <= target_high)
    above = sum(1 for v in vals if v > target_high)
    mean = sum(vals) / n
    svals = sorted(vals)
    median = svals[n // 2] if n % 2 else (svals[n // 2 - 1] + svals[n // 2]) / 2
    # per-day coverage
    days: Dict[date, int] = {}
    for r in readings:
        days[r.day] = days.get(r.day, 0) + 1
    complete_days = sum(1 for c in days.values() if c >= 200)  # ~ a full day of 5-min readings
    eA1c_pct = (mean + 46.7) / 28.7
    eA1c_mmol = (eA1c_pct - 2.15) * 10.929
    return {
        "has_data": True,
        "readings": n,
        "days_covered": len(days),
        "complete_days": complete_days,
        "mean": round(mean, 1),
        "median": round(median, 1),
        "min": round(min(vals), 1),
        "max": round(max(vals), 1),
        "below_pct": round(100.0 * below / n, 1),
        "in_range_pct": round(100.0 * in_range / n, 1),
        "above_pct": round(100.0 * above / n, 1),
        "est_a1c_pct": round(eA1c_pct, 1),
        "est_a1c_mmol": round(eA1c_mmol, 1),
        "hypo_events": below,
    }


def glucose_for_day(readings: List[GlucoseReading], day: date) -> List[GlucoseReading]:
    return [r for r in readings if r.day == day]


def latest_reading(readings: List[GlucoseReading]) -> GlucoseReading | None:
    return max(readings, key=lambda r: r.timestamp) if readings else None

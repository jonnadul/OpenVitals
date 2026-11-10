"""Fasting-window analysis.

Infers 16:8 (or any clock-anchored) fasting adherence from meal timestamps.
Apple Health has no native fasting metric — adherence is derived from *when*
food was logged. Water does not break the fast (configurable).
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Dict, List

from ..models import Meal
from ..types import day_of


def _is_water(meal: Meal) -> bool:
    t = meal.text.lower()
    return any(w in t for w in ("water", "💧", "hydrat", "sparkling"))


def compute_fasting(meals: List[Meal], start_hour: int = 9, end_hour: int = 17,
                    water_exempt: bool = True) -> Dict:
    """Return a fasting summary derived from meal timestamps."""
    food_meals = [m for m in meals if not (water_exempt and _is_water(m))]
    if not food_meals:
        return {"has_data": False, "reason": "no food entries"}

    in_window = 0
    slips = 0
    first_ts: datetime | None = None
    last_ts: datetime | None = None
    per_day: Dict[str, Dict] = {}

    for m in sorted(food_meals, key=lambda x: x.timestamp):
        h = m.timestamp.hour + m.timestamp.minute / 60.0
        inside = start_hour <= h < end_hour
        if inside:
            in_window += 1
        else:
            slips += 1
        if first_ts is None or m.timestamp < first_ts:
            first_ts = m.timestamp
        if last_ts is None or m.timestamp > last_ts:
            last_ts = m.timestamp
        dkey = m.day.isoformat()
        day = per_day.setdefault(dkey, {"in_window": 0, "slips": 0, "meals": 0})
        day["meals"] += 1
        if inside:
            day["in_window"] += 1
        else:
            day["slips"] += 1

    total = in_window + slips
    coverage_days = len(per_day)
    return {
        "has_data": True,
        "window": f"{start_hour:02d}:00–{end_hour:02d}:00",
        "in_window": in_window,
        "slips": slips,
        "adherence_pct": round(100.0 * in_window / total, 1) if total else 0.0,
        "first_food": first_ts.isoformat(sep=" ") if first_ts else None,
        "last_food": last_ts.isoformat(sep=" ") if last_ts else None,
        "coverage_days": coverage_days,
        "per_day": per_day,
        "meals": [
            {"ts": m.timestamp.isoformat(sep=" "), "text": m.text,
             "in_window": (start_hour <= (m.timestamp.hour + m.timestamp.minute / 60.0) < end_hour)}
            for m in sorted(food_meals, key=lambda x: x.timestamp)
        ],
    }

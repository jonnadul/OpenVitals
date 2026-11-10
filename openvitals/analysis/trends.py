"""Time-series helpers for OpenVitals analysis."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from ..models import Observation


def _pick_source(obs: Observation, priority: List[str]) -> int:
    if not priority:
        return 0
    try:
        return priority.index(obs.source)
    except ValueError:
        return len(priority)


def daily_latest(observations: List[Observation], metric: str,
                 source_priority: Optional[List[str]] = None) -> Dict[date, Observation]:
    """Latest reading per calendar day for a metric (respecting source priority)."""
    out: Dict[date, Observation] = {}
    for o in observations:
        if o.metric != metric:
            continue
        cur = out.get(o.day)
        if cur is None or o.timestamp > cur.timestamp or (
            o.timestamp == cur.timestamp and _pick_source(o, source_priority) < _pick_source(cur, source_priority)
        ):
            out[o.day] = o
    return out


def latest_value(observations: List[Observation], metric: str,
                 source_priority: Optional[List[str]] = None) -> Optional[Tuple[float, date]]:
    series = daily_latest(observations, metric, source_priority)
    if not series:
        return None
    day = max(series)
    return series[day].value, day


def values_in_window(observations: List[Observation], metric: str, days: int,
                     as_of: date) -> List[Tuple[date, float]]:
    out = daily_latest(observations, metric)
    cutoff = as_of.toordinal() - days
    return sorted(((d, o.value) for d, o in out.items() if d.toordinal() >= cutoff), key=lambda x: x[0])


def sleep_total_per_day(sleep) -> Dict[date, float]:
    """Best (longest) sleep session total per day."""
    from ..types import day_of
    best: Dict[date, float] = {}
    for s in sleep:
        d = day_of(s.start)
        best[d] = max(best.get(d, 0.0), s.total_sleep_h)
    return best


def steps_per_day(observations: List[Observation]) -> Dict[date, float]:
    return {d: o.value for d, o in daily_latest(observations, "step_count").items()}

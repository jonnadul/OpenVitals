"""Insight / coaching profiles.

An :class:`InsightProfile` turns an analyzed dataset into a short list of
human-readable insights. The bundled :class:`DiabetesLongevityProfile` is a
*reference example* only — it is evidence-flavored but is NOT medical advice and
is fully configurable. Users can supply their own profile (a Python class or a
config-driven rule set) via ``analysis.insight_profile``.

Every insight carries a ``level`` (good / info / warn / alert) and an optional
``cite`` string so dashboards can show provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..models import HealthData

# Guidance levels map to colors in the dashboard renderer.
LEVEL_GOOD = "good"
LEVEL_INFO = "info"
LEVEL_WARN = "warn"
LEVEL_ALERT = "alert"


@dataclass
class Insight:
    level: str
    text: str
    cite: Optional[str] = None


class InsightProfile:
    """Base class. Override :meth:`build`."""

    name: str = "base"

    def build(self, data: HealthData, dataset: Dict[str, Any], cfg: Any) -> List[Insight]:
        return []


class DiabetesLongevityProfile(InsightProfile):
    """Reference profile: balances glycemic control with longevity signals.

    Reads thresholds from the analysis config (glucose bands, fasting window) so
    it adapts to the user. Citations are illustrative, not a literature review.
    """

    name = "diabetes_longevity"

    def build(self, data: HealthData, dataset: Dict[str, Any], cfg: Any) -> List[Insight]:
        out: List[Insight] = []
        ana = getattr(cfg, "analysis", None)
        hypo = getattr(ana, "glucose_hypo", 70.0)
        thigh = getattr(ana, "glucose_target_high", 180.0)

        g = dataset.get("glucose", {})
        if g.get("has_data"):
            if g.get("below_pct", 0) > 4:
                out.append(Insight(LEVEL_ALERT,
                    f"{g['below_pct']}% of CGM readings are below {hypo:.0f} mg/dL — watch for hypoglycemia.",
                    "CGM"))
            if g.get("above_pct", 0) > 25:
                out.append(Insight(LEVEL_WARN,
                    f"{g['above_pct']}% of readings exceed {thigh:.0f} mg/dL. Post-meal walks + medication adherence help.",
                    "ADA 2025"))
            else:
                out.append(Insight(LEVEL_GOOD,
                    f"Time-in-range looks reasonable ({g.get('in_range_pct', 0)}% in 70–180).",
                    "CGM"))

        fast = dataset.get("fasting", {})
        if fast.get("has_data"):
            pct = fast.get("adherence_pct", 0)
            if pct >= 80:
                out.append(Insight(LEVEL_GOOD,
                    f"Fasting-window adherence {pct}% across {fast.get('coverage_days')} days.",
                    "16:8"))
            elif pct >= 50:
                out.append(Insight(LEVEL_INFO,
                    f"Fasting-window adherence {pct}% — protect the window on low-sleep days.",
                    "16:8"))
            else:
                out.append(Insight(LEVEL_WARN,
                    f"Fasting-window adherence only {pct}%.", "16:8"))

        meds = dataset.get("medications", {})
        for name, m in meds.items():
            if m.get("adherence_pct", 100) < 80:
                out.append(Insight(LEVEL_ALERT,
                    f"{name} adherence {m['adherence_pct']}% — missed {len(m.get('missed_days', []))} day(s).",
                    "Walker 2020"))

        sleep = dataset.get("sleep_series", [])
        if sleep:
            recent = [v for _, v in sleep[-7:]]
            if recent and sum(recent) / len(recent) < 6.5:
                out.append(Insight(LEVEL_WARN,
                    "Recent sleep under 6.5h on average — short sleep raises insulin resistance.",
                    "Darraj 2023"))

        if not out:
            out.append(Insight(LEVEL_INFO, "No strong signals this period. Keep the consistent baseline."))
        return out


_PROFILES = {
    "diabetes_longevity": DiabetesLongevityProfile,
}


def get_profile(name: Optional[str]) -> InsightProfile:
    if not name:
        return InsightProfile()
    return _PROFILES.get(name, InsightProfile())()

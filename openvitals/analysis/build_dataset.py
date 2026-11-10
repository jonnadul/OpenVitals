"""Build the dashboard dataset from normalized HealthData + Config.

The returned dict is the single source of truth the dashboard renderer embeds.
It contains FULL series (all days); the renderer applies the window selector
client-side so the page stays self-contained and offline.
"""

from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from typing import Any, Dict, List

from ..config import Config
from ..models import HealthData
from . import fasting as fasting_mod
from . import glucose as glucose_mod
from . import medications as meds_mod
from . import trends as trends_mod
from .correlation import pearson, pearson_pvalue, slope
from .insights import get_profile


def _series_to_pairs(d) -> List[List[Any]]:
    out: List[List[Any]] = []
    for d0, v in sorted(d.items()):
        val = getattr(v, "value", v)
        if not isinstance(val, (int, float)) or not isfinite(val):
            continue
        out.append([d0.isoformat(), round(float(val), 3)])
    return out


def build_dataset(data: HealthData, cfg: Config) -> Dict[str, Any]:
    ana = cfg.analysis
    dash = cfg.dashboard
    as_of = _max_day(data) or date.today()

    metrics_out: List[Dict] = []
    for md in dash.metrics:
        series = trends_mod.daily_latest(data.observations, md.key, md.source_priority)
        pairs = _series_to_pairs(series)
        latest = None
        latest_date = None
        if pairs:
            latest = pairs[-1][1]
            latest_date = pairs[-1][0]
        sl = None
        if len(pairs) >= 3:
            xs = list(range(len(pairs)))
            ys = [p[1] for p in pairs]
            sl = round(slope(xs, ys), 4)
        metrics_out.append({
            "key": md.key, "label": md.label, "unit": md.unit, "section": md.section,
            "latest": latest, "latest_date": latest_date, "slope": sl, "series": pairs,
        })

    sleep_series = _series_to_pairs(trends_mod.sleep_total_per_day(data.sleep))
    steps_series = _series_to_pairs(trends_mod.steps_per_day(data.observations))
    weight_series = _series_to_pairs(trends_mod.daily_latest(data.observations, "body_mass"))

    glucose = glucose_mod.glucose_metrics(data.glucose, ana.glucose_hypo, ana.glucose_target_low, ana.glucose_target_high)
    glucose_readings = [[r.timestamp.isoformat(sep=" "), round(r.value, 1)] for r in sorted(data.glucose, key=lambda x: x.timestamp)]

    meals = [{"ts": m.timestamp.isoformat(sep=" "), "text": m.text,
              "calories": m.calories, "day": m.day.isoformat()}
             for m in sorted(data.meals, key=lambda x: x.timestamp)]

    fasting = fasting_mod.compute_fasting(data.meals, ana.fast_start_hour, ana.fast_end_hour,
                                          ana.water_does_not_break_fast)

    medications = meds_mod.adherence(data.medications)

    nutrition = [{"day": n.day.isoformat(), "calories": n.calories, "protein_g": n.protein_g,
                  "carbs_g": n.carbs_g, "fat_g": n.fat_g, "fiber_g": n.fiber_g, "water_ml": n.water_ml}
                 for n in sorted(data.nutrition, key=lambda x: x.day)]

    dataset: Dict[str, Any] = {
        "meta": {
            "title": dash.title,
            "generated_at": datetime.now().isoformat(sep=" "),
            "as_of": as_of.isoformat(),
            "sources": sorted(data.sources()),
            "windows": dash.windows,
            "default_window": dash.default_window,
            "sections": dash.sections,
            "weight_axis": dash.weight_axis,
            "show_ai_summary": dash.show_ai_summary,
            "counts": {
                "observations": len(data.observations),
                "workouts": len(data.workouts),
                "medications": len(data.medications),
                "sleep": len(data.sleep),
                "meals": len(data.meals),
                "glucose": len(data.glucose),
                "nutrition": len(data.nutrition),
            },
        },
        "metrics": metrics_out,
        "sleep_series": sleep_series,
        "steps_series": steps_series,
        "weight_series": weight_series,
        "glucose": {**glucose, "readings": glucose_readings},
        "meals": meals,
        "fasting": fasting,
        "medications": medications,
        "nutrition": nutrition,
    }

    profile = get_profile(ana.insight_profile)
    insights = profile.build(data, dataset, cfg)
    dataset["insights"] = [{"level": i.level, "text": i.text, "cite": i.cite} for i in insights]

    # A couple of headline correlations (window-independent; reported with n+p)
    corr = _headline_correlations(data)
    dataset["correlations"] = corr
    return dataset


def _max_day(data: HealthData) -> date | None:
    days = set()
    for o in data.observations:
        days.add(o.day)
    for s in data.sleep:
        days.add(s.start.date())
    for g in data.glucose:
        days.add(g.day)
    for n in data.nutrition:
        days.add(n.day)
    return max(days) if days else None


def _headline_correlations(data: HealthData) -> List[Dict]:
    out: List[Dict] = []
    sleep = trends_mod.sleep_total_per_day(data.sleep)
    steps = trends_mod.steps_per_day(data.observations)
    common = sorted(set(sleep) & set(steps))
    if len(common) >= 8:
        xs = [sleep[d] for d in common]
        ys = [steps[d] for d in common]
        r = pearson(xs, ys)
        p = pearson_pvalue(r, len(xs))
        out.append({"a": "sleep", "b": "steps", "r": round(r, 3), "n": len(xs),
                    "p": round(p, 4), "significant": p < 0.05})
    return out

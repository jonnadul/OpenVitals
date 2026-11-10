"""Apple Health connector (Health Auto Export → JSON/JSONL).

This parses the JSON payloads produced by the iOS app **Health Auto Export**
(HAE) "Health Metrics" and "Workouts" REST automations. Each push is one JSON
object; the receiver typically appends them to a ``.jsonl`` file (one object per
line) or stores them as ``latest.json``.

Expected shape (per push)::

    {
      "received_at": "2026-...",
      "metrics": [
        {"name": "step_count", "units": "count",
         "data": [{"date": "2026-07-12 07:38:33 -0700", "qty": 1234, "source": "iPhone"}]}
      ],
      "workouts": [
        {"start": "...", "end": "...", "duration": 3600, "name": "Walk",
         "activeEnergyBurned": {"qty": 320, "units": "kcal"},
         "distance": {"qty": 5.2, "units": "km"}, "heartRate": {"avg": 120}}
      ]
    }

The parser is tolerant: it accepts either a single JSON object, a JSON array of
objects, or a JSONL file (one object per line). Unknown keys are ignored.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, Iterable, List

from ..config import SourceConfig
from ..models import (
    HealthData,
    Observation,
    Workout,
    Medication,
    GlucoseReading,
)
from ..types import day_of, MedicationStatus
from .base import SourceConnector


def _parse_dt(s: Any) -> datetime:
    if isinstance(s, (int, float)):
        return datetime.fromtimestamp(s)
    s = str(s).strip()
    if not s:
        raise ValueError("empty timestamp")
    s2 = s.replace("T", " ").replace("Z", "+00:00")
    # normalize "+0000" style offsets to "+00:00"
    if len(s2) > 6 and s2[-5] in "+-" and s2[-3] == "0" and ":" not in s2[-6:]:
        s2 = s2[:-2] + ":" + s2[-2:]
    dt = datetime.fromisoformat(s2)
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


# HAE (Health Auto Export) emits a few metric names that differ from
# OpenVitals' canonical names; map the common ones so analysis/dashboard don't
# need source-specific knowledge.
METRIC_ALIASES = {
    "weight_body_mass": "body_mass",
    "body_mass_index": "bmi",
}
GLUCOSE_METRIC = "blood_glucose"


def _nested_qty(v):
    if isinstance(v, dict):
        return _num(v.get("qty"))
    return _num(v)


def _safe_dt(s):
    if not s:
        return None
    try:
        return _parse_dt(s)
    except Exception:
        return None


def parse_payload(obj: Dict[str, Any], source: str = "apple_health") -> HealthData:
    """Parse one HAE push object into HealthData.

    Accepts both the wrapped real HAE format
    (``{received_at, payload: {data: {metrics, workouts, medications}}}``)
    and the flat/legacy format (metrics at the top level).
    """
    data = HealthData()
    payload = obj.get("payload")
    container = payload.get("data", payload) if isinstance(payload, dict) else obj
    if not isinstance(container, dict):
        return data

    # --- metrics (scalar observations) ---
    for m in container.get("metrics", []) or []:
        name = m.get("name")
        if not name:
            continue
        name = METRIC_ALIASES.get(name, name)
        units = m.get("units") or ""
        for pt in m.get("data", []) or []:
            try:
                ts = _parse_dt(pt.get("date") or pt.get("timestamp"))
            except Exception:
                continue
            qty = pt.get("qty")
            if qty is None:
                continue
            try:
                val = float(qty)
            except (TypeError, ValueError):
                continue
            src = pt.get("source")
            if not isinstance(src, str):
                src = source
            data.observations.append(Observation(
                metric=name, value=val, unit=units,
                timestamp=ts, source=src,
            ))
            if name == GLUCOSE_METRIC:
                data.glucose.append(GlucoseReading(
                    timestamp=ts, value=val, source=src,
                ))

    # --- workouts ---
    for w in container.get("workouts", []) or []:
        try:
            start = _parse_dt(w.get("start"))
            end = _parse_dt(w.get("end"))
        except Exception:
            continue
        dur = w.get("duration")
        dur_s = float(dur) if dur is not None else (end - start).total_seconds()
        energy = w.get("activeEnergyBurned") or w.get("energy") or {}
        distance = w.get("distance") or {}
        hr = w.get("heartRate") or {}
        wsrc = w.get("source")
        if not isinstance(wsrc, str):
            wsrc = source
        data.workouts.append(Workout(
            start=start, end=end, duration_s=dur_s,
            name=w.get("name") or "Workout", source=wsrc,
            energy_kcal=_nested_qty(energy.get("qty") if isinstance(energy, dict) else energy),
            distance_km=_nested_qty(distance.get("qty") if isinstance(distance, dict) else distance),
            hr_avg=_nested_qty(hr.get("avg") if isinstance(hr, dict) else hr),
        ))

    # --- medications ---
    for med in container.get("medications", []) or []:
        text = med.get("displayText") or med.get("name") or "Medication"
        status = MedicationStatus.normalize(med.get("status"))
        start_dt = _safe_dt(med.get("start"))
        end_dt = _safe_dt(med.get("end"))
        anchor = start_dt or end_dt
        sch_day = anchor.date() if anchor else date.today()
        taken_at = end_dt if status == MedicationStatus.TAKEN else None
        data.medications.append(Medication(
            name=text, scheduled_day=sch_day, status=status,
            taken_at=taken_at, source=source,
        ))

    return data


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def iter_payloads_from_path(path: str) -> Iterable[Dict[str, Any]]:
    if os.path.isdir(path):
        files = sorted(
            f for f in os.listdir(path)
            if f.endswith(".json") or f.endswith(".jsonl")
        )
        for f in files:
            yield from iter_payloads_from_path(os.path.join(path, f))
        return
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read().strip()
    if not text:
        return
    # JSONL: one object per line (HAE rolling files can be huge — stream lines)
    if "\n" in text and not text.lstrip().startswith("["):
        for line in text.splitlines():
            line = line.strip().rstrip(",")
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
    else:
        obj = json.loads(text)
        if isinstance(obj, list):
            yield from obj
        else:
            yield obj


class AppleHealthConnector(SourceConnector):
    type_key = "apple_health"

    def fetch(self) -> HealthData:
        path = self.params.get("path") or self.params.get("dir")
        if not path:
            raise ValueError("apple_health connector requires params.path (file or dir of HAE JSON/JSONL)")
        source = self.params.get("source", "apple_health")
        merged = HealthData()
        for obj in iter_payloads_from_path(path):
            merged += parse_payload(obj, source=source)
        return merged


register = AppleHealthConnector.register

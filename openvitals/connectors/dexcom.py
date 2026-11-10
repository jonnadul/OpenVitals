"""Dexcom CGM connector — reads a Dexcom data export.

In practice, most Dexcom G7 users get their glucose into OpenVitals via
**Apple Health** (Dexcom → Apple Health → the ``apple_health`` connector's
``blood_glucose`` metric). This connector exists for the direct-export path:
a CSV or JSON export from Dexcom Clarity / the Dexcom API.

CSV columns handled (tolerant): ``Timestamp``, ``Glucose Value (mg/dL)`` (or
``EGV`` / ``Value``), and an optional ``Source`` / ``Trend`` column. JSON is
accepted as a list of ``{"timestamp": ..., "value": ..., "source": ...}``.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from ..config import SourceConfig
from ..models import GlucoseReading, HealthData
from ..types import day_of
from .base import SourceConnector


class DexcomConnector(SourceConnector):
    type_key = "dexcom"

    def fetch(self) -> HealthData:
        path = self.params.get("path")
        if not path or not os.path.exists(path):
            raise ValueError("dexcom connector requires params.path (CSV or JSON export)")
        src = self.params.get("source", "dexcom")
        data = HealthData()
        if path.endswith(".json"):
            with open(path, "r", encoding="utf-8") as fh:
                for row in json.load(fh):
                    data.glucose.append(GlucoseReading(_dt(row["timestamp"]), float(row["value"]), src))
        else:
            with open(path, "r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    ts = _pick(row, ["Timestamp", "Time", "DateTime", "timestamp"])
                    val = _pick(row, ["Glucose Value (mg/dL)", "EGV", "Value", "glucose", "value"])
                    if not (ts and val):
                        continue
                    data.glucose.append(GlucoseReading(_dt(ts), float(val), src))
        return data


def _pick(row: Dict[str, Any], keys: List[str]) -> Any | None:
    lowered = {k.lower(): v for k, v in row.items()}
    for k in keys:
        if k.lower() in lowered and lowered[k.lower()] not in (None, ""):
            return lowered[k.lower()]
    return None


def _dt(s: Any) -> datetime:
    if isinstance(s, (int, float)):
        return datetime.fromtimestamp(s)
    s = str(s).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


register = DexcomConnector.register

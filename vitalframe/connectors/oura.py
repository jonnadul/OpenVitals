"""Oura (Ring) connector — Oura v2 REST API.

Fetches sleep, readiness, and activity summaries and maps them into the
VitalFrame model. Requires a personal access token (``params.token`` or the
``OURA_TOKEN`` environment variable). Token: https://cloud.ouraring.com/personal-access-tokens

Reference endpoints used (v2 ``/usercollection``):
- daily_sleep, sleep        -> SleepSession + sleep observations
- daily_readiness           -> readiness score observation
- daily_activity            -> RHR, steps, HRV observations
"""

from __future__ import annotations

import os
import urllib.request
import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from ..config import SourceConfig
from ..models import (
    GlucoseReading,
    HealthData,
    Observation,
    SleepSession,
)
from ..types import day_of
from .base import SourceConnector


def _get(url: str, token: str) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (user-configured host)
        return json.loads(r.read().decode("utf-8"))


class OuraConnector(SourceConnector):
    type_key = "oura"
    requires_network = True

    def _token(self) -> str:
        return self.params.get("token") or os.environ.get("OURA_TOKEN") or ""

    def fetch(self) -> HealthData:
        token = self._token()
        if not token:
            raise ValueError("oura connector requires params.token or OURA_TOKEN env var")
        end = date.today()
        last_n = int(self.params.get("last_n_days", 120))
        start = end - timedelta(days=last_n)
        base = "https://api.ouraring.com/v2/usercollection"
        src = self.name
        data = HealthData()

        # Sleep
        try:
            resp = _get(f"{base}/sleep?start_date={start}&end_date={end}", token)
            for s in resp.get("data", []):
                begin = _dt(s.get("bedtime_start"))
                fin = _dt(s.get("bedtime_end"))
                total_s = s.get("total_sleep_duration") or 0
                data.sleep.append(SleepSession(
                    begin, fin, round(total_s / 3600.0, 2), src,
                    rem_h=_sec_to_h(s.get("rem_sleep_duration")),
                    deep_h=_sec_to_h(s.get("deep_sleep_duration")),
                    core_h=_sec_to_h(s.get("light_sleep_duration")),
                ))
                if s.get("average_heart_rate") is not None:
                    data.observations.append(Observation("oura_sleep_hr_avg",
                                                        float(s["average_heart_rate"]), "bpm", begin, src))
                if s.get("hrv_average") is not None:
                    data.observations.append(Observation("heart_rate_variability",
                                                        float(s["hrv_average"]), "ms", begin, src))
        except Exception as e:  # network/parse issues shouldn't hard-crash a cron
            data.meta["oura_sleep_error"] = str(e)

        # Readiness
        try:
            resp = _get(f"{base}/daily_readiness?start_date={start}&end_date={end}", token)
            for r in resp.get("data", []):
                d = _dt(r.get("day") or r.get("timestamp"))
                if r.get("score") is not None:
                    data.observations.append(Observation("readiness", float(r["score"]), "score", d, src))
        except Exception as e:
            data.meta["oura_readiness_error"] = str(e)

        # Activity
        try:
            resp = _get(f"{base}/daily_activity?start_date={start}&end_date={end}", token)
            for a in resp.get("data", []):
                d = _dt(a.get("day") or a.get("timestamp"))
                if a.get("resting_heart_rate") is not None:
                    data.observations.append(Observation("resting_heart_rate",
                                                        float(a["resting_heart_rate"]), "bpm", d, src))
                if a.get("steps") is not None:
                    data.observations.append(Observation("step_count", float(a["steps"]), "count", d, src))
                if a.get("average_hrv") is not None:
                    data.observations.append(Observation("heart_rate_variability",
                                                        float(a["average_hrv"]), "ms", d, src))
        except Exception as e:
            data.meta["oura_activity_error"] = str(e)

        return data


def _dt(s: Any) -> datetime:
    if isinstance(s, str):
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    return datetime.fromisoformat(str(s))


def _sec_to_h(v: Any) -> float | None:
    try:
        return round(float(v) / 3600.0, 2)
    except (TypeError, ValueError):
        return None


register = OuraConnector.register

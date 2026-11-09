"""Yazio connector — REST API reference client.

Yazio has no official public API; this is a reference implementation of the
endpoints the Yazio app uses, sufficient for daily nutrition summaries and
consumed-food items. It authenticates with account email/password (stored in
config or env), caches a session token, and fetches:

- ``/user/widgets/daily-summary?date=YYYY-MM-DD`` -> DailyNutrition
- ``/user/consumed-items?date=YYYY-MM-DD``        -> Meals + calorie totals

Use your own account. Credentials live in config (``params.email`` /
``params.password`` or ``YAZIO_EMAIL`` / ``YAZIO_PASSWORD`` env). This connector
does NOT write back to Yazio — it only reads for analysis/dashboarding.
"""

from __future__ import annotations

import os
import urllib.request
import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from ..config import SourceConfig
from ..models import (
    DailyNutrition,
    HealthData,
    Meal,
)
from ..types import day_of
from .base import SourceConnector


class YazioConnector(SourceConnector):
    type_key = "yazio"
    requires_network = True

    def __init__(self, cfg: SourceConfig) -> None:
        super().__init__(cfg)
        self._token: str | None = None

    def _creds(self):
        email = self.params.get("email") or os.environ.get("YAZIO_EMAIL")
        password = self.params.get("password") or os.environ.get("YAZIO_PASSWORD")
        if not (email and password):
            raise ValueError("yazio connector requires params.email/password or YAZIO_EMAIL/YAZIO_PASSWORD")
        return email, password

    def connect(self) -> None:
        email, password = self._creds()
        body = json.dumps({"email": email, "password": password}).encode("utf-8")
        req = urllib.request.Request(
            "https://www.yazio.com/api/login/v1/token",
            data=body, headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            self._token = json.loads(r.read().decode("utf-8")).get("token")

    def _get(self, url: str) -> Dict[str, Any]:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._token}"})
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8"))

    def fetch(self) -> HealthData:
        if not self._token:
            self.connect()
        end = date.today()
        last_n = int(self.params.get("last_n_days", 30))
        data = HealthData()
        src = self.name
        for i in range(last_n):
            day = end - timedelta(days=last_n - 1 - i)
            ds = day.isoformat()
            try:
                summ = self._get(f"https://www.yazio.com/api/user/widgets/daily-summary?date={ds}")
                data.nutrition.append(DailyNutrition(
                    day,
                    calories=_num(summ.get("energy")),
                    protein_g=_num(summ.get("protein")),
                    carbs_g=_num(summ.get("carbs")),
                    fat_g=_num(summ.get("fat")),
                    fiber_g=_num(summ.get("fiber")),
                    water_ml=_num(summ.get("water_intake")),
                    source=src,
                ))
                items = self._get(f"https://www.yazio.com/api/user/consumed-items?date={ds}")
                for it in items.get("items", []) or []:
                    ts = _dt(it.get("datetime") or it.get("date"))
                    data.meals.append(Meal(ts, it.get("name") or it.get("label") or "",
                                           src, calories=_num(it.get("energy")), items=[it]))
            except Exception as e:
                data.meta.setdefault("yazio_errors", []).append({ds: str(e)})
        return data


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _dt(s: Any) -> datetime:
    if isinstance(s, str):
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    return datetime.fromisoformat(str(s))


register = YazioConnector.register

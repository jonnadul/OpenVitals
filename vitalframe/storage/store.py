"""SQLite-backed local store for VitalFrame.

The store is the canonical local copy of normalized health data. Connectors
write into it; analysis and the dashboard read from it (or from an in-memory
``HealthData`` object for one-shot builds).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator, List, Optional

from ..models import (
    DailyNutrition,
    GlucoseReading,
    HealthData,
    Meal,
    Medication,
    Observation,
    SleepSession,
    Workout,
)
from .schema import INDEX_SQL, SCHEMA_SQL


def _iso(dt: datetime) -> str:
    return dt.isoformat(sep=" ")


def _from_iso(s: str) -> datetime:
    s = s.replace("T", " ")
    if " " not in s and "Z" not in s:
        return datetime.fromisoformat(s)
    # tolerate trailing Z
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


class Store:
    """A small, dependency-free SQLite store for normalized health records."""

    def __init__(self, path: str = "data/vitalframe.db") -> None:
        self.path = path
        self._conn = sqlite3.connect(path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.executescript(INDEX_SQL)
        self._conn.commit()

    # -- lifecycle -------------------------------------------------------
    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- ingest ----------------------------------------------------------
    def ingest(self, data: HealthData) -> int:
        """Persist a HealthData batch. Returns the number of rows written."""
        cur = self._conn
        n = 0
        cur.execute("BEGIN")
        try:
            for o in data.observations:
                cur.execute(
                    "INSERT OR REPLACE INTO observations "
                    "(metric, value, unit, timestamp, source, day) VALUES (?,?,?,?,?,?)",
                    (o.metric, o.value, o.unit, _iso(o.timestamp), o.source, o.day.isoformat()),
                )
                n += 1
            for w in data.workouts:
                cur.execute(
                    "INSERT INTO workouts (start,end,duration_s,name,energy_kcal,distance_km,hr_avg,source) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (_iso(w.start), _iso(w.end), w.duration_s, w.name, w.energy_kcal,
                     w.distance_km, w.hr_avg, w.source),
                )
                n += 1
            for m in data.medications:
                cur.execute(
                    "INSERT OR REPLACE INTO medications (name,scheduled_day,status,taken_at,source) VALUES (?,?,?,?,?)",
                    (m.name, m.scheduled_day.isoformat(), m.status.value, _iso(m.taken_at) if m.taken_at else None, m.source),
                )
                n += 1
            for s in data.sleep:
                cur.execute(
                    "INSERT OR REPLACE INTO sleep (start,end,total_sleep_h,rem_h,deep_h,core_h,source) VALUES (?,?,?,?,?,?,?)",
                    (_iso(s.start), _iso(s.end), s.total_sleep_h, s.rem_h, s.deep_h, s.core_h, s.source),
                )
                n += 1
            for ml in data.meals:
                cur.execute(
                    "INSERT INTO meals (timestamp,text,calories,items_json,source,day) VALUES (?,?,?,?,?,?)",
                    (_iso(ml.timestamp), ml.text, ml.calories, json.dumps(ml.items, default=str),
                     ml.source, ml.day.isoformat()),
                )
                n += 1
            for g in data.glucose:
                cur.execute(
                    "INSERT OR REPLACE INTO glucose (timestamp,value,source,day) VALUES (?,?,?,?)",
                    (_iso(g.timestamp), g.value, g.source, g.day.isoformat()),
                )
                n += 1
            for nu in data.nutrition:
                cur.execute(
                    "INSERT OR REPLACE INTO nutrition (day,calories,protein_g,carbs_g,fat_g,fiber_g,water_ml,source) VALUES (?,?,?,?,?,?,?,?)",
                    (nu.day.isoformat(), nu.calories, nu.protein_g, nu.carbs_g, nu.fat_g, nu.fiber_g, nu.water_ml, nu.source),
                )
                n += 1
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise
        return n

    def set_meta(self, key: str, value: str) -> None:
        self._conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (key, value))
        self._conn.commit()

    def get_meta(self, key: str) -> Optional[str]:
        row = self._conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    # -- query -----------------------------------------------------------
    def load(self, since: Optional[date] = None, until: Optional[date] = None) -> HealthData:
        """Load records into an in-memory HealthData (optionally date-bounded)."""
        data = HealthData()
        bounds = self._bounds(since, until)

        for r in self._conn.execute(
            f"SELECT metric,value,unit,timestamp,source,day FROM observations {bounds}", self._args(since, until)
        ):
            data.observations.append(
                Observation(metric=r[0], value=r[1], unit=r[2], timestamp=_from_iso(r[3]),
                            source=r[4], day=date.fromisoformat(r[5]))
            )

        for r in self._conn.execute(
            "SELECT start,end,duration_s,name,energy_kcal,distance_km,hr_avg,source FROM workouts"
        ):
            data.workouts.append(
                Workout(start=_from_iso(r[0]), end=_from_iso(r[1]), duration_s=r[2] or 0.0, name=r[3] or "",
                        energy_kcal=r[4], distance_km=r[5], hr_avg=r[6], source=r[7])
            )

        for r in self._conn.execute(
            "SELECT name,scheduled_day,status,taken_at,source FROM medications"
        ):
            data.medications.append(
                Medication(name=r[0], scheduled_day=date.fromisoformat(r[1]), status=__import__("vitalframe.types", fromlist=["MedicationStatus"]).MedicationStatus(r[2]),
                           taken_at=_from_iso(r[3]) if r[3] else None, source=r[4])
            )

        for r in self._conn.execute(
            "SELECT start,end,total_sleep_h,rem_h,deep_h,core_h,source FROM sleep"
        ):
            data.sleep.append(
                SleepSession(start=_from_iso(r[0]), end=_from_iso(r[1]), total_sleep_h=r[2] or 0.0,
                             rem_h=r[3], deep_h=r[4], core_h=r[5], source=r[6])
            )

        for r in self._conn.execute(
            "SELECT timestamp,text,calories,items_json,source,day FROM meals"
        ):
            items = json.loads(r[3]) if r[3] else []
            data.meals.append(
                Meal(timestamp=_from_iso(r[0]), text=r[1] or "", source=r[4],
                     calories=r[2], items=items, day=date.fromisoformat(r[5]))
            )

        for r in self._conn.execute(
            f"SELECT timestamp,value,source,day FROM glucose {bounds}", self._args(since, until)
        ):
            data.glucose.append(
                GlucoseReading(timestamp=_from_iso(r[0]), value=r[1], source=r[2], day=date.fromisoformat(r[3]))
            )

        for r in self._conn.execute(
            "SELECT day,calories,protein_g,carbs_g,fat_g,fiber_g,water_ml,source FROM nutrition"
        ):
            data.nutrition.append(
                DailyNutrition(day=date.fromisoformat(r[0]), calories=r[1], protein_g=r[2], carbs_g=r[3],
                               fat_g=r[4], fiber_g=r[5], water_ml=r[6], source=r[7])
            )
        return data

    # -- helpers ---------------------------------------------------------
    def _bounds(self, since: Optional[date], until: Optional[date]) -> str:
        if since and until:
            return "WHERE day BETWEEN ? AND ?"
        if since:
            return "WHERE day >= ?"
        if until:
            return "WHERE day <= ?"
        return ""

    def _args(self, since: Optional[date], until: Optional[date]):
        if since and until:
            return (since.isoformat(), until.isoformat())
        if since:
            return (since.isoformat(),)
        if until:
            return (until.isoformat(),)
        return ()

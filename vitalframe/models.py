"""Core data model for VitalFrame.

Every source connector normalizes external data into these plain dataclasses.
The storage layer, analysis modules, and dashboard renderer all consume
``HealthData`` — so a new source only has to produce these records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from .types import MedicationStatus, day_of


@dataclass
class Observation:
    """A single scalar health metric reading (e.g. resting heart rate, weight)."""

    metric: str
    value: float
    unit: str
    timestamp: datetime
    source: str
    day: date = field(default_factory=lambda: date(1970, 1, 1))
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.day == date(1970, 1, 1):
            self.day = day_of(self.timestamp)


@dataclass
class Workout:
    """A single workout / exercise session."""

    start: datetime
    end: datetime
    duration_s: float
    name: str
    source: str
    energy_kcal: Optional[float] = None
    distance_km: Optional[float] = None
    hr_avg: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Medication:
    """A scheduled medication dose and its logged status."""

    name: str
    scheduled_day: date
    status: MedicationStatus
    taken_at: Optional[datetime] = None
    source: str = "medications"


@dataclass
class SleepSession:
    """A single sleep session (one night may contain several)."""

    start: datetime
    end: datetime
    total_sleep_h: float
    source: str
    rem_h: Optional[float] = None
    deep_h: Optional[float] = None
    core_h: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Meal:
    """A logged meal (free-text and/or structured nutrition)."""

    timestamp: datetime
    text: str
    source: str
    calories: Optional[float] = None
    items: List[Dict[str, Any]] = field(default_factory=list)
    day: date = field(default_factory=lambda: date(1970, 1, 1))

    def __post_init__(self) -> None:
        if self.day == date(1970, 1, 1):
            self.day = day_of(self.timestamp)


@dataclass
class GlucoseReading:
    """A single continuous-glucose / blood-glucose reading (mg/dL)."""

    timestamp: datetime
    value: float  # mg/dL
    source: str
    day: date = field(default_factory=lambda: date(1970, 1, 1))

    def __post_init__(self) -> None:
        if self.day == date(1970, 1, 1):
            self.day = day_of(self.timestamp)


@dataclass
class DailyNutrition:
    """Daily aggregated nutrition (from a tracker such as Yazio)."""

    day: date
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    water_ml: Optional[float] = None
    source: str = "nutrition"


@dataclass
class HealthData:
    """The complete, normalized health record set for a user.

    Connectors append into these lists; analysis modules and the dashboard
    read from them. All timestamps are tz-naive local time.
    """

    observations: List[Observation] = field(default_factory=list)
    workouts: List[Workout] = field(default_factory=list)
    medications: List[Medication] = field(default_factory=list)
    sleep: List[SleepSession] = field(default_factory=list)
    meals: List[Meal] = field(default_factory=list)
    glucose: List[GlucoseReading] = field(default_factory=list)
    nutrition: List[DailyNutrition] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def __iadd__(self, other: "HealthData") -> "HealthData":
        self.observations.extend(other.observations)
        self.workouts.extend(other.workouts)
        self.medications.extend(other.medications)
        self.sleep.extend(other.sleep)
        self.meals.extend(other.meals)
        self.glucose.extend(other.glucose)
        self.nutrition.extend(other.nutrition)
        self.meta.update(other.meta)
        return self

    def empty(self) -> bool:
        return not (
            self.observations
            or self.workouts
            or self.medications
            or self.sleep
            or self.meals
            or self.glucose
            or self.nutrition
        )

    def sources(self) -> set:
        s = set()
        for o in self.observations:
            s.add(o.source)
        for w in self.workouts:
            s.add(w.source)
        for m in self.medications:
            s.add(m.source)
        for sl in self.sleep:
            s.add(sl.source)
        for ml in self.meals:
            s.add(ml.source)
        for g in self.glucose:
            s.add(g.source)
        for n in self.nutrition:
            s.add(n.source)
        return s

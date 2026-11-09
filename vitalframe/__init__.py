"""VitalFrame — a self-hosted personal health-data framework.

Ingest from any source, store locally, analyze, and render a private offline
dashboard. See ``README.md`` and ``docs/`` for usage.
"""

__version__ = "0.1.0"

from .models import (
    HealthData,
    Observation,
    Workout,
    Medication,
    SleepSession,
    Meal,
    GlucoseReading,
    DailyNutrition,
)
from .config import Config, load_config

__all__ = [
    "HealthData",
    "Observation",
    "Workout",
    "Medication",
    "SleepSession",
    "Meal",
    "GlucoseReading",
    "DailyNutrition",
    "Config",
    "load_config",
    "__version__",
]

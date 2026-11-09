"""Shared enums and constants for VitalFrame.

Unit conventions (internal canonical form):
- glucose: mg/dL
- distance: kilometers
- energy: kilocalories
- duration: seconds
- mass: kilograms
- sleep: hours
- water/volume: milliliters
"""

from enum import Enum
from datetime import date, datetime, timezone


class MedicationStatus(str, Enum):
    """Normalized medication logging status."""

    TAKEN = "Taken"
    SKIPPED = "Skipped"
    NOT_INTERACTED = "Not Interacted"
    UNKNOWN = "Unknown"

    @classmethod
    def normalize(cls, raw: str) -> "MedicationStatus":
        if raw is None:
            return cls.UNKNOWN
        r = raw.strip().lower()
        if r in ("taken", "took", "logged", "yes"):
            return cls.TAKEN
        if r in ("skipped", "missed", "no"):
            return cls.SKIPPED
        if r in ("not interacted", "pending", "scheduled", "due"):
            return cls.NOT_INTERACTED
        return cls.UNKNOWN


# Glucose clinical bands (mg/dL) — used by the dashboard + analysis.
GLUCOSE_HYPO = 70.0          # below = hypoglycemia risk
GLUCOSE_TARGET_LOW = 70.0
GLUCOSE_TARGET_HIGH = 180.0  # above = elevated
GLUCOSE_HIGH = 180.0

# Fasting window (local clock). Overridable per-config.
DEFAULT_FAST_START_HOUR = 9
DEFAULT_FAST_END_HOUR = 17

# Precision helpers
def to_naive_local(dt: datetime) -> datetime:
    """Normalize a (possibly tz-aware) datetime to tz-naive local time."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def day_of(dt: datetime) -> date:
    return to_naive_local(dt).date()

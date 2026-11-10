"""Tests for glucose analysis."""

from datetime import datetime

from openvitals.models import GlucoseReading
from openvitals.analysis.glucose import glucose_metrics


def _g(v, day="2026-01-01"):
    return GlucoseReading(datetime.fromisoformat(f"{day}T08:00:00"), v, "test")


def test_metrics_basic():
    readings = [_g(70), _g(100), _g(130), _g(200)]
    m = glucose_metrics(readings, hypo=70, target_low=70, target_high=180)
    assert m["has_data"]
    assert m["mean"] == 125.0
    # 70,100,130 in [70,180] (3); 200 above (1) -> 75% in range
    assert m["in_range_pct"] == 75.0
    assert m["above_pct"] == 25.0
    assert m["below_pct"] == 0.0
    # est A1c = (125 + 46.7)/28.7 ≈ 5.98, rounded to 1 decimal
    assert m["est_a1c_pct"] == 6.0


def test_empty():
    assert not glucose_metrics([])["has_data"]

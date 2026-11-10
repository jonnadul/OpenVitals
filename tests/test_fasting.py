"""Tests for fasting-window analysis."""

from datetime import datetime

from openvitals.models import Meal
from openvitals.analysis.fasting import compute_fasting


def _meal(hour, text="lunch: salad"):
    return Meal(datetime(2026, 1, 1, hour, 0), text, "test")


def test_window_adherence():
    meals = [_meal(9), _meal(13), _meal(19)]  # 2 in window (9-17), 1 slip
    f = compute_fasting(meals, 9, 17, water_exempt=True)
    assert f["has_data"]
    assert f["in_window"] == 2
    assert f["slips"] == 1
    assert abs(f["adherence_pct"] - 66.7) < 0.1


def test_water_exempt():
    meals = [_meal(9), _meal(13), _meal(20, "water 500ml")]
    f = compute_fasting(meals, 9, 17, water_exempt=True)
    # water at 20:00 must NOT count as a slip
    assert f["slips"] == 0
    assert f["in_window"] == 2


def test_no_data():
    f = compute_fasting([], 9, 17)
    assert not f["has_data"]

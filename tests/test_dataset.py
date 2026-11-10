"""End-to-end test: synthetic connector -> dataset -> render (self-contained)."""

import json
import os
import tempfile
from datetime import datetime

from openvitals.config import Config, SourceConfig
from openvitals.connectors.synthetic import SyntheticConnector
from openvitals.analysis.build_dataset import build_dataset
from openvitals.dashboard import render, verify_self_contained
from openvitals.models import HealthData, Meal, Observation


def _config():
    return Config.from_dict({
        "storage": {"path": ":memory:"},
        "dashboard": {
            "title": "Test",
            "metrics": [
                {"key": "resting_heart_rate", "label": "RHR", "unit": "bpm", "section": "recovery"},
                {"key": "body_mass", "label": "Weight", "unit": "kg", "section": "weight"},
                {"key": "blood_glucose", "label": "Glucose", "unit": "mg/dL", "section": "glucose"},
            ],
        },
        "analysis": {"fast_start_hour": 9, "fast_end_hour": 17, "insight_profile": "diabetes_longevity"},
    })


def _synthetic(days=30, seed=3):
    conn = SyntheticConnector(SourceConfig(type="synthetic", name="demo", params={"days": days, "seed": seed}))
    return conn.fetch()


def test_synthetic_pipeline():
    data = _synthetic(30, 3)
    assert data.glucose
    assert data.observations
    assert data.medications

    ds = build_dataset(data, _config())
    assert ds["meta"]["counts"]["glucose"] == len(data.glucose)
    assert ds["glucose"]["has_data"]
    assert ds["fasting"]["has_data"]
    assert "insights" in ds and ds["insights"]


def test_dashboard_receives_configured_glucose_thresholds():
    cfg = _config()
    cfg.analysis.glucose_hypo = 65
    cfg.analysis.glucose_target_low = 80
    cfg.analysis.glucose_target_high = 160
    meta = build_dataset(_synthetic(2), cfg)["meta"]
    assert meta["glucose_hypo"] == 65
    assert meta["glucose_target_low"] == 80
    assert meta["glucose_target_high"] == 160


def test_snapshot_anchor_includes_latest_meal_timestamp():
    data = HealthData(
        observations=[Observation("step_count", 1000, "steps", datetime(2025, 2, 10, 12), "fixture")],
        meals=[Meal(datetime(2025, 2, 11, 23, 30), "Synthetic supper", "fixture")],
    )
    ds = build_dataset(data, Config())
    assert ds["meta"]["as_of"] == "2025-02-11"


def test_render_self_contained():
    data = _synthetic(20, 1)
    ds = build_dataset(data, _config())

    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "dash.html")
        render(ds, out)
        checks = verify_self_contained(out)
        assert checks["http_links"] == 0
        assert checks["https_links"] == 0
        assert checks["script_src"] == 0
        assert checks["link_tags"] == 0
        assert checks["inline_scripts"] == 1
        # embedded JSON must parse
        with open(out, "r", encoding="utf-8") as fh:
            html = fh.read()
        start = html.index("const DATA = ") + len("const DATA = ")
        end = html.index(";", start)
        parsed = json.loads(html[start:end])
        assert parsed["meta"]["title"] == "Test"

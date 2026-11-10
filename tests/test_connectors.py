"""Tests for source connectors (parse logic, no network)."""

import json

from openvitals.connectors.apple_health import parse_payload, iter_payloads_from_path
from openvitals.connectors.dexcom import DexcomConnector
from openvitals.config import SourceConfig


def test_hae_payload_parse():
    obj = {
        "metrics": [
            {"name": "step_count", "units": "count",
             "data": [{"date": "2026-07-12 07:38:33 -0700", "qty": 1234, "source": "iPhone"}]},
        ],
        "workouts": [
            {"start": "2026-07-12 07:00:00", "end": "2026-07-12 07:45:00", "duration": 2700,
             "name": "Walk", "activeEnergyBurned": {"qty": 200, "units": "kcal"},
             "distance": {"qty": 3.1, "units": "km"}, "heartRate": {"avg": 110}},
        ],
    }
    data = parse_payload(obj, source="ah")
    assert len(data.observations) == 1
    assert data.observations[0].value == 1234
    assert len(data.workouts) == 1
    assert data.workouts[0].name == "Walk"
    assert data.workouts[0].energy_kcal == 200
    assert data.workouts[0].distance_km == 3.1


def test_dexcom_csv(tmp_path):
    csv = "Timestamp,Glucose Value (mg/dL),Source\n2026-01-01T08:00:00,110,DEXCOM\n2026-01-01T08:05:00,118,DEXCOM\n"
    p = tmp_path / "dex.csv"
    p.write_text(csv, encoding="utf-8")
    conn = DexcomConnector(SourceConfig(type="dexcom", name="dex", params={"path": str(p)}))
    data = DexcomConnector.fetch(conn)
    assert len(data.glucose) == 2
    assert data.glucose[0].value == 110

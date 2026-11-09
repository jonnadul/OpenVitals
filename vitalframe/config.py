"""Configuration for VitalFrame.

A config is a plain mapping (loaded from YAML/JSON) describing:
- ``storage`` — where data lives (SQLite path)
- ``sources`` — one block per ingestion connector, keyed by type
- ``dashboard`` — which metrics/sections to show and how
- ``analysis`` — fasting window, glucose bands, insight profile

Everything is overridable; nothing in the code bakes in a specific person.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import json

try:
    import yaml  # type: ignore

    _HAVE_YAML = True
except Exception:  # pragma: no cover
    _HAVE_YAML = False


@dataclass
class SourceConfig:
    """Configuration for a single ingestion source/connector."""

    type: str  # connector key, e.g. "apple_health", "oura", "yazio", "dexcom", "synthetic"
    name: str = ""
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SourceConfig":
        return cls(
            type=d["type"],
            name=d.get("name", d["type"]),
            enabled=bool(d.get("enabled", True)),
            params=d.get("params", {}) or {},
        )


@dataclass
class StorageConfig:
    path: str = "data/vitalframe.db"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StorageConfig":
        return cls(path=d.get("path", "data/vitalframe.db"))


@dataclass
class MetricDisplay:
    """How a single metric should appear on the dashboard."""

    key: str
    label: str
    unit: str
    source_priority: List[str] = field(default_factory=list)  # preferred sources, in order
    good: Optional[str] = None  # optional reference band for color (not clinical advice)
    section: str = "metrics"


@dataclass
class DashboardConfig:
    title: str = "VitalFrame"
    windows: List[int] = field(default_factory=lambda: [7, 14, 30, 90, 365, 0])
    default_window: int = 30
    metrics: List[MetricDisplay] = field(default_factory=list)
    sections: List[str] = field(
        default_factory=lambda: [
            "recovery",
            "glucose",
            "activity",
            "nutrition",
            "fasting",
            "sleep",
            "weight",
            "logs",
        ]
    )
    weight_axis: Optional[List[float]] = None  # [min, max] fixed axis
    show_ai_summary: bool = False  # off by default; opt-in per InsightProfile

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DashboardConfig":
        metrics = [MetricDisplay(**m) for m in d.get("metrics", [])]
        return cls(
            title=d.get("title", "VitalFrame"),
            windows=d.get("windows", [7, 14, 30, 90, 365, 0]),
            default_window=d.get("default_window", 30),
            metrics=metrics,
            sections=d.get("sections", ["recovery", "glucose", "activity", "nutrition", "fasting", "sleep", "weight", "logs"]),
            weight_axis=d.get("weight_axis"),
            show_ai_summary=bool(d.get("show_ai_summary", False)),
        )


@dataclass
class AnalysisConfig:
    fast_start_hour: int = 9
    fast_end_hour: int = 17
    water_does_not_break_fast: bool = True
    glucose_hypo: float = 70.0
    glucose_target_low: float = 70.0
    glucose_target_high: float = 180.0
    insight_profile: Optional[str] = None  # name of a built-in or user InsightProfile

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AnalysisConfig":
        return cls(
            fast_start_hour=int(d.get("fast_start_hour", 9)),
            fast_end_hour=int(d.get("fast_end_hour", 17)),
            water_does_not_break_fast=bool(d.get("water_does_not_break_fast", True)),
            glucose_hypo=float(d.get("glucose_hypo", 70.0)),
            glucose_target_low=float(d.get("glucose_target_low", 70.0)),
            glucose_target_high=float(d.get("glucose_target_high", 180.0)),
            insight_profile=d.get("insight_profile"),
        )


@dataclass
class Config:
    storage: StorageConfig = field(default_factory=StorageConfig)
    sources: List[SourceConfig] = field(default_factory=list)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Config":
        return cls(
            storage=StorageConfig.from_dict(d.get("storage", {}) or {}),
            sources=[SourceConfig.from_dict(s) for s in d.get("sources", [])],
            dashboard=DashboardConfig.from_dict(d.get("dashboard", {}) or {}),
            analysis=AnalysisConfig.from_dict(d.get("analysis", {}) or {}),
            raw=d,
        )


def load_config(path: Optional[str] = None) -> Config:
    """Load a Config from a YAML/JSON file (env ``VITALFRAME_CONFIG`` overrides).

    Falls back to built-in defaults if no file is found.
    """
    env_path = os.environ.get("VITALFRAME_CONFIG")
    target = path or env_path
    if not target or not os.path.exists(target):
        return Config()
    with open(target, "r", encoding="utf-8") as fh:
        text = fh.read()
    if target.endswith((".yaml", ".yml")):
        if not _HAVE_YAML:
            raise RuntimeError("PyYAML is required to read YAML config; install with `pip install pyyaml`.")
        data = yaml.safe_load(text)
    elif target.endswith(".json"):
        data = json.loads(text)
    else:
        # best-effort: try yaml then json
        data = yaml.safe_load(text) if _HAVE_YAML else json.loads(text)
    return Config.from_dict(data or {})


def default_config_dict() -> Dict[str, Any]:
    """A representative default config (used by the sample generator + docs)."""
    return {
        "storage": {"path": "data/vitalframe.db"},
        "sources": [
            {"type": "synthetic", "name": "demo", "params": {"days": 120, "seed": 7}}
        ],
        "dashboard": {
            "title": "My Health",
            "default_window": 30,
            "metrics": [
                {"key": "resting_heart_rate", "label": "Resting HR", "unit": "bpm", "section": "recovery"},
                {"key": "heart_rate_variability", "label": "HRV", "unit": "ms", "section": "recovery"},
                {"key": "sleep_total", "label": "Sleep", "unit": "h", "section": "sleep"},
                {"key": "step_count", "label": "Steps", "unit": "steps", "section": "activity"},
                {"key": "body_mass", "label": "Weight", "unit": "kg", "section": "weight"},
                {"key": "blood_glucose", "label": "Glucose", "unit": "mg/dL", "section": "glucose"},
            ],
            "weight_axis": [60, 90],
        },
        "analysis": {
            "fast_start_hour": 9,
            "fast_end_hour": 17,
            "glucose_hypo": 70,
            "glucose_target_high": 180,
        },
    }

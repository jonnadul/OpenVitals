"""The public preview can only be built from the synthetic connector."""
from pathlib import Path
import importlib.util


def preview_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "generate_dashboard_preview.py"
    assert path.exists(), "A reproducible synthetic-only preview generator is required"
    spec = importlib.util.spec_from_file_location("preview_generator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preview_dataset_is_synthetic_and_date_anchored():
    module = preview_module()
    dataset = module.demo_dataset()
    assert dataset["meta"]["as_of"] == "2025-06-30"
    assert dataset["meta"]["sources"] == ["synthetic_demo"]
    assert dataset["meta"]["demo"] is True
    assert dataset["meta"]["title"] == "OpenVitals demo"
    assert dataset["sleep_series"] and dataset["nutrition"] and dataset["weight_series"]
    assert dataset["glucose"]["readings"]
    assert "synthetic" in dataset["meta"]["demo_notice"].lower()
    assert module.demo_dataset() == dataset


def test_landing_uses_a_real_synthetic_dashboard_capture():
    path = Path(__file__).resolve().parents[1] / "index.html"
    html = path.read_text(encoding="utf-8")
    assert 'src="assets/dashboard-preview.png"' in html
    assert 'alt="OpenVitals overall-health summary with synthetic demo data"' in html
    assert "Actual dashboard" in html
    assert "Synthetic data" in html
    assert "<!-- mock dashboard preview -->" not in html

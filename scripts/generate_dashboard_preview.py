"""Capture the real dashboard using ONLY generated synthetic data.

Run from the repo: python scripts/generate_dashboard_preview.py
Requires Playwright + Chromium. OPENVITALS_BROWSER can select an installed browser.
There is intentionally no input-data, database, or configuration argument.
"""
from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openvitals.analysis.build_dataset import build_dataset
from openvitals.config import Config, SourceConfig, default_config_dict
from openvitals.connectors.synthetic import SyntheticConnector
from openvitals.dashboard import render

END = date(2025, 6, 30)
SEED = 7
DAYS = 60


def demo_dataset():
    """Return a fixed-date demo; never inspect any personal source or file."""
    source = SourceConfig(type="synthetic", name="synthetic_demo", params={"days": DAYS, "seed": SEED})
    data = SyntheticConnector(source).fetch()
    shift = END - max(o.day for o in data.observations)
    for collection in (data.observations, data.sleep, data.glucose, data.meals,
                       data.nutrition, data.medications, data.workouts):
        for record in collection:
            for field in fields(record):
                value = getattr(record, field.name)
                if isinstance(value, (date, datetime)):
                    setattr(record, field.name, value + shift)
    for record in data.medications:
        record.name = "Example daily medication"
    assert data.sources() == {"synthetic_demo"}
    config = Config.from_dict(default_config_dict())
    config.dashboard.title = "OpenVitals demo"
    config.dashboard.default_window = 30
    dataset = build_dataset(data, config)
    dataset["meta"].update({
        "generated_at": "2025-06-30 23:59:59",
        "demo": True,
        "demo_notice": "Synthetic demo data · Not a real person",
    })
    assert dataset["meta"]["as_of"] == END.isoformat()
    return dataset


def main():
    from playwright.sync_api import sync_playwright

    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    image = assets / "dashboard-preview.png"
    with tempfile.TemporaryDirectory(prefix="openvitals-demo-", dir=os.environ.get("TMPDIR")) as temporary:
        path = Path(temporary) / "index.html"
        render(demo_dataset(), str(path))
        with sync_playwright() as p:
            options = {"headless": True}
            if os.environ.get("OPENVITALS_BROWSER"):
                options["executable_path"] = os.environ["OPENVITALS_BROWSER"]
            browser = p.chromium.launch(**options)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 1000}, device_scale_factor=1)
                errors, external = [], []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on("request", lambda r: external.append(r.url) if r.url.startswith(("http:", "https:")) else None)
                page.goto(path.as_uri())
                page.wait_for_selector("#summary-view .domain-card")
                assert page.locator("#demo-notice").is_visible()
                assert page.locator("#demo-notice").inner_text() == "Synthetic demo data · Not a real person"
                assert not errors, errors
                assert not external, external
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=str(image), full_page=True)
            finally:
                browser.close()
    manifest = {
        "synthetic_only": True,
        "generator": "scripts/generate_dashboard_preview.py",
        "source": "SyntheticConnector",
        "seed": SEED,
        "days": DAYS,
        "as_of": END.isoformat(),
        "viewport": {"width": 1280, "height": 1000},
        "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "template_sha256": hashlib.sha256((ROOT / "openvitals/dashboard/template.html").read_bytes()).hexdigest(),
    }
    (assets / "dashboard-preview.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Synthetic-only dashboard screenshot: {image}")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

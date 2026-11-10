"""Optional real-browser regressions: pip install playwright; playwright install chromium.

All fixtures are synthetic. Never point these tests at a personal data store.
Set OPENVITALS_BROWSER to a local Chromium executable when needed.
"""
import os
from datetime import date, datetime, timedelta

import pytest

from openvitals.analysis.build_dataset import build_dataset
from openvitals.config import Config
from openvitals.dashboard import render
from openvitals.models import HealthData, Observation, SleepSession

pw = pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        options = {"headless": True}
        if os.environ.get("OPENVITALS_BROWSER"):
            options["executable_path"] = os.environ["OPENVITALS_BROWSER"]
        instance = p.chromium.launch(**options)
        yield instance
        instance.close()


@pytest.fixture
def dataset():
    return {
        "meta": {"title": "Fixture health", "as_of": "2025-02-10",
                 "generated_at": "2025-02-11 08:00:00", "sources": ["fixture"],
                 "windows": [7, 14, 30, 90, 365, 0], "default_window": 30,
                 "sections": ["recovery", "glucose", "activity", "sleep", "weight", "nutrition", "fasting", "logs"],
                 "counts": {"observations": 3, "glucose": 4}},
        "metrics": [{"key": "resting_heart_rate", "label": "Resting heart rate", "unit": "bpm", "section": "recovery",
                     "latest": 60, "latest_date": "2025-02-10", "series": [["2025-02-01", 65], ["2025-02-05", 62], ["2025-02-10", 60]]}],
        "glucose": {"has_data": True, "readings": [["2025-02-01 12:00:00", 210], ["2025-02-10 12:00:00", 60], ["2025-02-10 12:05:00", 110], ["2025-02-10 13:00:00", 240]]},
        "steps_series": [], "sleep_series": [], "weight_series": [],
        "nutrition": [], "meals": [], "fasting": {"has_data": False},
        "medications": {}, "insights": [],
    }


def open_dashboard(browser, tmp_path, dataset, width=1280):
    path = str(tmp_path / "dashboard.html")
    render(dataset, path)
    page = browser.new_page(viewport={"width": width, "height": 900})
    page.goto(__import__("pathlib").Path(path).as_uri())
    return page


def test_untrusted_text_cannot_break_out_of_the_embedded_dataset(browser, tmp_path, dataset):
    attack = '</ScRiPt><img src=x onerror="window.__injected=1">'
    dataset["meta"]["sources"] = [attack]
    dataset["meals"] = [{"ts": "2025-02-10 12:00:00", "text": attack, "calories": 42}]
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        pw.expect(page.get_by_role("heading", name="Summary", exact=True)).to_be_visible()
        assert page.evaluate("window.__injected || null") is None
        page.get_by_role("button", name="Browse", exact=True).click()
        page.locator("#browse-list button", has_text="Meal log").click()
        page.locator("#detail-body summary").click()
        pw.expect(page.locator("#detail-body")).to_contain_text(attack)
        assert page.locator("img").count() == 0
    finally:
        page.close()


def test_summary_browse_and_detail_are_a_single_clear_path(browser, tmp_path, dataset):
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        pw.expect(page.get_by_role("heading", name="Summary", exact=True)).to_be_visible()
        pw.expect(page.locator("#summary-view")).to_be_visible()
        pw.expect(page.locator("#browse-view")).to_be_hidden()
        pw.expect(page.locator("#summary-view")).not_to_contain_text("No data")
        page.get_by_role("button", name="Browse", exact=True).click()
        pw.expect(page.locator("#browse-view")).to_be_visible()
        page.get_by_role("searchbox", name="Search health data").fill("heart")
        page.locator("#browse-list button", has_text="Resting heart rate").click()
        pw.expect(page.get_by_role("dialog")).to_be_visible()
        pw.expect(page.locator("#detail-title")).to_have_text("Resting heart rate")
        assert page.locator("#detail-body svg").count() == 1
        page.keyboard.press("Escape")
        pw.expect(page.get_by_role("dialog")).to_be_hidden()
    finally:
        page.close()


def test_summary_distinguishes_daily_chart_from_period_and_sample_counts(browser, tmp_path, dataset):
    dataset["steps_series"] = [["2025-02-10", 6]]
    dataset["medications"] = {"Example medication": {"taken": 1, "skipped": 0, "pending": 0, "total": 1}}
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        pw.expect(page.locator('#summary-view [data-open="steps"]')).to_contain_text("Latest sample")
        page.locator('#summary-view [data-open="glucose"]').click()
        pw.expect(page.locator("#detail-body")).to_contain_text("Daily readings")
        page.get_by_role("button", name="Done", exact=True).click()
        page.get_by_role("button", name="Browse", exact=True).click()
        pw.expect(page.locator('#browse-list [data-open="medications"]')).to_contain_text("1 medication")
    finally:
        page.close()


@pytest.mark.parametrize("key,unit,section,entry,preferred,other", [
    ("step_count", "steps", "activity", "steps", 8000, 1000),
    ("body_mass", "lb", "weight", "weight", 170, 180),
])
@pytest.mark.parametrize("configured_series", [True, False])
def test_canonical_metrics_prefer_configured_series_with_dedicated_fallback(
    browser, tmp_path, key, unit, section, entry, preferred, other, configured_series
):
    timestamp = datetime(2025, 2, 10, 12)
    data = HealthData(observations=[
        Observation(key, other, unit, timestamp, "other"),
        Observation(key, preferred, unit, timestamp, "preferred"),
    ])
    cfg = Config.from_dict({"dashboard": {"metrics": [
        {"key": key, "label": entry, "unit": unit, "section": section, "source_priority": ["preferred"]},
    ]}})
    dataset = build_dataset(data, cfg)
    assert dataset["metrics"][0]["series"] == [["2025-02-10", preferred]]
    assert dataset[f"{entry}_series"] == [["2025-02-10", other]]
    if not configured_series:
        dataset["metrics"][0]["series"] = []
    expected = preferred if configured_series else other
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        pw.expect(page.locator(f'#summary-view [data-open="{entry}"] .row-value')).to_have_text(f"{expected:,}{unit}")
        page.get_by_role("button", name="Browse", exact=True).click()
        row = page.locator(f'#browse-list [data-open="{entry}"]')
        pw.expect(row.locator(".row-value")).to_have_text(f"{expected:,}{unit}")
        row.click()
        pw.expect(page.locator("#detail-body .value")).to_have_text(f"{expected:,}{unit}")
        pw.expect(page.locator("#detail-body svg")).to_have_attribute("data-y-min", str(expected))
        page.locator("#detail-body summary").click()
        pw.expect(page.locator("#detail-body .history-row")).to_contain_text(f"{expected:,} {unit}")
    finally:
        page.close()


@pytest.mark.parametrize("unit,value", [("min", 450), ("h", 7.5)])
@pytest.mark.parametrize("with_sessions", [False, True])
def test_sleep_observations_fallback_keeps_series_and_units_paired(browser, tmp_path, unit, value, with_sessions):
    data = HealthData(observations=[
        Observation("sleep_total", value, unit, datetime(2025, 2, 10, 8), "fixture"),
    ])
    if with_sessions:
        data.sleep = [SleepSession(datetime(2025, 2, 10), datetime(2025, 2, 10, 8), 8, "fixture")]
    cfg = Config.from_dict({"dashboard": {"metrics": [
        {"key": "sleep_total", "label": "Sleep", "unit": unit, "section": "sleep"},
    ]}})
    dataset = build_dataset(data, cfg)
    expected, expected_unit = (8, "h") if with_sessions else (value, unit)
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        pw.expect(page.locator('#summary-view [data-open="sleep"] .row-value')).to_have_text(f"{expected}{expected_unit}")
        page.get_by_role("button", name="Browse", exact=True).click()
        row = page.locator('#browse-list [data-open="sleep"]')
        pw.expect(row.locator(".row-value")).to_have_text(f"{expected}{expected_unit}")
        row.click()
        pw.expect(page.locator("#detail-body .value")).to_have_text(f"{expected}{expected_unit}")
        pw.expect(page.locator("#detail-body svg")).to_have_attribute("data-y-min", str(expected))
        if not with_sessions:
            pw.expect(page.locator("#detail-body")).not_to_contain_text("Longest recorded sleep session")
        page.locator("#detail-body summary").click()
        pw.expect(page.locator("#detail-body .history-row")).to_contain_text(f"{expected} {expected_unit}")
    finally:
        page.close()


@pytest.mark.parametrize("configured_unit", [None, "", "lb"])
def test_weight_never_invents_a_unit_when_configuration_has_none(browser, tmp_path, configured_unit):
    data = HealthData(observations=[
        Observation("body_mass", 170, "lb", datetime(2025, 2, 10, 8), "fixture"),
    ])
    metrics = [] if configured_unit is None else [
        {"key": "body_mass", "label": "Weight", "unit": configured_unit, "section": "weight"},
    ]
    dataset = build_dataset(data, Config.from_dict({"dashboard": {"metrics": metrics}}))
    unit = configured_unit or ""
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        pw.expect(page.locator('#summary-view [data-open="weight"] .row-value')).to_have_text(f"170{unit}")
        page.get_by_role("button", name="Browse", exact=True).click()
        row = page.locator('#browse-list [data-open="weight"]')
        pw.expect(row.locator(".row-value")).to_have_text(f"170{unit}")
        row.click()
        pw.expect(page.locator("#detail-body .value")).to_have_text(f"170{unit}")
        page.locator("#detail-body summary").click()
        pw.expect(page.locator("#detail-body .history-row > span")).to_have_text(f"170 {unit}".strip())
    finally:
        page.close()


def test_configured_weight_axis_clips_out_of_range_points(browser, tmp_path, dataset):
    dataset["meta"]["weight_axis"] = [60, 90]
    dataset["weight_series"] = [["2025-02-05", 50], ["2025-02-10", 75]]
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        page.get_by_role("button", name="Browse", exact=True).click()
        page.locator('#browse-list [data-open="weight"]').click()
        svg = page.locator('#detail-body svg')
        assert svg.get_attribute('data-y-min') == '60'
        assert svg.get_attribute('data-y-max') == '90'
        assert svg.locator('g[clip-path]').count() == 1
    finally:
        page.close()


def test_glucose_detail_uses_daily_averages_not_a_collapsed_raw_line(browser, tmp_path, dataset):
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        page.locator('#summary-view [data-open="glucose"]').click()
        page.locator("#detail-body summary", has_text="Period trend").click()
        pw.expect(page.locator("#detail-body")).to_contain_text("Daily average")
        pw.expect(page.locator("#detail-body")).to_contain_text("4 readings across 2 recorded days")
        assert page.locator("#detail-body svg").count() == 2
    finally:
        page.close()


@pytest.mark.parametrize("width", [320, 390, 768, 1280])
def test_responsive_navigation_has_no_overflow_or_script_errors(browser, tmp_path, dataset, width):
    path = str(tmp_path / "responsive.html")
    render(dataset, path)
    page = browser.new_page(viewport={"width": width, "height": 900})
    errors, network = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: network.append(r.url) if r.url.startswith(("http:", "https:")) else None)
    try:
        page.goto(__import__("pathlib").Path(path).as_uri())
        for view in ("Summary", "Browse"):
            page.get_by_role("button", name=view, exact=True).click()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert "NaN" not in page.locator("body").inner_text()
        page.locator("#browse-list button", has_text="Resting heart rate").click()
        assert page.locator("dialog").evaluate("e => e.scrollWidth <= e.clientWidth")
        page.get_by_role("button", name="Done", exact=True).click()
        assert not errors, errors
        assert not network, network
    finally:
        page.close()


def test_empty_snapshot_has_no_phantom_metrics(browser, tmp_path, dataset):
    dataset["metrics"] = []
    dataset["glucose"] = {"has_data": False, "readings": []}
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        pw.expect(page.locator("#summary-view")).to_contain_text("Your summary starts here")
        assert page.locator("#summary-view .metric-row").count() == 0
    finally:
        page.close()


@pytest.mark.parametrize("entry", ["resting_heart_rate", "meals"])
def test_all_dates_ignores_stale_anchor_but_finite_windows_keep_exact_days(browser, tmp_path, dataset, entry):
    days = [(date(2025, 2, 1) + timedelta(days=i)).isoformat() for i in range(11)]
    dataset["metrics"][0]["series"] = [[day, 60] for day in days] + [["invalid-date", 99]]
    dataset["meals"] = [{"ts": day + " 12:00:00", "text": "Synthetic meal " + day} for day in days]
    dataset["meals"].append({"ts": "invalid-date", "text": "Invalid date meal"})
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        page.get_by_role("button", name="All dates", exact=True).click()
        page.get_by_role("button", name="Browse", exact=True).click()
        page.locator(f'#browse-list [data-open="{entry}"]').click()
        assert page.locator("#detail-body .history-row").count() == len(days)
        pw.expect(page.locator("#detail-body")).not_to_contain_text("Unknown date")
        pw.expect(page.locator("#detail-body")).not_to_contain_text("Invalid date meal")
        page.get_by_role("button", name="Done", exact=True).click()
        page.get_by_role("button", name="7 days", exact=True).click()
        page.locator(f'#browse-list [data-open="{entry}"]').click()
        page.locator("#detail-body summary").click()
        rows = page.locator("#detail-body .history-row")
        assert rows.count() == 7
        pw.expect(rows.first).to_contain_text("2025-02-10" if entry == "meals" else "Feb 10, 2025")
        pw.expect(rows.last).to_contain_text("2025-02-04" if entry == "meals" else "Feb 4, 2025")
    finally:
        page.close()


def test_glucose_period_updates_statistics_and_keeps_gaps_and_lows(browser, tmp_path, dataset):
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        page.locator('#summary-view [data-open="glucose"]').click()
        pw.expect(page.locator("#glucose-mean")).to_have_text("155")
        pw.expect(page.locator("#glucose-count")).to_contain_text("4 readings")
        page.locator("#detail").get_by_role("button", name="7 days", exact=True).click()
        pw.expect(page.locator("#glucose-mean")).to_have_text("136.7")
        pw.expect(page.locator("#glucose-count")).to_contain_text("3 readings")
        pw.expect(page.locator("#glucose-low-note")).to_contain_text("1 recorded reading below 70")
        assert page.locator("#glucose-day option").count() == 1
        svg = page.locator("#glucose-day-chart svg")
        assert float(svg.get_attribute("data-y-min")) <= 60
        assert float(svg.get_attribute("data-y-max")) >= 240
        # A 55-minute missing stretch is not drawn as a continuous line.
        assert svg.locator("path.sensor-line").get_attribute("d").count("M") == 2
        page.locator("#detail").get_by_role("button", name="All dates", exact=True).click()
        assert page.locator("#glucose-day option").count() == 2
        page.locator("#glucose-day").select_option("2025-02-01")
        pw.expect(page.locator("#glucose-day-note")).to_contain_text("1 reading")
        page.reload()
        pw.expect(page.get_by_role("button", name="All dates", exact=True)).to_have_attribute("aria-pressed", "true")
    finally:
        page.close()

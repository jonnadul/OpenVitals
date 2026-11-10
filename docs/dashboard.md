# Dashboard

The dashboard is a **single, self-contained HTML file** with inline data, CSS, and
JavaScript. There are no fonts, scripts, stylesheets, analytics, or API requests
loaded from another server. Open it from disk or serve it locally.

## Summary first, details on demand

The light, grouped layout takes inspiration from Apple Health without copying
Apple branding or assets:

- **Summary:** equal-weight Sleep, Movement, Recovery, Nutrition, Body, and
  Metabolic health cards when those domains have recorded data. Glucose is one
  peer measurement, not a hero panel. Missing domains are named in a coverage note.
- **Context:** neutral latest-seven-day versus prior-seven-day comparisons, with
  observed-day counts, describe changes rather than diagnosing improvement.
  No biological-age or longevity score is inferred from wearable data.
- **Browse:** searchable categories containing every available configured metric,
  nutrition entries, eating-window logs, meal logs, and medication summaries.
- **Details:** click a measurement for a chart and an expandable recorded-entry
  list. A native dialog supports keyboard focus, Escape, and a Done button.
- **Mobile navigation:** Summary and Browse stay reachable at the bottom. The
  desktop layout presents equal-size domain cards in a compact grid.
- **About this data:** source names, snapshot/build dates, privacy notes, and any
  full-snapshot analysis notes stay collapsed by default.

## Periods and dates

`dashboard.windows` and `dashboard.default_window` configure the period control.
The selection persists under `ov.period` in browser local storage. A seven-day
window includes the snapshot's last day and the preceding six calendar days.
Finite windows exclude dates after the snapshot anchor. **All** retains every
valid recorded date, including newer meal logs in older exported datasets.
The dataset builder includes meal dates in its anchor. Missing values are never
replaced by a stale value from outside the selected window.

The dataset's `meta.as_of` anchors the range; the browser's current date does not.
The header explicitly identifies the page as an **imported snapshot, not live**.
Each measurement shows its own recorded date. Changing a period updates charts,
measurements, glucose statistics, and dated nutrition/meal/fasting lists.
Medication summaries have no dated dose records in the current dataset, so they
are explicitly labeled **all loaded dates** and are not period-filtered. Analysis
notes are likewise labeled full-snapshot.

## Glucose

- The metabolic-health summary card shows the average of recorded readings.
- Open its detail view for the **Daily readings** chart, which defaults to the most recent
  recorded day in that period. A date selector and previous/next buttons inspect
  other recorded days.
- Chart positions use recorded clock time across a full day, not reading index.
  The y-axis includes recorded lows and highs plus the configured target band.
  Gaps longer than 15 minutes are not connected. Isolated readings remain visible.
- Percentages describe **readings**, not time-weighted coverage or a clinical
  estimate. Recorded lows receive an explicit historical-data notice.
- The detail view shows daily averages and counts/ranges; its copy warns that
  daily averages hide short excursions. The estimated A1c is not promoted in the UI.
- Thresholds are supplied by `analysis.glucose_hypo`, `glucose_target_low`, and
  `glucose_target_high` through dataset metadata.

## Interpretation limits

Steps currently come from the backend's latest stored step sample per day, not
necessarily a complete daily total. Both the summary and detail disclose this.
The UI does not sum overlapping device samples or silently change aggregation.
Medication states distinguish taken, skipped, and unconfirmed; unconfirmed is not
proof of a missed dose. Eating-window percentages describe logged meals, not
verified fasting duration or unlogged intake. Metric changes are not automatically
colored as good or bad. Fixed weight axes use plot clipping.

Configured non-empty step and weight series take precedence over generic series,
so source selections are preserved. Configured sleep observations remain visible
when session-derived sleep is absent. Units stay paired with the selected series;
weight with no known unit is displayed without an invented kilogram label.

## Privacy and rendering

`openvitals.dashboard.render(dataset, out_path)` atomically replaces the rendered
file. The embedded JSON escapes `<`, `>`, `&`, and Unicode line separators, including
mixed-case script-closing text. Displayed free text is HTML-escaped.

The HTML **contains health data**, even though it performs no external requests.
Anyone who can access the file or its hosting URL can read that data. Local/LAN
hosting alone is not authentication. Keep personal outputs, stores, configurations,
and screenshots outside a public repository. Never publish real-data HTML to
GitHub Pages; the project's landing page is a separate file.

## Verification

Core tests:

```bash
python -m pytest tests -q
```

Browser tests are optional but required when changing the UI:

```bash
python -m pip install pytest playwright
python -m playwright install chromium
python -m pytest tests/test_dashboard_ui.py -q
```

Set `OPENVITALS_BROWSER` to an installed Chromium executable if necessary. Browser
fixtures use synthetic data and cover navigation/search/dialogs, empty snapshots,
period filtering, glucose gaps/lows, fixed weight axes, script-injection handling,
offline behavior, and 320/390/768/1280-pixel layouts.

## Public landing-page screenshot

`python scripts/generate_dashboard_preview.py` captures this exact renderer using
only `SyntheticConnector`, a fixed seed, and a fixed demo date. It has no personal
input-file/configuration argument. The image visibly says synthetic data and is
written to `assets/dashboard-preview.png` with a provenance/hash manifest. The
landing page uses this relative asset path so GitHub Pages project subpaths work.
Real-data screenshots are never used as public assets.

## Serving

Open the file directly, or use:

```bash
openvitals serve --config config.yaml --port 8899
```

`serve` builds once and rebuilds on a timer (default 300 seconds). For a UI-only
change, re-render an existing dataset instead of re-running connector ingestion.

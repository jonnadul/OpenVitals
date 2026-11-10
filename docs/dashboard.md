# Dashboard

The dashboard is a **single, self-contained HTML file** — no server, no CDN, no
external requests. `openvitals.dashboard.render(dataset, out_path)` embeds the full
dataset as inline JSON and renders it with vanilla JS.

## What's on the page

- **Metric cards** — latest value + unit, trend arrow, as-of date. Configured via
  `dashboard.metrics`.
- **Window selector** — 7/14/30/90/365/All days. Choice persists in `localStorage`;
  trends and series recompute client-side.
- **Section tabs** (configurable): Recovery, Glucose, Activity, Nutrition, Fasting,
  Sleep, Weight, Logs, Insights.
- **Glucose** — mean, time-in-range %, estimated A1c, and a line chart with the
  70–180 mg/dL target band.
- **Fasting** — window adherence %, in-window vs slips, and a recent-meals table.
- **Insights** — leveled guidance from the configured InsightProfile.

## Theme

Apple Health-inspired light theme: grouped-gray background (`#f2f2f7`), white cards,
system gray text, semantic green/amber/red. Charts are inline SVG with hardcoded
hex colors (no CSS-variable dependency). It is responsive — metric cards go 2-up and
wide tables scroll sideways on phones.

## Privacy

The page embeds your health data inline, so it should be treated like the data itself:
don't post it publicly. `verify_self_contained()` checks the file for any
`http(s)://`, `<script src>`, or `<link>` — all must be zero. User-entered meal text is
HTML-escaped, and the embedded JSON is scanned for a literal `</script>` (which would
prematurely close the tag); if found, the data is JSON-stringified and `JSON.parse`d
instead.

## Serving

Open the file directly, or serve it with any static host. For live refresh:

```bash
openvitals serve --config config.yaml --port 8899
```

`serve` builds the page once, serves it, and rebuilds on a timer (default 300s) so it
stays fresh without rebuilding per request.

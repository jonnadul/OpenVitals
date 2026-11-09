# Architecture

VitalFrame is a pipeline with four stages. Each stage has a clean contract so you
can replace any part without touching the others.

## 1. Ingestion — Connectors

A connector implements one method, `fetch() -> HealthData`, and is selected by
`type` in the config:

```python
from vitalframe.connectors import SourceConnector
from vitalframe.models import HealthData

class MyConnector(SourceConnector):
    type_key = "my_source"
    def fetch(self) -> HealthData:
        data = HealthData()
        # ... read your source, append normalized records ...
        return data
```

`vitalframe.pipeline.ingest(config)` runs every enabled source, isolates failures
(one bad source never blocks the others), and writes the merged `HealthData` to
the store.

## 2. Storage — SQLite store

`vitalframe.storage.Store` persists the normalized model into typed tables:

- `observations` — scalar metrics (`metric`, `value`, `unit`, `timestamp`, `source`, `day`)
- `workouts`, `sleep`, `meals`, `glucose`, `nutrition`, `medications`

Records are keyed so re-ingesting is idempotent (latest value wins per key).
`store.load(since, until)` returns an in-memory `HealthData` for analysis.

The store deliberately avoids an ORM and WAL-only writes, so it is safe to back up
with SQLite's online `backup()` API and portable across machines.

## 3. Analysis

`vitalframe.analysis.build_dataset(data, config)` is the single contract the
dashboard consumes. It returns a plain `dict` with:

- `meta` — title, as-of date, sources, window options, record counts
- `metrics` — per configured metric: latest value, as-of date, trend slope, full daily series
- `sleep_series`, `steps_series`, `weight_series` — daily series
- `glucose` — summary stats + every reading (for the chart)
- `meals`, `fasting`, `medications`, `nutrition` — domain outputs
- `insights` — produced by the configured InsightProfile
- `correlations` — headline correlations with n and p-value

The dashboard embeds the **full** series and applies the window selector
client-side, so the page stays self-contained.

### Insight profiles

An `InsightProfile.build(data, dataset, cfg) -> List[Insight]` turns analyzed data
into short, leveled insights (good/info/warn/alert) with optional citations. The
bundled `DiabetesLongevityProfile` is a **reference example** — evidence-flavored
but fully configurable and explicitly not medical advice. Supply your own class via
`analysis.insight_profile` in config.

## 4. Rendering — Dashboard

`vitalframe.dashboard.render(dataset, out_path)` writes one HTML file. The dataset
JSON is embedded inline; the page is rendered by vanilla JS with no external
requests. `verify_self_contained()` asserts zero `http(s)` links, `<script src>`,
or `<link>` tags — a guard against accidental leaks.

## Data flow at a glance

```
config.yaml
   │  pipeline.ingest
   ▼
[connectors] ──► HealthData ──► Store (SQLite)
                              │  Store.load
                              ▼
                         HealthData
                              │  build_dataset
                              ▼
                         dataset dict
                              │  render
                              ▼
                   dashboard.html (offline)
```

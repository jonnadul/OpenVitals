# OpenVitals

**A self-hosted, open-source personal health-data framework.**

Ingest health data from *any* source, store it locally in a private SQLite store,
analyze it (trends, correlations, glucose, fasting, medications), and render a
**fully offline, self-contained dashboard** — no cloud, no CDN, no tracking.

> ⚠️ OpenVitals is a data tool, not a medical device. Insights are heuristic and
> not medical advice. Nothing here diagnoses or treats any condition.

---

## Why

Most health dashboards lock your data in a vendor's cloud or only show one
device's view. OpenVitals is:

- **Local-first** — your data lives in a SQLite file you control.
- **Source-agnostic** — a small connector interface normalizes any source
  (Apple Health, Oura, Yazio, Dexcom, or your own) into one model.
- **Private by design** — the dashboard is a single HTML file with zero external
  requests; it works from disk or any static host.
- **Configurable, not hard-coded** — what metrics show, the fasting window, glucose
  bands, and the insight profile all come from config.

## Quick start (60 seconds, no private data)

```bash
pip install -e .
openvitals sample --output config.yaml      # writes a sample config (uses demo data)
openvitals build --config config.yaml --output dashboard.html
# open dashboard.html in a browser
```

Or run it live with auto-refresh:

```bash
openvitals serve --config config.yaml --port 8899
# open http://localhost:8899/
```

The sample config uses the **synthetic** connector, which generates deterministic
demo data so you can see the whole pipeline immediately. Swap in real sources by
editing `config.yaml` (see [docs/configuration.md](docs/configuration.md)).

## Architecture

```
 source connectors ──┐
 (apple_health,     │
  oura, yazio,      ├──► HealthData (normalized model) ──► SQLite store
  dexcom,           │                                        │
  synthetic) ───────┘                                        │
                                                            ▼
                                              analysis  (trends, correlation,
                                              fasting, glucose, medications,
                                              insight profiles)
                                                            │
                                                            ▼
                                              build_dataset()  ──►  render()
                                                            │           (self-contained HTML)
                                                            ▼
                                                  dashboard.html
```

- **Connectors** (`openvitals/connectors/`) — each turns one external source into
  the shared `HealthData` model. Add your own by subclassing `SourceConnector`.
- **Storage** (`openvitals/storage/`) — a dependency-free SQLite store keyed by
  entity kind (observations, workouts, sleep, meals, glucose, nutrition, meds).
- **Analysis** (`openvitals/analysis/`) — pure-Python stats (no SciPy needed) plus
  domain modules (glucose, fasting, medications) and a pluggable **insight profile**.
- **Dashboard** (`openvitals/dashboard/`) — renders `build_dataset()` output into a
  single offline HTML file (Apple Health-inspired light theme).

See [docs/architecture.md](docs/architecture.md) for details.

## Connectors

| Connector | Source | Auth |
|---|---|---|
| `synthetic` | demo data generator (no network) | none |
| `apple_health` | Health Auto Export JSON/JSONL pushes | none (file) |
| `oura` | Oura v2 REST API | personal access token |
| `yazio` | Yazio REST (reference client) | email/password |
| `dexcom` | Dexcom / CGM export (CSV or JSON) | none (file) |

Authoring a new connector is ~30 lines — see
[docs/connectors.md](docs/connectors.md).

## Configuration

Everything is config-driven. A minimal config:

```yaml
storage:
  path: data/openvitals.db
sources:
  - type: apple_health
    params:
      path: data/snapshots/health.jsonl
  - type: oura
    params:
      token: "${OURA_TOKEN}"
dashboard:
  title: "My Health"
  metrics:
    - key: resting_heart_rate
      label: Resting HR
      unit: bpm
analysis:
  fast_start_hour: 9
  fast_end_hour: 17
  insight_profile: diabetes_longevity
```

Full schema in [docs/configuration.md](docs/configuration.md).

## Self-hosting

```bash
docker compose up --build
# dashboard at http://localhost:8899/
```

See [docs/self_hosting.md](docs/self_hosting.md).

## Development

```bash
pip install -e ".[dev]"
pytest tests -q
```

## Disclaimer

OpenVitals is provided for personal health-data exploration. It is not a medical
device and does not provide medical advice, diagnosis, or treatment. Consult a
qualified clinician for health decisions.

## License

[MIT](LICENSE)

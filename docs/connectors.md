# Connectors

A connector is anything that produces a `HealthData` from an external source. This
page covers the built-ins and how to write your own.

## Built-in connectors

### `synthetic`
Deterministic demo data (no network, no private data). Params: `days`, `seed`.

### `apple_health`
Parses **Health Auto Export** (iOS) JSON/JSONL pushes. Point `params.path` at a
single `.json`/`.jsonl` file or a directory of them. Tolerant of single objects,
JSON arrays, and line-delimited JSONL. Maps `metrics[].data[]` → observations and
`workouts[]` → workouts.

### `oura`
Oura v2 REST API. Params: `token` (or `OURA_TOKEN` env), `last_n_days`. Fetches
sleep, daily readiness, and daily activity; maps to observations + sleep sessions.
Errors on any endpoint are captured into `meta` rather than aborting the build.

### `yazio`
Yazio REST reference client. Params: `email`/`password` (or env vars), `last_n_days`.
Authenticates, then reads daily nutrition summaries + consumed items. Read-only.

### `dexcom`
Reads a CGM export file (CSV or JSON). For most users, Dexcom G7 → Apple Health → the
`apple_health` connector's `blood_glucose` metric is the simpler path; this connector
exists for direct Dexcom exports / the Dexcom API export.

## Writing a new connector

Subclass `SourceConnector`, set `type_key`, implement `fetch()`, and register it.

```python
# vitalframe/connectors/myfitbit.py
from vitalframe.connectors import SourceConnector, register_connector
from vitalframe.models import HealthData, Observation
from vitalframe.types import day_of

class MyFitbitConnector(SourceConnector):
    type_key = "myfitbit"

    def fetch(self) -> HealthData:
        data = HealthData()
        # pull from the Fitbit API, then:
        data.observations.append(Observation(
            metric="resting_heart_rate", value=58.0, unit="bpm",
            timestamp=..., source=self.name,
        ))
        return data

register = MyFitbitConnector.register
```

Then reference it in config:

```yaml
sources:
  - type: myfitbit
    params: { token: "${FITBIT_TOKEN}" }
```

Connectors are auto-discovered by importing their module; `vitalframe.connectors`
imports all built-ins on startup. A custom connector in your own package just needs
to be imported once (e.g. in your entrypoint) so `register` runs.

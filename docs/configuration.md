# Configuration

OpenVitals is configured with a single YAML (or JSON) file. Loaded via
`openvitals sample` (writes a starting point) or `VITALFRAME_CONFIG=/path/config.yaml`.

Top-level keys: `storage`, `sources`, `dashboard`, `analysis`.

## `storage`

```yaml
storage:
  path: data/openvitals.db   # any path; created on first ingest
```

## `sources`

A list of connector blocks. Each has `type`, optional `name`, `enabled`, and `params`.

```yaml
sources:
  - type: synthetic            # demo data, no network
    params: { days: 120, seed: 7 }

  - type: apple_health
    params:
      path: data/snapshots/health.jsonl   # HAE REST push file

  - type: oura
    params:
      token: "${OURA_TOKEN}"     # or set OURA_TOKEN env var
      last_n_days: 120

  - type: yazio
    params:
      email: "${YAZIO_EMAIL}"
      password: "${YAZIO_PASSWORD}"
      last_n_days: 30

  - type: dexcom
    params:
      path: data/dexcom_export.csv
```

Secrets belong in environment variables (`${VAR}` is expanded) — never commit them.
See each connector's module for its exact `params`.

## `dashboard`

```yaml
dashboard:
  title: "My Health"
  windows: [7, 14, 30, 90, 365, 0]   # 0 = all
  default_window: 30
  weight_axis: [60, 90]               # fixed weight-chart axis (optional)
  show_ai_summary: false              # opt-in; insight profiles are separate
  metrics:
    - key: resting_heart_rate
      label: Resting HR
      unit: bpm
      section: recovery                # recovery|glucose|activity|nutrition|fasting|sleep|weight|logs
    - key: blood_glucose
      label: Glucose
      unit: mg/dL
      section: glucose
  sections: [recovery, glucose, activity, nutrition, fasting, sleep, weight, logs, insights]
```

`metrics[].key` must match a metric name produced by your connectors. Common Apple
Health / Oura keys: `step_count`, `resting_heart_rate`, `heart_rate_variability`,
`body_mass`, `blood_glucose`, `sleep_total`. `source_priority` (list of source
names) is optional and resolves conflicts when two sources report the same metric.

## `analysis`

```yaml
analysis:
  fast_start_hour: 9        # fasting window (local clock)
  fast_end_hour: 17
  water_does_not_break_fast: true
  glucose_hypo: 70           # mg/dL hypoglycemia threshold
  glucose_target_low: 70
  glucose_target_high: 180    # mg/dL post-meal/elevated threshold
  insight_profile: diabetes_longevity   # name of a registered InsightProfile
```

The `diabetes_longevity` profile is a bundled reference example. Set
`insight_profile: null` to disable insights.

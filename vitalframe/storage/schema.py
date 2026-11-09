"""SQLite schema for VitalFrame's local store."""

from __future__ import annotations

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS observations (
    metric   TEXT NOT NULL,
    value    REAL NOT NULL,
    unit     TEXT,
    timestamp TEXT NOT NULL,
    source   TEXT NOT NULL,
    day      TEXT NOT NULL,
    PRIMARY KEY (metric, timestamp, source)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS workouts (
    start      TEXT NOT NULL,
    end        TEXT NOT NULL,
    duration_s REAL,
    name       TEXT,
    energy_kcal REAL,
    distance_km REAL,
    hr_avg     REAL,
    source     TEXT
);

CREATE TABLE IF NOT EXISTS medications (
    name          TEXT NOT NULL,
    scheduled_day TEXT NOT NULL,
    status        TEXT,
    taken_at      TEXT,
    source        TEXT,
    PRIMARY KEY (name, scheduled_day)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS sleep (
    start         TEXT NOT NULL,
    end           TEXT NOT NULL,
    total_sleep_h REAL,
    rem_h         REAL,
    deep_h        REAL,
    core_h        REAL,
    source        TEXT,
    PRIMARY KEY (start, source)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS meals (
    timestamp TEXT NOT NULL,
    text      TEXT,
    calories  REAL,
    items_json TEXT,
    source    TEXT,
    day       TEXT
);

CREATE TABLE IF NOT EXISTS glucose (
    timestamp TEXT NOT NULL,
    value     REAL NOT NULL,
    source    TEXT NOT NULL,
    day       TEXT NOT NULL,
    PRIMARY KEY (timestamp, source)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS nutrition (
    day       TEXT NOT NULL,
    calories  REAL,
    protein_g REAL,
    carbs_g   REAL,
    fat_g     REAL,
    fiber_g   REAL,
    water_ml  REAL,
    source    TEXT,
    PRIMARY KEY (day, source)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

# Indexes for common queries
INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_obs_day      ON observations(day);
CREATE INDEX IF NOT EXISTS idx_obs_metric   ON observations(metric);
CREATE INDEX IF NOT EXISTS idx_glucose_day  ON glucose(day);
CREATE INDEX IF NOT EXISTS idx_meal_day     ON meals(day);
CREATE INDEX IF NOT EXISTS idx_sleep_end    ON sleep(end);
CREATE INDEX IF NOT EXISTS idx_workout_start ON workouts(start);
"""

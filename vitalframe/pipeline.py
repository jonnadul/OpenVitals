"""Pipeline orchestration: ingest sources -> store -> build dataset -> render.

This is the reusable core behind the CLI and the live server. It is deliberately
side-effect-light: ``run_pipeline`` returns the dataset dict; callers decide
whether to write the HTML (``render``) or serve it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from .config import Config
from .connectors import get_connector
from .analysis.build_dataset import build_dataset
from .models import HealthData
from .storage import Store


def ingest(config: Config, store: Optional[Store] = None) -> HealthData:
    """Fetch every enabled source and merge into one HealthData (optionally storing)."""
    merged = HealthData()
    used_store = store
    own = False
    if used_store is None:
        used_store = Store(config.storage.path)
        own = True
    try:
        for src in config.sources:
            if not src.enabled:
                continue
            try:
                conn = get_connector(src)
                conn.connect()
                data = conn.fetch()
                merged += data
                used_store.ingest(data)
                conn.close()
            except Exception as e:  # isolate a failing source from the others
                merged.meta.setdefault("source_errors", {})[src.name or src.type] = str(e)
    finally:
        if own:
            used_store.close()
    return merged


def run_pipeline(config: Config, use_store: bool = True) -> Dict:
    """Full pipeline. Returns the dashboard dataset dict."""
    if use_store:
        store = Store(config.storage.path)
        try:
            data = ingest(config, store=store)
        finally:
            store.close()
        # reload so analysis sees everything persisted (covers multi-run accumulation)
        store2 = Store(config.storage.path)
        try:
            data = store2.load()
        finally:
            store2.close()
    else:
        data = ingest(config, store=None)
    return build_dataset(data, config)


def render_to(config: Config, out_path: str, use_store: bool = True) -> str:
    from .dashboard import render
    dataset = run_pipeline(config, use_store=use_store)
    return render(dataset, out_path)

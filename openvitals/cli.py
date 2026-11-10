"""Command-line interface for OpenVitals."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .config import Config, default_config_dict, load_config
from .pipeline import ingest, render_to, run_pipeline
from .storage import Store


def cmd_sample(args) -> int:
    out = args.output
    with open(out, "w", encoding="utf-8") as fh:
        import yaml  # sample command needs yaml to emit a clean file
        yaml.safe_dump(default_config_dict(), fh, sort_keys=False)
    print(f"Wrote sample config to {out}")
    return 0


def cmd_ingest(args) -> int:
    cfg = load_config(args.config)
    data = ingest(cfg)
    errs = data.meta.get("source_errors")
    print(f"Ingested: " + ", ".join(f"{k}={len(v)}" for k, v in _counts(data).items()))
    if errs:
        for name, e in errs.items():
            print(f"  ! source '{name}' error: {e}", file=sys.stderr)
    print(f"Stored at {cfg.storage.path}")
    return 0


def cmd_build(args) -> int:
    cfg = load_config(args.config)
    out = render_to(cfg, args.output)
    print(f"Dashboard written to {out}")
    return 0


def cmd_analyze(args) -> int:
    cfg = load_config(args.config)
    store = Store(cfg.storage.path)
    try:
        data = store.load()
    finally:
        store.close()
    from .analysis.build_dataset import build_dataset
    ds = build_dataset(data, cfg)
    print(json.dumps(ds.get("glucose", {}), indent=2, default=str))
    print("\nFasting:", json.dumps(ds.get("fasting", {}), indent=2, default=str)[:800])
    print("\nMedications:", json.dumps(ds.get("medications", {}), indent=2, default=str)[:800])
    print("\nInsights:")
    for i in ds.get("insights", []):
        print(f"  [{i['level']}] {i['text']}" + (f" ({i['cite']})" if i.get("cite") else ""))
    return 0


def cmd_serve(args) -> int:
    from . import serve as serve_mod
    cfg_path = args.config
    if not cfg_path:
        cfg_path = "config.yaml" if os.path.exists("config.yaml") else None
    serve_mod.serve(cfg_path, host=args.host, port=args.port, rebuild_seconds=args.rebuild)
    return 0


def _counts(data) -> dict:
    return {
        "observations": len(data.observations),
        "workouts": len(data.workouts),
        "medications": len(data.medications),
        "sleep": len(data.sleep),
        "meals": len(data.meals),
        "glucose": len(data.glucose),
        "nutrition": len(data.nutrition),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="openvitals", description="Self-hosted personal health-data framework.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sample", help="Write a sample config file.")
    s.add_argument("--output", default="config.yaml")
    s.set_defaults(func=cmd_sample)

    s = sub.add_parser("ingest", help="Run all enabled sources and store locally.")
    s.add_argument("--config", default=None)
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("build", help="Build the offline dashboard HTML.")
    s.add_argument("--config", default=None)
    s.add_argument("--output", default="data/openvitals_dashboard.html")
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("analyze", help="Print a text analysis summary.")
    s.add_argument("--config", default=None)
    s.set_defaults(func=cmd_analyze)

    s = sub.add_parser("serve", help="Serve the dashboard over HTTP.")
    s.add_argument("--config", default=None)
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8899)
    s.add_argument("--rebuild", type=int, default=300)
    s.set_defaults(func=cmd_serve)
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

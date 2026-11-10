"""Minimal local dashboard server.

Serves the rendered, self-contained dashboard HTML. On startup it builds the
page from the local store; a background thread rebuilds it when any source file
changes (or on a timer), so the page stays fresh without rebuilding per request.

Run: ``openvitals serve --config config.yaml --port 8899``
"""

from __future__ import annotations

import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .config import Config, load_config
from .dashboard import render
from .pipeline import run_pipeline


def _build_once(config: Config, out_path: str) -> None:
    try:
        dataset = run_pipeline(config, use_store=True)
        render(dataset, out_path)
    except Exception as e:  # noqa: BLE001
        with open(out_path + ".error", "w", encoding="utf-8") as fh:
            fh.write(f"build failed: {e}")


def serve(config_path: str, host: str = "0.0.0.0", port: int = 8899,
          rebuild_seconds: int = 300, build_dir: str = "data") -> None:
    os.makedirs(build_dir, exist_ok=True)
    out_path = os.path.join(build_dir, "openvitals_dashboard.html")
    cfg = load_config(config_path)

    # initial build (offline-safe: if network sources fail, synthetic/local still render)
    _build_once(cfg, out_path)

    stop = threading.Event()

    def watcher():
        while not stop.is_set():
            if stop.wait(rebuild_seconds):
                break
            _build_once(cfg, out_path)

    t = threading.Thread(target=watcher, daemon=True)
    t.start()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            p = urlparse(self.path).path
            if p in ("/", "/index.html", "/dashboard"):
                if os.path.exists(out_path):
                    self._send_file(out_path, "text/html")
                else:
                    self._send(503, "text/plain", "dashboard not built yet")
            elif p == "/refresh":
                _build_once(cfg, out_path)
                self._send(200, "text/plain", "rebuilt")
            elif p == "/healthz":
                self._send(200, "application/json", '{"status":"ok"}')
            else:
                self._send(404, "text/plain", "not found")

        def _send_file(self, path, ctype):
            with open(path, "rb") as fh:
                body = fh.read()
            self._send(200, ctype, body, binary=True)

        def _send(self, code, ctype, body, binary=False):
            data = body if binary else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):  # silence default logging
            pass

    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"OpenVitals dashboard serving at http://{host}:{port}/  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        httpd.server_close()

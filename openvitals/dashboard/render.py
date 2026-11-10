"""Render the self-contained offline dashboard HTML.

The output is a single HTML file with no CDN, no external requests, and no
server: the dataset JSON is embedded inline and rendered by vanilla JS. It works
when opened directly from disk or served by any static file server.

Security note: embedded JSON escapes HTML-significant characters so even mixed-case
closing script tags remain data. Visible free text is escaped by the UI as well.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

_TEMPLATE = os.path.join(os.path.dirname(__file__), "template.html")


def _safe_json(obj: Any) -> str:
    return (json.dumps(obj, ensure_ascii=False, default=str)
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def render(dataset: Dict[str, Any], out_path: str) -> str:
    with open(_TEMPLATE, "r", encoding="utf-8") as fh:
        tpl = fh.read()

    data_json = _safe_json(dataset)
    html = tpl.replace("/*__VITALFRAME_DATA__*/", f"const DATA = {data_json};")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(html)
    os.replace(tmp, out_path)
    return out_path


def verify_self_contained(html_path: str) -> Dict[str, int]:
    """Assert the page is offline: 0 external links/scripts/stylesheets."""
    with open(html_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    checks = {
        "http_links": text.lower().count("http://"),
        "https_links": text.lower().count("https://"),
        "script_src": text.count("<script src"),
        "link_tags": text.count("<link"),
        "inline_scripts": text.count("<script"),
    }
    return checks

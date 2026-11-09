"""Connector package — import side-effects register every built-in connector."""

from . import (  # noqa: F401
    apple_health,
    dexcom,
    oura,
    synthetic,
    yazio,
)
from .base import (  # noqa: F401
    SourceConnector,
    available_connectors,
    get_connector,
    register_connector,
)

__all__ = [
    "SourceConnector",
    "get_connector",
    "register_connector",
    "available_connectors",
]

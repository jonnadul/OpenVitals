"""Source connector framework for VitalFrame.

A connector is anything that produces a :class:`HealthData` from some external
source. Connectors are selected by ``type`` in the config and instantiated via
:func:`get_connector`. Add your own by subclassing ``SourceConnector`` and
registering it with ``register_connector`` (or by subclassing and calling
``SourceConnector.register``).
"""

from __future__ import annotations

import importlib
from typing import Dict, Type

from ..config import SourceConfig
from ..models import HealthData


class SourceConnector:
    """Base class for all ingestion connectors.

    Subclasses set ``type_key`` and implement :meth:`fetch`. They receive the
    resolved ``SourceConfig`` (so secrets/paths live in config, never in code).
    """

    type_key: str = "base"
    requires_network: bool = False

    def __init__(self, cfg: SourceConfig) -> None:
        self.cfg = cfg
        self.name = cfg.name or self.type_key

    def connect(self) -> None:
        """Optional setup (open clients, authenticate). Default: no-op."""

    def fetch(self) -> HealthData:
        """Return a HealthData batch. Must be implemented by subclasses."""
        raise NotImplementedError

    def close(self) -> None:
        """Optional teardown. Default: no-op."""

    # convenience for subclasses
    @property
    def params(self) -> Dict:
        return self.cfg.params

    @classmethod
    def register(cls) -> None:
        _REGISTRY[cls.type_key] = cls


_REGISTRY: Dict[str, Type[SourceConnector]] = {}


def register_connector(key: str, cls: Type[SourceConnector]) -> None:
    _REGISTRY[key] = cls


def get_connector(cfg: SourceConfig) -> SourceConnector:
    """Instantiate the connector named by ``cfg.type``.

    Falls back to plugin import ``vitalframe.connectors.<type>`` if not already
    registered (so new connector modules self-register on import).
    """
    if cfg.type in _REGISTRY:
        return _REGISTRY[cfg.type](cfg)
    # try lazy import of the matching module
    try:
        mod = importlib.import_module(f"vitalframe.connectors.{cfg.type}")
        # module should register on import
        if cfg.type in _REGISTRY:
            return _REGISTRY[cfg.type](cfg)
        # also accept a class named <Camel>Connector
        for attr in vars(mod).values():
            if isinstance(attr, type) and issubclass(attr, SourceConnector) and attr is not SourceConnector:
                if attr.type_key == cfg.type or attr.type_key == "base":
                    attr.type_key = cfg.type
                    register_connector(cfg.type, attr)
                    return attr(cfg)
    except ModuleNotFoundError:
        pass
    raise ValueError(
        f"Unknown connector type '{cfg.type}'. Available: {sorted(_REGISTRY)}"
    )


def available_connectors() -> list:
    return sorted(_REGISTRY)

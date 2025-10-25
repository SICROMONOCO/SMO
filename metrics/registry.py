"""Central metrics registry.

This module imports the per-area metric providers (cpu, memory, diskes, networks)
and exposes a unified registry API so the rest of the framework can fetch a
single JSON-serializable dict of all metrics.

API:
  - register(name, func): register a metrics provider function (callable -> dict)
  - unregister(name)
  - gather_all(): call all providers and return a merged dict
  - to_primitive(obj): normalize psutil namedtuples/enums/bytes/iterables -> primitives

The file intentionally keeps output in a structure similar to the original modules
but ensures all values are plain Python primitives suitable for JSON serialization.
"""
from __future__ import annotations

import time
import math
import enum
import threading
from typing import Any, Callable, Dict

try:
    # when imported as package: use relative imports
    from . import cpu as cpu_mod
    from . import memory as memory_mod
    from . import diskes as disk_mod
    from . import networks as net_mod
    from . import process as process_mod
except ImportError:  # pragma: no cover - allow running file directly
    # when executed as a script, the package context may be missing; fall back
    # to absolute imports using the package path 'Agents.metrics'.
    import importlib
    import os
    import sys

    # Ensure the workspace root (two levels up: .../SMO) is on sys.path so
    # 'Agents' is importable when this file is executed directly.
    this_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.abspath(os.path.join(this_dir, "..", ".."))
    if workspace_root not in sys.path:
        sys.path.insert(0, workspace_root)

    # Import from the local 'metrics' package when executed outside a package
    cpu_mod = importlib.import_module("metrics.cpu")
    memory_mod = importlib.import_module("metrics.memory")
    disk_mod = importlib.import_module("metrics.diskes")
    net_mod = importlib.import_module("metrics.networks")
    process_mod = importlib.import_module("metrics.process")

# Registry of provider functions: name -> callable returning dict
_PROVIDERS = {}  # existing provider registry
_LATEST = {}
_LOCK = threading.RLock()
_LATEST: dict[str, dict] = {}  # cache of most recent results
_LAST_UPDATE: dict[str, float] = {}

def set_latest(name: str, data: dict):
    """Save the latest snapshot for a provider."""
    _LATEST[name] = data
    _LAST_UPDATE[name] = time.time()

def get_latest(name: str) -> dict | None:
    """Get last known snapshot for a provider."""
    return _LATEST.get(name)


def register_provider(name: str, func: callable):
    with _LOCK:
        _PROVIDERS[name] = func

def get_provider(name: str):
    with _LOCK:
        return _PROVIDERS.get(name)

def get_providers():
    with _LOCK:
        return list(_PROVIDERS.keys())

def set_latest(name: str, value):
    with _LOCK:
        _LATEST[name] = value

def gather_all():
    with _LOCK:
        # return a shallow copy to avoid callers mutating internal state
        combined = {k: _LATEST.get(k) for k in _PROVIDERS.keys()}
    return combined


def to_primitive(obj: Any, _seen: set | None = None) -> Any:
    """Convert arbitrary psutil/OS objects into JSON-serializable primitives.

    Handles:
      - namedtuples (._asdict or _fields)
      - enums (returns name)
      - bytes/bytearray -> decoded str or repr
      - dicts, iterables -> nested conversion
      - objects with __dict__ -> dict
      - floats NaN/inf -> str
    """
    if _seen is None:
        _seen = set()
    oid = id(obj)
    if oid in _seen:
        return "<recursion>"
    _seen.add(oid)

    # primitives
    if obj is None or isinstance(obj, (bool, int, str)):
        _seen.discard(oid)
        return obj

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            _seen.discard(oid)
            return str(obj)
        _seen.discard(oid)
        return obj

    if isinstance(obj, (bytes, bytearray)):
        try:
            s = obj.decode("utf-8")
            _seen.discard(oid)
            return s
        except Exception:
            _seen.discard(oid)
            return repr(obj)

    if isinstance(obj, enum.Enum):
        _seen.discard(oid)
        return obj.name if hasattr(obj, "name") else str(obj)

    # psutil namedtuple-like
    if hasattr(obj, "_asdict"):
        try:
            result = {k: to_primitive(v, _seen) for k, v in obj._asdict().items()}
            _seen.discard(oid)
            return result
        except Exception:
            pass
    if hasattr(obj, "_fields"):
        try:
            vals = tuple(obj)
            result = {k: to_primitive(v, _seen) for k, v in zip(obj._fields, vals)}
            _seen.discard(oid)
            return result
        except Exception:
            pass

    if isinstance(obj, dict):
        result = {to_primitive(k, _seen): to_primitive(v, _seen) for k, v in obj.items()}
        _seen.discard(oid)
        return result

    if isinstance(obj, (list, tuple, set)):
        result = [to_primitive(i, _seen) for i in obj]
        _seen.discard(oid)
        return result

    # fallback: try vars()
    try:
        v = vars(obj)
        if isinstance(v, dict):
            result = {k: to_primitive(val, _seen) for k, val in v.items()}
            _seen.discard(oid)
            return result
    except Exception:
        pass

    # final fallback
    try:
        s = str(obj)
        _seen.discard(oid)
        return s
    finally:
        if oid in _seen:
            _seen.discard(oid)


def register(name: str, func: Callable[[], dict]) -> None:
    """Register a provider function under `name`.

    The provider should be a callable taking no arguments and returning a dict.
    """
    if not callable(func):
        raise TypeError("func must be callable")
    _PROVIDERS[name] = func


def unregister(name: str) -> None:
    _PROVIDERS.pop(name, None)


def gather_all() -> dict:
    """Call all registered providers and return a merged, normalized dict.

    The result has the shape:
      {
         "timestamp": <float>,
         "<provider_name>": { ... provider data ... },
         "<other_provider>": { ... }
      }

    All values are passed through `to_primitive`.
    """
    out: dict[str, Any] = {"timestamp": time.time()}
    for name, func in list(_PROVIDERS.items()):
        try:
            raw = func()
            out[name] = to_primitive(raw)
        except Exception as exc:  # don't let one failing provider stop others
            out[name] = {"error": str(exc)}
    return out


# --- Register built-in providers from the local metric modules ---
register("cpu", cpu_mod.get_cpu_metrics)
register("memory", memory_mod.get_memory_metrics)
register("disk", disk_mod.get_disk_metrics)
register("network", net_mod.get_network_metrics)
register("process", process_mod.gather)


    
"""Simple logger used by the SMO agent.

This module provides JSONL and CSV logging. The CSV writer preserves and
expands headers when new keys appear so columns aren't lost between runs.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict
from metrics import registry


# Keep imports light at module import time (metrics can depend on psutil).

LOG_DIR = "logs"
JSON_LOG = os.path.join(LOG_DIR, "smo_metrics.jsonl")
CSV_LOG = os.path.join(LOG_DIR, "smo_metrics.csv")

os.makedirs(LOG_DIR, exist_ok=True)


def log_json(snapshot: Dict[str, Any]) -> None:
    """Append the snapshot as one JSON line to the JSONL log."""
    try:
        with open(JSON_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
    except Exception:
        # Best-effort logging; don't fail the caller
        return


def _flatten(obj: Any, prefix: str = "") -> Dict[str, Any]:
    """Recursively flatten nested dicts into dotted keys.

    Non-primitive values (lists, None, objects) are JSON-dumped to keep CSV
    cells simple.
    """
    out: Dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                out.update(_flatten(v, key))
            elif isinstance(v, (int, float, str)):
                out[key] = v
            else:
                try:
                    out[key] = json.dumps(v, ensure_ascii=False)
                except Exception:
                    out[key] = str(v)
    else:
        out[prefix or "value"] = obj
    return out


def log_csv(snapshot: Dict[str, Any]) -> None:
    """Flatten the snapshot and append to CSV, expanding headers when needed."""
    try:
        flat: Dict[str, Any] = {"timestamp": datetime.now().isoformat()}
        for section, data in snapshot.items():
            if section == "timestamp":
                continue
            if isinstance(data, dict):
                flat.update(_flatten(data, section))
            else:
                flat[section] = data

        _write_csv_preserve_headers(flat)
    except Exception:
        return


def _write_csv_preserve_headers(row: Dict[str, Any]) -> None:
    """Write a row to CSV, preserving and expanding headers (atomic rewrite)."""
    try:
        new_keys = list(row.keys())
        if not os.path.exists(CSV_LOG):
            with open(CSV_LOG, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=new_keys)
                writer.writeheader()
                writer.writerow(row)
            return

        # Read existing file
        with open(CSV_LOG, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_fields = reader.fieldnames or []
            existing_rows = list(reader)

        # Build union of fields: keep existing order, append any new keys
        union_fields = list(existing_fields)
        for k in new_keys:
            if k not in union_fields:
                union_fields.append(k)

        # If nothing new, append quickly
        if set(new_keys).issubset(set(existing_fields)):
            with open(CSV_LOG, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=existing_fields)
                writer.writerow(row)
            return

        # Otherwise rewrite file with expanded header
        tmp = CSV_LOG + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=union_fields)
            writer.writeheader()
            for r in existing_rows:
                out = {k: r.get(k, "") for k in union_fields}
                writer.writerow(out)
            out_new = {k: row.get(k, "") for k in union_fields}
            writer.writerow(out_new)

        os.replace(tmp, CSV_LOG)
    except Exception:
        return


def log_snapshot(snapshot: Dict[str, Any]) -> None:
    """Log snapshot to JSONL and CSV (best-effort)."""
    log_json(snapshot)
    log_csv(snapshot)

if __name__ == "__main__":
    log_snapshot(registry.gather_all())


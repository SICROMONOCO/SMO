"""Logging utilities for SMO metrics snapshots.
Provides functions to log snapshots to InfluxDB and JSONL format.
"""

from __future__ import annotations
import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, Iterator, List, Tuple
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# This ensures InfluxDB credentials are loaded for standalone installations
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

_METADATA_KEYS = {
    "unit",
    "type",
    "description",
    "refresh_interval",
    "human_readable",
    "alert",
    "threshold",
    "level",
    "message",
    "time",
}
from io import StringIO
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Keep imports light at module import time (metrics can depend on psutil).

LOG_DIR = "logs"
JSON_LOG = os.path.join(LOG_DIR, "smo_metrics.jsonl")

os.makedirs(LOG_DIR, exist_ok=True)

class MetricsLogger:
    def __init__(self, log_file: str = JSON_LOG):
        self.log_file = log_file
        self.influx_client = None
        self._init_influxdb()

    def _init_influxdb(self):
        try:
            url = os.environ.get("INFLUXDB_URL", "http://smo-db:8086")
            token = os.environ.get("INFLUXDB_TOKEN", "my-super-secret-token")
            org = os.environ.get("INFLUXDB_ORG", "my-org")
            self.bucket = os.environ.get("INFLUXDB_BUCKET", "smo-metrics")
            
            print(f"Initializing InfluxDB client:")
            print(f"  URL: {url}")
            print(f"  Org: {org}")
            print(f"  Bucket: {self.bucket}")
            print(f"  Token: {'*' * 10 + token[-10:] if len(token) > 10 else '***'}")
            
            self.influx_client = InfluxDBClient(url=url, token=token, org=org)
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            print("✓ InfluxDB client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize InfluxDB client: {e}")
            print("  Metrics will be logged to file only (not to InfluxDB)")
            self.influx_client = None

    def log(self, snapshot: Dict[str, Any]) -> None:
        """Log the snapshot in JSON format and write to InfluxDB."""
        if "alert" in snapshot and len(snapshot) == 1:
            return

        if "timestamp" not in snapshot:
            snapshot["timestamp"] = datetime.now().timestamp()

        # Log to JSONL file
        try:
            with open(self.log_file, "a", encoding="utf-8", buffering=1) as f:
                f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
        except Exception:
            pass

        # Write to InfluxDB
        if self.influx_client:
            try:
                points = self._snapshot_to_points(snapshot)
                if points:
                    self.write_api.write(bucket=self.bucket, record=points)
            except Exception as e:
                print(f"Failed to write to InfluxDB: {e}")

    def _snapshot_to_points(self, snapshot: Dict[str, Any]) -> List[Point]:
        points: List[Point] = []
        
        # Ensure timestamp exists and is valid
        timestamp_value = snapshot.get("timestamp")
        if timestamp_value is None:
            timestamp = datetime.now()
        else:
            try:
                timestamp = datetime.fromtimestamp(timestamp_value)
            except (ValueError, TypeError, OSError):
                timestamp = datetime.now()

        for metric, data in snapshot.items():
            if metric in {"timestamp", "alerts"}:
                continue

            field_values = dict(self._iter_numeric_fields(data))
            if not field_values:
                continue

            point = Point(metric).time(timestamp)
            for field_name, value in field_values.items():
                try:
                    point.field(field_name, value)
                except Exception:
                    # Skip invalid fields
                    continue
            points.append(point)
        return points

    def _iter_numeric_fields(self, payload: Any, prefix: Tuple[str, ...] = ()) -> Iterator[Tuple[str, int | float]]:
        """Yield flattened numeric fields from nested payload structures.
        
        Preserves integer types for fields like 'pid' to avoid InfluxDB type conflicts.
        """

        if isinstance(payload, dict):
            # Handle dicts that directly expose numeric values via the "value" key
            if "value" in payload:
                value = payload["value"]
                if isinstance(value, (int, float)):
                    # Preserve integer type, convert float to float
                    yield self._build_field_name(prefix or ("value",)), value
                elif isinstance(value, (dict, list)):
                    yield from self._iter_numeric_fields(value, prefix)

            for key, value in payload.items():
                if key in _METADATA_KEYS or key == "value":
                    continue
                yield from self._iter_numeric_fields(value, prefix + (key,))

        elif isinstance(payload, list):
            for idx, item in enumerate(payload):
                yield from self._iter_numeric_fields(item, prefix + (str(idx),))

        elif isinstance(payload, (int, float)):
            # Preserve the original type (int or float)
            yield self._build_field_name(prefix or ("value",)), payload

    def _build_field_name(self, parts: Tuple[str, ...]) -> str:
        safe_parts = [part.replace(" ", "_") for part in parts if part]
        return "_".join(safe_parts) or "value"

    def write_alert(self, alert: Dict[str, Any]) -> None:
        pass

    def read_json_logs(self) -> Iterator[Dict[str, Any]]:
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    yield json.loads(line.strip())
        except Exception:
            return

    def transform_to_csv(self, data: Dict[str, Any] = None) -> str:
        if data:
            entries = [data]
        else:
            entries = list(self.read_json_logs())
            
        if not entries:
            return ""

        flattened_entries = []
        all_fields = set()
        
        for entry in entries:
            flat = self._flatten_entry(entry)
            flattened_entries.append(flat)
            all_fields.update(flat.keys())
            
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=sorted(all_fields))
        writer.writeheader()
        
        for entry in flattened_entries:
            row = {field: entry.get(field, "") for field in all_fields}
            writer.writerow(row)
            
        return output.getvalue()

    def _flatten_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        flat: Dict[str, Any] = {"timestamp": entry.get("timestamp", datetime.now().isoformat())}
        
        for section, data in entry.items():
            if section == "timestamp":
                continue
            if isinstance(data, dict):
                flat.update(self._flatten(data, section))
            else:
                flat[section] = data
        return flat

    def _flatten(self, obj: Any, prefix: str = "") -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    out.update(self._flatten(v, key))
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

logger = MetricsLogger()

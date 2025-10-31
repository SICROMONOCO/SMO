"""Logging utilities for SMO metrics snapshots.
Provides functions to log snapshots in JSONL format with optional CSV transformation.
"""

from __future__ import annotations
import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, Iterator, List
from io import StringIO

# Keep imports light at module import time (metrics can depend on psutil).

LOG_DIR = "logs"
JSON_LOG = os.path.join(LOG_DIR, "smo_metrics.jsonl")

os.makedirs(LOG_DIR, exist_ok=True)

class MetricsLogger:
    def __init__(self, log_file: str = JSON_LOG):
        self.log_file = log_file
    
    def log(self, snapshot: Dict[str, Any]) -> None:
        """Log the snapshot in JSON format."""
        # Don't log if it's just an alert without metrics
        if "alert" in snapshot and len(snapshot) == 1:
            return
            
        try:
            # Ensure we have a timestamp
            if "timestamp" not in snapshot:
                snapshot["timestamp"] = datetime.now().timestamp()
                
            with open(self.log_file, "a", encoding="utf-8", buffering=1) as f:
                f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
        except Exception:
            # Best-effort logging; don't fail the caller
            return
            
    def write_alert(self, alert: Dict[str, Any]) -> None:
        """This method is called by the alerts system but we want to avoid separate alert logging.
        Alerts should be included in the main snapshot instead."""
        pass  # Intentionally do nothing - alerts are handled in the main snapshot
    
    def read_json_logs(self) -> Iterator[Dict[str, Any]]:
        """Read JSON logs line by line."""
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    yield json.loads(line.strip())
        except Exception:
            return
            
    def transform_to_csv(self, data: Dict[str, Any] = None) -> str:
        """Transform a single snapshot or all logs to CSV format.
        
        Args:
            data: Optional single snapshot to transform. If None, transforms all logs.
            
        Returns:
            CSV formatted string
        """
        if data:
            entries = [data]
        else:
            entries = list(self.read_json_logs())
            
        if not entries:
            return ""
            
        # Flatten all entries first to get complete field list
        flattened_entries = []
        all_fields = set()
        
        for entry in entries:
            flat = self._flatten_entry(entry)
            flattened_entries.append(flat)
            all_fields.update(flat.keys())
            
        # Convert to CSV string
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=sorted(all_fields))
        writer.writeheader()
        
        for entry in flattened_entries:
            # Ensure all fields are present
            row = {field: entry.get(field, "") for field in all_fields}
            writer.writerow(row)
            
        return output.getvalue()


    def _flatten_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten a single log entry for CSV format."""
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
        """Recursively flatten nested dicts into dotted keys.
        
        Non-primitive values (lists, None, objects) are JSON-dumped to keep CSV
        cells simple.
        """
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


# Create a default logger instance
logger = MetricsLogger()


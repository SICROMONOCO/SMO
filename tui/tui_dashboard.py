
"""
The main TUI dashboard application.

This file brings together the modular UI components from the `widgets`
directory and orchestrates the application's behavior.
"""

from __future__ import annotations
import json
import logging
import yaml
import csv
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Optional

# Textual Imports
from textual.app import App, ComposeResult
from textual.dom import NoMatches
from textual.containers import Container, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TabbedContent,
    TabPane,
    RadioButton,
    RadioSet,
)

# Local Widget Imports
from .widgets.metric_group import MetricGroup
from .widgets.cpu_stats import CPUStatsGroup
from .widgets.memory import MemoryGroup
from .widgets.disk import DiskUsageGroup
from .widgets.network import NetworkIOGroup
from .widgets.system_info import SystemInfoGroup
from .widgets.alerts import AlertsGroup

# Set up logging
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# 1. CSS - STYLING
# ----------------------------------------------------------------------------

DEFAULT_CSS = """
Screen {
    background: #0a0a0a;
    color: #f0f0f0;
    layout: vertical;
}

TabbedContent {
    background: #1a1a1a;
    height: 1fr;
}

TabPane {
    padding: 1;
}

/* Live view container - use full available space, leave room for bottom bar */
#live-view-container {
    width: 100%;
    height: 100%;
    min-height: 50;
    overflow-y: auto;
}

/* Fixed bottom bar for alerts */
#alerts-bottom-bar {
    width: 100%;
    height: 5;
    min-height: 5;
    max-height: 5;
    background: #1a1a1a;
    border-top: thick #4a4a4a;
    layout: vertical;
}

/* Metric Groups - flexible sizing with overflow */
MetricGroup {
    border: round #4a4a4a;
    background: #121212;
    margin-bottom: 1;
    padding: 1;
    height: auto;
    min-height: 8;
    max-height: 25vh; /* Limit max height, enable scrolling */
    overflow-y: auto;
    layout: vertical;
}

/* Important groups get more space */
#cpu_stats {
    min-height: 8;
    max-height: 30vh;
}

#memory {
    min-height: 6;
    max-height: 25vh;
}

#disk_usage {
    min-height: 6;
    max-height: 25vh;
}

#network_io {
    min-height: 6;
    max-height: 25vh;
}

/* Alerts in bottom bar - compact single line, no border, no title */
#alerts-bottom-bar #alerts {
    border: none;
    background: #1a1a1a;
    width: 100%;
    height: 3;
    min-height: 3;
    max-height: 3;
    padding: 0;
    margin: 0;
    overflow: hidden;
}

/* Hide the title label in bottom bar alerts (if it exists) */
#alerts-bottom-bar #alerts > Label {
    display: none;
}

/* Ensure alerts Static widget takes full height in bottom bar */
#alerts-bottom-bar #alerts > Static {
    height: 3;
    min-height: 3;
}


MetricGroup > Label {
    width: 100%;
    background: #2a2a2a;
    color: #e0e0e0;
    padding: 0 1;
    border-bottom: thick #4a4a4a;
    text-style: bold;
    height: 1;
    min-height: 1;
}

/* Static widgets inside metric groups */
MetricGroup > Static {
    width: 100%;
    padding: 0 1;
    height: auto;
    min-height: 3;
    overflow-y: auto;
    visibility: visible;
    display: block;
}

#alerts > Label {
    background: #3a1a1a;
    color: #ffaaaa;
    height: 1;
    min-height: 1;
}

/* Alerts renderable in bottom bar - single line, no wrap */
#alerts-bottom-bar #alerts-renderable {
    width: 100%;
    height: 3;
    min-height: 3;
    overflow: hidden;
    text-overflow: ellipsis;
    padding: 0 1;
    content-align: left middle;
    background: #2a1a1a;
    border-top: thick #ff6b6b;
}

.stat-title {
    color: #888;
    text-style: bold;
    margin-top: 1;
}

.config-section-header {
    margin-top: 1;
}

Button {
    margin: 1;
    width: 100%;
}

"""

# ----------------------------------------------------------------------------
# 2. MAIN APPLICATION
# ----------------------------------------------------------------------------

class TUIDashboardApp(App):
    """The main TUI Dashboard Application."""

    CSS = DEFAULT_CSS
    TITLE = "TUI Dashboard"
    SUB_TITLE = "Live Stats, Config, and More"

    # --- State Management ---

    available_groups = {
        "cpu_stats": {"class": CPUStatsGroup, "name": "CPU Stats", "desc": "Shows real-time CPU load and per-core usage."},
        "memory": {"class": MemoryGroup, "name": "Memory", "desc": "Displays memory and swap usage."},
        "disk_usage": {"class": DiskUsageGroup, "name": "Disk Usage", "desc": "Shows disk space usage for mounted partitions."},
        "network_io": {"class": NetworkIOGroup, "name": "Network I/O", "desc": "Displays current network traffic (upload/download)."},
        "system_info": {"class": SystemInfoGroup, "name": "System Info", "desc": "Provides general system information like OS and hostname."},
    }


    latest_metrics: reactive[dict] = reactive({})
    


    # --- Data Loading ---

    CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
    METRICS_LOG_PATH = Path(__file__).parent.parent / "logs" / "smo_metrics.jsonl"

    def load_config_to_ui(self) -> None:
        """Load config from YAML and dynamically populate the config editor."""
        try:
            container = self.query_one("#config-editor-container")
            container.remove_children()
            with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if config is None:
                config = {}
            widgets = self._create_config_widgets(config)
            container.mount(*widgets)
        except NoMatches:
            self.notify("Config editor container not found.", severity="error")
            logger.error("Config editor container not found")
        except IOError as e:
            self.notify(f"Error reading config file: {e}", severity="error")
            logger.error(f"Error reading config file: {e}")
        except yaml.YAMLError as e:
            self.notify(f"Error parsing config YAML: {e}", severity="error")
            logger.error(f"Error parsing config YAML: {e}")

    def _set_nested_dict_value(self, d: dict, keys: str, value: str) -> None:
        """Sets a value in a nested dictionary using a dot-separated key string, attempting type conversion."""
        keys_list = keys.split('.')
        current_level = d
        for key in keys_list[:-1]:
            if not isinstance(current_level.setdefault(key, {}), dict):
                # If the key exists but is not a dict, convert it to a dict
                current_level[key] = {}
            current_level = current_level[key]

        last_key = keys_list[-1]
        original_value = current_level.get(last_key)

        new_value: Any = value
        if original_value is not None:
            original_type = type(original_value)
            try:
                if original_type == bool:
                    new_value = value.lower() in ['true', '1', 't', 'y', 'yes']
                elif original_type == int:
                    new_value = int(value)
                elif original_type == float:
                    new_value = float(value)
                else:
                    new_value = original_type(value)
            except (ValueError, TypeError):
                # Keep as string if conversion fails
                logger.warning(f"Failed to convert '{value}' to {original_type.__name__}, keeping as string")

        current_level[last_key] = new_value

    def save_config_from_ui(self) -> None:
        """Save the current UI input values to the config file."""
        try:
            with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            inputs = self.query("#config-editor-container Input")
            for input_widget in inputs:
                if input_widget.id:
                    key_path = input_widget.id.replace("config-input-", "").replace("-", ".")
                    value = input_widget.value
                    self._set_nested_dict_value(config, key_path, value)

            self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

            self.notify("Configuration saved successfully!", severity="information")
            logger.info("Configuration saved successfully")

        except NoMatches:
            self.notify("Config editor container not found.", severity="error")
            logger.error("Config editor container not found")
        except IOError as e:
            self.notify(f"Error accessing config file: {e}", severity="error")
            logger.error(f"Error accessing config file: {e}")
        except yaml.YAMLError as e:
            self.notify(f"Error writing config YAML: {e}", severity="error")
            logger.error(f"Error writing config YAML: {e}")
        except ValueError as e:
            self.notify(f"Invalid configuration value: {e}", severity="error")
            logger.error(f"Invalid configuration value: {e}")

    def update_metrics(self) -> None:
        """Reads and parses the last line from the metrics log file."""
        if not self.METRICS_LOG_PATH.exists():
            self.sub_title = "Metrics log file not found."
            logger.warning(f"Metrics log file not found: {self.METRICS_LOG_PATH}")
            return

        try:
            with open(self.METRICS_LOG_PATH, "r", encoding="utf-8") as f:
                last_line = None
                for line in f:
                    if line.strip():
                        last_line = line

                if last_line:
                    self.latest_metrics = json.loads(last_line)
                else:
                    logger.debug("Metrics log file is empty")

        except json.JSONDecodeError as e:
            error_msg = f"Error parsing metrics JSON: {e}"
            self.sub_title = error_msg
            logger.error(error_msg)
        except IOError as e:
            error_msg = f"Error reading metrics file: {e}"
            self.sub_title = error_msg
            logger.error(error_msg)

    def watch_latest_metrics(self, old_metrics: dict, new_metrics: dict) -> None:
        """Called when self.latest_metrics changes. Passes data to visible widgets."""
        # Update all mounted MetricGroup widgets (including alerts in bottom bar)
        for widget in self.query(MetricGroup):
            try:
                if hasattr(widget, "update_data"):
                    widget.update_data(new_metrics)
            except NoMatches:
                # Widget query failed, skip
                logger.debug(f"Widget {widget} not found for update")
                continue
            except Exception as e:
                # Be resilient to individual widget errors but log them
                logger.warning(f"Error updating widget {widget.id}: {e}", exc_info=True)
                continue

    # watch_active_groups removed: group toggling via UI is no longer supported.

    def _create_config_widgets(self, config_data: dict, parent_key: str = "") -> list:
        """Recursively create widgets for the config editor."""
        widgets = []
        for key, value in config_data.items():
            current_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, dict):
                widgets.append(Static(f"[bold]{key.replace('_', ' ').title()}:[/bold]", classes="config-section-header"))
                widgets.extend(self._create_config_widgets(value, current_key))
            else:
                # Add a label for better UX
                label_text = key.replace('_', ' ').title()
                widgets.append(Label(label_text))
                widgets.append(
                    Input(
                        placeholder=f"Enter {label_text.lower()}",
                        value=str(value) if value is not None else "",
                        id=f"config-input-{current_key.replace('.', '-')}"
                    )
                )
        return widgets

    # --- Main UI Composition ---

    def compose(self) -> ComposeResult:
        """Create the main layout and widgets for the app."""
        yield Header()
        with TabbedContent(initial="live_view_tab"):
            with TabPane("Live View", id="live_view_tab"):
                yield ScrollableContainer(id="live-view-container")

            with TabPane("Config Editor", id="config_editor_tab"):
                with ScrollableContainer(id="config-editor-container"):
                    pass  # Populated dynamically
                with Container(id="config-editor-buttons"):
                    yield Button("Save Changes", variant="success", id="save_config")
                    yield Button("Restore Defaults", variant="error", id="restore_config")

            with TabPane("Log Exporter", id="log_exporter_tab"):
                with Container(id="log-exporter-container"):
                    yield Static("Select Export Format:")
                    with RadioSet(id="export_format"):
                        yield RadioButton("JSON", value=True)
                        yield RadioButton("CSV")
                        yield RadioButton("Markdown")
                    yield Input(placeholder="/path/to/export.log", id="export_path")
                    yield Button("Export", variant="primary", id="export_logs")
            
        # Fixed bottom bar for alerts
        with Container(id="alerts-bottom-bar"):
            yield AlertsGroup(title="Alerts", id="alerts")
        
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        self.set_interval(2, self.update_metrics)
        self.load_config_to_ui()
        self.update_metrics()
        
        # Mount widgets after a short delay to ensure DOM is ready
        self.set_timer(0.5, self._mount_all_widgets)
        
        # Mount alerts widget in bottom bar
        self.set_timer(0.6, self._mount_alerts_widget)
        
    
    def _mount_alerts_widget(self) -> None:
        """Ensure alerts widget is properly set up in the bottom bar."""
        try:
            alerts_widget = self.query_one("#alerts", AlertsGroup)
            logger.info("Alerts widget is ready in bottom bar")
        except NoMatches:
            logger.warning("Alerts widget not found in bottom bar")
        except Exception as e:
            logger.error(f"Error checking alerts widget: {e}", exc_info=True)
    
    def _mount_all_widgets(self) -> None:
        """Mount all metric groups into the live view container."""
        try:
            live_view = self.query_one("#live-view-container", ScrollableContainer)
            logger.info(f"Mounting {len(self.available_groups)} widgets into live view")
            
            for group_id, info in self.available_groups.items():
                try:
                    # Check if already mounted
                    self.query_one(f"#{group_id}", MetricGroup)
                    logger.debug(f"Widget {group_id} already exists")
                except NoMatches:
                    # Create and mount new widget
                    try:
                        new_widget = info["class"](title=info["name"], id=group_id)
                        live_view.mount(new_widget)
                        logger.info(f"✓ Mounted: {group_id} ({info['name']})")
                    except Exception as e:
                        logger.error(f"Failed to mount {group_id}: {e}", exc_info=True)
                        
        except NoMatches:
            logger.error("Live view container #live-view-container not found!")
        except Exception as e:
            logger.error(f"Error in _mount_all_widgets: {e}", exc_info=True)


    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "save_config":
            self.save_config_from_ui()
        elif event.button.id == "restore_config":
            # Reload config from disk and update UI
            self.load_config_to_ui()
            self.notify("Restored unsaved changes from config file.", severity="information")
        elif event.button.id == "export_logs":
            self.export_logs()
    # Switch-related handlers removed: toggling groups from the UI is no longer supported.

    # --- Log Exporting ---

    def _flatten_dict(self, d: dict, parent_key: str = '', sep: str = '.') -> dict:
        """Flatten a nested dictionary into a single-level dictionary with dot-separated keys."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def export_logs(self) -> None:
        """Export metric logs to the specified format and path."""
        try:
            export_path_str = self.query_one("#export_path", Input).value
            if not export_path_str:
                self.notify("Export path cannot be empty.", severity="error")
                return

            export_path = Path(export_path_str)
            
            # Check if format is selected
            radio_set = self.query_one(RadioSet)
            pressed_button = radio_set.pressed_button
            if pressed_button is None:
                self.notify("Please select an export format.", severity="error")
                return
                
            selected_format = pressed_button.label.plain.lower()

            if not self.METRICS_LOG_PATH.exists():
                self.notify(f"Metrics log file not found: {self.METRICS_LOG_PATH}", severity="error")
                logger.error(f"Metrics log file not found: {self.METRICS_LOG_PATH}")
                return

            with open(self.METRICS_LOG_PATH, "r", encoding="utf-8") as f:
                logs = [json.loads(line) for line in f if line.strip()]

            if not logs:
                self.notify("No logs to export.", severity="warning")
                return

            export_path.parent.mkdir(parents=True, exist_ok=True)

            if selected_format == "json":
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2)

            elif selected_format == "csv":
                flat_logs = [self._flatten_dict(log) for log in logs]
                if flat_logs:
                    headers = sorted(list(set(key for log in flat_logs for key in log.keys())))
                    with open(export_path, "w", newline='', encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=headers)
                        writer.writeheader()
                        writer.writerows(flat_logs)

            elif selected_format == "markdown":
                flat_logs = [self._flatten_dict(log) for log in logs]
                if flat_logs:
                    headers = sorted(list(set(key for log in flat_logs for key in log.keys())))
                    with open(export_path, "w", encoding="utf-8") as f:
                        f.write(f"| {' | '.join(headers)} |\n")
                        f.write(f"| {' | '.join(['---'] * len(headers))} |\n")
                        for log in flat_logs:
                            row = [str(log.get(h, '')) for h in headers]
                            f.write(f"| {' | '.join(row)} |\n")
            else:
                self.notify(f"Unknown export format: {selected_format}", severity="error")
                logger.error(f"Unknown export format: {selected_format}")
                return

            self.notify(f"Logs successfully exported to {export_path}", severity="information")
            logger.info(f"Logs successfully exported to {export_path}")

        except NoMatches as e:
            self.notify(f"UI component not found: {e}", severity="error")
            logger.error(f"UI component not found during export: {e}")
        except IOError as e:
            self.notify(f"File I/O error during export: {e}", severity="error")
            logger.error(f"File I/O error during export: {e}")
        except json.JSONDecodeError as e:
            self.notify(f"Error parsing log JSON: {e}", severity="error")
            logger.error(f"Error parsing log JSON: {e}")
        except Exception as e:
            self.notify(f"Failed to export logs: {e}", severity="error")
            logger.error(f"Failed to export logs: {e}", exc_info=True)

# ----------------------------------------------------------------------------
# 3. RUN THE APP
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    app = TUIDashboardApp()
    app.run()

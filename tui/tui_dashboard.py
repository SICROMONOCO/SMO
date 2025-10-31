
"""
The main TUI dashboard application.

This file brings together the modular UI components from the `widgets`
directory and orchestrates the application's behavior.
"""

from __future__ import annotations
import json
import yaml
import csv
from pathlib import Path

# Textual Imports
from textual.app import App, ComposeResult
from textual.dom import NoMatches
from textual.containers import Container, Horizontal, VerticalScroll, ScrollableContainer
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


# ----------------------------------------------------------------------------
# 1. CSS - STYLING
# ----------------------------------------------------------------------------

DEFAULT_CSS = """
Screen {
    background: #0a0a0a;
    color: #f0f0f0;
}

TabbedContent {
    background: #1a1a1a;
}

TabPane {
    padding: 1 2;
}

MetricGroup {
    border: round #4a4a4a;
    background: #121212;
    margin-bottom: 1;
    padding: 0 1;
}

MetricGroup > Label {
    width: 100%;
    background: #2a2a2a;
    color: #e0e0e0;
    padding: 0 1;
    border-bottom: thick #4a4a4a;
    text-style: bold;
}

.stat-title {
    color: #888;
    text-style: bold;
    margin-top: 1;
}

#live-view-sidebar {
    width: 30%;
    min-width: 25;
    border-right: thick #2a2a2a;
    padding-right: 2;
    margin-right: 2;
}

.config-section-header {
    margin-top: 1;
}

"""

# ----------------------------------------------------------------------------
# 2. MAIN APPLICATION
# ----------------------------------------------------------------------------

class TUIDashboardApp(App):
    """The main TUI Dashboard Application."""

    CSS = DEFAULT_CSS
    TITLE = "Modular TUI Dashboard"
    SUB_TITLE = "Live Stats, Config, and More"

    # --- State Management ---

    available_groups = {
        "cpu_stats": {"class": CPUStatsGroup, "name": "CPU Stats", "desc": "Shows real-time CPU load and per-core usage."},
        "memory": {"class": MemoryGroup, "name": "Memory", "desc": "Displays memory and swap usage."},
        "disk_usage": {"class": DiskUsageGroup, "name": "Disk Usage", "desc": "Shows disk space usage for mounted partitions."},
        "network_io": {"class": NetworkIOGroup, "name": "Network I/O", "desc": "Displays current network traffic (upload/download)."},
        "system_info": {"class": SystemInfoGroup, "name": "System Info", "desc": "Provides general system information like OS and hostname."},
    }

    # We no longer support toggling groups on/off dynamically via the UI.
    # All available groups are mounted into the live view by default.

    latest_metrics: reactive[dict] = reactive({})

    # --- Data Loading ---

    CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
    METRICS_LOG_PATH = Path(__file__).parent.parent / "logs" / "smo_metrics.jsonl"

    def load_config_to_ui(self) -> None:
        """Load config from YAML and dynamically populate the config editor."""
        try:
            container = self.query_one("#config-editor-container")
            container.remove_children()
            with open(self.CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
            widgets = self._create_config_widgets(config)
            container.mount(*widgets)
        except (IOError, yaml.YAMLError, NoMatches) as e:
            self.notify(f"Error loading config: {e}", severity="error")

    def _set_nested_dict_value(self, d: dict, keys: str, value: str):
        """Sets a value in a nested dictionary using a dot-separated key string, attempting type conversion."""
        keys_list = keys.split('.')
        current_level = d
        for key in keys_list[:-1]:
            current_level = current_level.setdefault(key, {})

        last_key = keys_list[-1]
        original_value = current_level.get(last_key)

        new_value = value
        if original_value is not None:
            original_type = type(original_value)
            try:
                if original_type == bool:
                    new_value = value.lower() in ['true', '1', 't', 'y', 'yes']
                else:
                    new_value = original_type(value)
            except (ValueError, TypeError):
                pass # Keep as string if conversion fails

        current_level[last_key] = new_value

    def save_config_from_ui(self) -> None:
        """Save the current UI input values to the config file."""
        try:
            with open(self.CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)

            inputs = self.query("#config-editor-container Input")
            for input_widget in inputs:
                if input_widget.id:
                    key_path = input_widget.id.replace("config-input-", "").replace("-", ".")
                    value = input_widget.value
                    self._set_nested_dict_value(config, key_path, value)

            with open(self.CONFIG_PATH, "w") as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

            self.notify("Configuration saved successfully!", severity="information")

        except (IOError, yaml.YAMLError, ValueError, NoMatches) as e:
            self.notify(f"Error saving config: {e}", severity="error")

    def update_metrics(self) -> None:
        """Reads and parses the last line from the metrics log file."""
        if not self.METRICS_LOG_PATH.exists():
            self.sub_title = "Metrics log file not found."
            return

        try:
            with open(self.METRICS_LOG_PATH, "r", encoding="utf-8") as f:
                last_line = None
                for line in f:
                    if line.strip():
                        last_line = line

                if last_line:
                    self.latest_metrics = json.loads(last_line)

        except (json.JSONDecodeError, IOError) as e:
            self.sub_title = f"Error reading metrics: {e}"

    def watch_latest_metrics(self, old_metrics: dict, new_metrics: dict) -> None:
        """Called when self.latest_metrics changes. Passes data to visible widgets."""
        # Update all mounted MetricGroup widgets. This avoids relying on
        # in-UI toggle state which was removed.
        for widget in self.query(MetricGroup):
            try:
                if hasattr(widget, "update_data"):
                    widget.update_data(new_metrics)
            except Exception:
                # be resilient to individual widget errors
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
                widgets.append(
                    Input(
                        placeholder=f"{key}: {value}",
                        value=str(value),
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

        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        self.set_interval(2, self.update_metrics)
        self.load_config_to_ui()
        self.update_metrics()
        # Mount all available metric groups into the live view by default.
        try:
            live_view = self.query_one("#live-view-container", ScrollableContainer)
            for group_id, info in self.available_groups.items():
                try:
                    # avoid duplicate mounts if already present
                    self.query_one(f"#{group_id}", MetricGroup)
                except NoMatches:
                    new_widget = info["class"](title=info["name"], id=group_id)
                    live_view.mount(new_widget)
        except NoMatches:
            pass


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

    def _flatten_dict(self, d: dict, parent_key: str = '', sep: str ='.') -> dict:
        items = []
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def export_logs(self) -> None:
        """Export metric logs to the specified format and path."""
        export_path_str = self.query_one("#export_path", Input).value
        if not export_path_str:
            self.notify("Export path cannot be empty.", severity="error")
            return

        export_path = Path(export_path_str)
        selected_format = self.query_one(RadioSet).pressed_button.label.plain.lower()

        try:
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

            self.notify(f"Logs successfully exported to {export_path}", severity="information")

        except Exception as e:
            self.notify(f"Failed to export logs: {e}", severity="error")


# ----------------------------------------------------------------------------
# 3. RUN THE APP
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    app = TUIDashboardApp()
    app.run()

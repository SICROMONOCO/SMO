
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
from datetime import datetime
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
    DirectoryTree,
)

# Local Widget Imports
from .widgets.metric_group import MetricGroup
from .widgets.cpu_stats import CPUStatsGroup
from .widgets.memory import MemoryGroup
from .widgets.disk import DiskUsageGroup
from .widgets.network import NetworkIOGroup
from .widgets.system_info import SystemInfoGroup
from .widgets.process import ProcessGroup
from .widgets.alerts import AlertsGroup

# Set up logging
logger = logging.getLogger(__name__)

# Import centralized configuration
try:
    from config_loader import load_config, save_config, get_config_path, DEFAULT_CONFIG as AGENT_DEFAULT_CONFIG
except Exception:  # pragma: no cover - defensive guard if import path changes
    AGENT_DEFAULT_CONFIG = {}
    # Fallback functions if config_loader is not available
    def load_config():
        return AGENT_DEFAULT_CONFIG
    def save_config(config):
        return False
    def get_config_path():
        return Path(__file__).parent.parent / "config" / "config.yaml"


# ----------------------------------------------------------------------------
# 1. CSS - STYLING
# ----------------------------------------------------------------------------

DEFAULT_CSS = """
/* ========================================================================
   MODERN TUI DESIGN - Clean, Spacious, and Convenient
   ======================================================================== */

Screen {
    background: #0d1117;
    color: #e6edf3;
    layout: vertical;
}

/* Header and Footer Styling */
Header {
    background: #161b22;
    color: #58a6ff;
    text-style: bold;
}

Footer {
    background: #161b22;
}

/* Main content area takes remaining space */
#main-content {
    width: 100%;
    height: 1fr;
    dock: top;
    padding: 0;
}

TabbedContent {
    background: #0d1117;
    height: 100%;
    border: none;
}

TabbedContent > ContentSwitcher {
    background: #0d1117;
    padding: 0 1;
}

/* Tab styling */
Tabs {
    background: #161b22;
    dock: top;
}

Tab {
    background: #21262d;
    color: #7d8590;
    padding: 0 2;
    margin: 0 1;
    text-style: bold;
}

Tab:hover {
    background: #30363d;
    color: #c9d1d9;
}

Tab.-active {
    background: #388bfd;
    color: #ffffff;
}

TabPane {
    padding: 1 2;
    background: #0d1117;
    overflow-y: auto;
}

/* Live view container - clean scrolling */
#live-view-container {
    width: 100%;
    height: 100%;
    min-height: 30;
    overflow-y: auto;
    padding: 1;
    scrollbar-background: #161b22;
    scrollbar-color: #30363d;
    scrollbar-color-hover: #484f58;
}

/* Fixed bottom bar for alerts - clean separation */
#alerts-bottom-bar {
    dock: bottom;
    width: 100%;
    height: 7;
    background: #161b22;
    border-top: wide #f85149;
}

/* ========================================================================
   METRIC GROUPS - Card-based design with better hierarchy
   ======================================================================== */

MetricGroup {
    border: round #30363d;
    background: #161b22;
    margin: 0 0 1 0;
    padding: 0;
    height: auto;
    min-height: 8;
    max-height: 25vh;
    overflow-y: auto;
    layout: vertical;
    scrollbar-background: #0d1117;
    scrollbar-color: #21262d;
}

MetricGroup:focus-within {
    border: round #58a6ff;
}

/* Priority sizing for different metric types */
#cpu_stats {
    min-height: 10;
    max-height: 35vh;
    border: round #388bfd;
}

#memory {
    min-height: 8;
    max-height: 28vh;
    border: round #a371f7;
}

#disk_usage {
    min-height: 8;
    max-height: 30vh;
    border: round #f778ba;
}

#network_io {
    min-height: 8;
    max-height: 25vh;
    border: round #56d364;
}

#process {
    min-height: 8;
    max-height: 25vh;
    border: round #ffa657;
}

#system_info {
    min-height: 6;
    max-height: 20vh;
    border: round #79c0ff;
}

/* Metric Group Headers - Modern card-style headers */
MetricGroup > Label {
    width: 100%;
    background: #21262d;
    color: #58a6ff;
    padding: 1 2;
    text-style: bold;
    height: 3;
    content-align: center middle;
    border-bottom: tall #30363d;
}

#cpu_stats > Label {
    background: #1c2d41;
    color: #79c0ff;
}

#memory > Label {
    background: #2b2140;
    color: #d2a8ff;
}

#disk_usage > Label {
    background: #3b1f2e;
    color: #f778ba;
}

#network_io > Label {
    background: #1b2d1f;
    color: #7ee787;
}

#process > Label {
    background: #2d2416;
    color: #ffa657;
}

#system_info > Label {
    background: #1c2d41;
    color: #79c0ff;
}

/* Static widgets inside metric groups - better padding and readability */
MetricGroup > Static {
    width: 100%;
    padding: 1 2;
    height: auto;
    min-height: 4;
    overflow-y: auto;
    background: #0d1117;
}

/* ========================================================================
   ALERTS SECTION - Clean and visible
   ======================================================================== */

#alerts-bottom-bar #alerts {
    border: none;
    background: #161b22;
    width: 100%;
    height: 100%;
    padding: 0 1;
    margin: 0;
    overflow-y: auto;
    scrollbar-background: #0d1117;
    scrollbar-color: #21262d;
}

#alerts-bottom-bar #alerts > Label {
    display: none;
}

#alerts-bottom-bar #alerts > Static {
    width: 100%;
    height: auto;
    background: #161b22;
}

#alerts-bottom-bar #alerts-renderable {
    width: 100%;
    height: auto;
    padding: 1;
    content-align: left top;
    background: #161b22;
}

/* ========================================================================
   CONFIG EDITOR - Clean form design
   ======================================================================== */

#config-editor-container {
    padding: 2;
    background: #0d1117;
}

.config-section-header {
    margin-top: 2;
    margin-bottom: 1;
    color: #58a6ff;
    text-style: bold;
}

#config-editor-container Label {
    color: #7d8590;
    margin-top: 1;
    margin-bottom: 0;
}

Input {
    background: #161b22;
    border: tall #30363d;
    color: #e6edf3;
    padding: 0 1;
    margin-bottom: 1;
}

Input:focus {
    border: tall #58a6ff;
    background: #0d1117;
}

#config-editor-buttons {
    padding: 1 2;
    background: #0d1117;
}

Button {
    margin: 1 0;
    width: 100%;
    height: 3;
    border: tall #30363d;
    text-style: bold;
}

Button:hover {
    border: tall #58a6ff;
    background: #1f6feb;
}

Button.success {
    background: #238636;
    color: #ffffff;
}

Button.error {
    background: #da3633;
    color: #ffffff;
}

Button.primary {
    background: #1f6feb;
    color: #ffffff;
}

/* ========================================================================
   LOG EXPORTER - Clean layout
   ======================================================================== */

#log-exporter-container {
    padding: 1 2;
    background: #0d1117;
}

#export-title {
    color: #58a6ff;
    text-style: bold;
    margin-bottom: 0;
}

#export-description {
    color: #7d8590;
    margin-bottom: 2;
}

.export-section-label {
    color: #e6edf3;
    margin-top: 2;
    margin-bottom: 1;
}

#path-help {
    background: #161b22;
    border: round #30363d;
    padding: 1;
    margin: 1 0;
    color: #7d8590;
}

#path-validation {
    height: auto;
    min-height: 0;
    margin: 0 0 1 0;
    color: #7d8590;
}

#directory-browser-container {
    height: 20;
    border: round #30363d;
    background: #161b22;
    margin: 1 0 2 0;
    scrollbar-background: #0d1117;
    scrollbar-color: #21262d;
}

DirectoryTree {
    background: #161b22;
    color: #e6edf3;
    height: 100%;
}

#export-status {
    margin: 1 0;
    text-align: center;
    height: auto;
    min-height: 0;
}

RadioSet {
    background: #161b22;
    border: round #30363d;
    padding: 1;
    margin: 1 0;
}

RadioButton {
    background: #0d1117;
    margin: 0 1;
}

RadioButton:hover {
    background: #21262d;
}

#export_path {
    margin: 1 0 2 0;
}

"""

# ----------------------------------------------------------------------------
# 2. MAIN APPLICATION
# ----------------------------------------------------------------------------

class TUIDashboardApp(App):
    """The main TUI Dashboard Application."""

    CSS = DEFAULT_CSS
    TITLE = "SMO System Monitor"
    SUB_TITLE = "Real-time Performance & Configuration Dashboard"

    # --- State Management ---

    available_groups = {
        "cpu_stats": {"class": CPUStatsGroup, "name": "CPU Stats", "desc": "Shows real-time CPU load and per-core usage."},
        "memory": {"class": MemoryGroup, "name": "Memory", "desc": "Displays memory and swap usage."},
        "disk_usage": {"class": DiskUsageGroup, "name": "Disk Usage", "desc": "Shows disk space usage for mounted partitions."},
        "network_io": {"class": NetworkIOGroup, "name": "Network I/O", "desc": "Displays current network traffic (upload/download)."},
        "system_info": {"class": SystemInfoGroup, "name": "System Info", "desc": "Provides general system information like OS and hostname."},
        "process": {"class": ProcessGroup, "name": "Process", "desc": "Displays SMO agent process metrics (PID, uptime, CPU, memory, I/O, threads)."},
    }


    latest_metrics: reactive[dict] = reactive({})



    # --- Data Loading ---

    CONFIG_PATH = get_config_path()
    METRICS_LOG_PATH = Path(__file__).parent.parent / "logs" / "smo_metrics.jsonl"

    def load_config_to_ui(self) -> None:
        """Load config from YAML and dynamically populate the config editor."""
        try:
            container = self.query_one("#config-editor-container")

            # Robustly clear existing editor content to avoid duplicate IDs
            try:
                # Preferred: remove all current children explicitly
                for child in list(container.children):
                    try:
                        child.remove()
                    except Exception:
                        # Best-effort removal; continue clearing others
                        pass
            except Exception:
                # Fallback to container.remove_children if available
                try:
                    container.remove_children()  # type: ignore[attr-defined]
                except Exception:
                    # As a last resort, attempt to remove any known config inputs globally
                    for w in self.query("Input"):
                        if getattr(w, "id", "").startswith("config-input-"):
                            try:
                                w.remove()
                            except Exception:
                                pass
            # Use centralized config loader
            config = load_config()
            widgets = self._create_config_widgets(config)
            # Mount after a refresh tick to ensure removals are fully processed
            try:
                self.call_after_refresh(lambda: container.mount(*widgets))  # type: ignore[attr-defined]
            except Exception:
                # Fallback: schedule on next loop tick
                self.set_timer(0, lambda: container.mount(*widgets))
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
            # Load current config
            config = load_config()

            inputs = self.query("#config-editor-container Input")
            for input_widget in inputs:
                if input_widget.id:
                    key_path = input_widget.id.replace("config-input-", "").replace("-", ".")
                    value = input_widget.value
                    self._set_nested_dict_value(config, key_path, value)

            # Use centralized save function
            if save_config(config):
                self.notify("Configuration saved successfully!", severity="information")
                logger.info("Configuration saved successfully")
            else:
                raise IOError("Failed to save configuration")

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
        
        # Main content area (tabs)
        with Container(id="main-content"):
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
                    with ScrollableContainer(id="log-exporter-container"):
                        yield Static("[bold cyan]📁 Export System Metrics[/bold cyan]\n", id="export-title")
                        yield Static(
                            "[dim]Export collected metrics to JSON, CSV, or Markdown format.[/dim]\n",
                            id="export-description"
                        )
                        
                        # Format Selection
                        yield Static("[bold]1. Select Export Format:[/bold]", classes="export-section-label")
                        with RadioSet(id="export_format"):
                            yield RadioButton("JSON (Structured data with metadata)", value=True, id="fmt_json")
                            yield RadioButton("CSV (Flattened tabular format)", id="fmt_csv")
                            yield RadioButton("Markdown (Human-readable reports)", id="fmt_markdown")
                        
                        # Path Input Section
                        yield Static("[bold]2. Enter Export Path:[/bold]", classes="export-section-label")
                        yield Static(
                            "[dim]Examples:[/dim]\n"
                            "  • [cyan]~/exports/metrics.json[/cyan]  (home directory)\n"
                            "  • [cyan]/tmp/data/output.csv[/cyan]  (absolute path)\n"
                            "  • [cyan]./reports/metrics.md[/cyan]  (relative to current dir)\n"
                            "[dim]Tips: Use ~ for home, ./ for current directory[/dim]",
                            id="path-help"
                        )
                        yield Input(
                            placeholder="~/exports/metrics.json",
                            id="export_path"
                        )
                        yield Static("", id="path-validation")
                        
                        # File Browser Section
                        yield Static(
                            "[bold]3. Or Browse Directories:[/bold] [dim](Click to select destination folder)[/dim]",
                            classes="export-section-label"
                        )
                        with ScrollableContainer(id="directory-browser-container"):
                            yield DirectoryTree(str(Path.home()), id="directory_browser")
                        
                        # Export Button
                        yield Button("📤 Export Logs", variant="primary", id="export_logs")
                        yield Static("", id="export-status")

        # Fixed bottom bar for alerts (docked to bottom)
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
            # Overwrite config file with project defaults and refresh the editor
            self.restore_config_to_defaults()
        elif event.button.id == "export_logs":
            self.export_logs()

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Handle directory selection from the file browser."""
        try:
            selected_path = Path(event.path)
            
            # Get the currently selected format
            radio_set = self.query_one("#export_format", RadioSet)
            pressed_button = radio_set.pressed_button
            
            if pressed_button:
                # Determine file extension based on format
                format_label = pressed_button.label.plain.lower()
                if "json" in format_label:
                    extension = ".json"
                elif "csv" in format_label:
                    extension = ".csv"
                elif "markdown" in format_label:
                    extension = ".md"
                else:
                    extension = ".json"
                
                # Create a default filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"smo_metrics_{timestamp}{extension}"
                full_path = selected_path / filename
                
                # Update the input field
                export_input = self.query_one("#export_path", Input)
                export_input.value = str(full_path)
                
                # Show validation message
                validation = self.query_one("#path-validation", Static)
                validation.update(f"[green]✓[/green] Selected: [cyan]{full_path}[/cyan]")
                
                self.notify(f"Selected directory: {selected_path}", severity="information")
            else:
                self.notify("Please select an export format first", severity="warning")
        except Exception as e:
            logger.error(f"Error handling directory selection: {e}", exc_info=True)
            self.notify(f"Error selecting directory: {e}", severity="error")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Validate export path as user types."""
        if event.input.id == "export_path":
            try:
                path_str = event.value.strip()
                if not path_str:
                    validation = self.query_one("#path-validation", Static)
                    validation.update("")
                    return
                
                # Expand and validate path
                path = Path(path_str).expanduser()
                
                # Check parent directory
                parent = path.parent
                
                # Validate
                validation = self.query_one("#path-validation", Static)
                if parent.exists() and parent.is_dir():
                    validation.update(f"[green]✓[/green] Valid path. Will save to: [cyan]{path.resolve()}[/cyan]")
                elif not parent.exists():
                    validation.update(f"[yellow]⚠[/yellow] Directory will be created: [cyan]{parent}[/cyan]")
                else:
                    validation.update(f"[red]✗[/red] Invalid path")
            except Exception as e:
                validation = self.query_one("#path-validation", Static)
                validation.update(f"[red]✗[/red] Invalid path: {str(e)[:50]}")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Update file extension suggestion when format changes."""
        if event.radio_set.id == "export_format":
            try:
                export_input = self.query_one("#export_path", Input)
                current_path = export_input.value.strip()
                
                if not current_path:
                    return
                
                # Determine new extension
                format_label = event.pressed.label.plain.lower()
                if "json" in format_label:
                    new_ext = ".json"
                elif "csv" in format_label:
                    new_ext = ".csv"
                elif "markdown" in format_label:
                    new_ext = ".md"  # Prefer .md, but .markdown will be accepted
                else:
                    return
                
                # Update path with new extension
                path = Path(current_path).expanduser()
                new_path = path.with_suffix(new_ext)
                export_input.value = str(new_path)
                
                # Update validation
                validation = self.query_one("#path-validation", Static)
                validation.update(f"[blue]ℹ[/blue] Extension updated to {new_ext}")
            except Exception as e:
                logger.debug(f"Error updating extension: {e}")

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

    def _write_markdown_entry(self, f, log: dict, entry_num: int) -> None:
        """Write a single log entry in clean Markdown format (no front-matter)."""
        from datetime import datetime

        # Entry Header
        f.write(f"## Entry {entry_num}\n")

        # Timestamp (supports unix timestamp or ISO string)
        ts = log.get("timestamp")
        ts_text = "N/A"
        try:
            if isinstance(ts, (int, float)) and ts:
                dt = datetime.fromtimestamp(ts)
                ts_text = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            elif isinstance(ts, str) and ts:
                ts_text = ts
        except Exception:
            ts_text = str(ts) if ts else "N/A"

        f.write(f"**Timestamp:** {ts_text}\n\n")

        # System Overview
        system = log.get("system", {})
        if system:
            f.write("### 1. System Overview\n")
            f.write("| Metric | Value |\n")
            f.write("| :--- | :--- |\n")
            f.write(f"| **Hostname** | `{system.get('hostname', {}).get('value', 'N/A')}` |\n")
            f.write(f"| **OS** | {system.get('platform', {}).get('value', 'N/A')} |\n")
            f.write(f"| **Uptime** | {system.get('uptime', {}).get('human_readable', 'N/A')} |\n")
            f.write("\n")
        
        # CPU Usage
        cpu = log.get("cpu", {})
        if cpu:
            f.write("### 2. CPU Usage\n")
            avg_cpu = cpu.get("average", {}).get("cpu_percent", {}).get("value", 0)
            f.write(f"**Average Load:** {avg_cpu}%\n\n")
            
            # Core Breakdown
            per_core = cpu.get("per_core", {})
            if per_core:
                f.write("#### Core Breakdown\n")
                f.write("| Core ID | Usage (%) |\n")
                f.write("| :--- | :--- |\n")
                for key, val in sorted(per_core.items()):
                    if 'core_' in key and '_usage' in key:
                        core_num = key.replace('core_', '').replace('_usage', '')
                        usage = val.get('value', 0)
                        f.write(f"| Core {core_num} | {usage}% |\n")
                f.write("\n")
            
            # CPU Info
            count = cpu.get("count", {}).get("count", {}).get("value", "N/A")
            freq = cpu.get("frequency", {}).get("current", {}).get("value", 0)
            if count != "N/A" or freq > 0:
                f.write("#### CPU Info\n")
                f.write(f"- **Cores:** {count}\n")
                if freq > 0:
                    f.write(f"- **Frequency:** {freq/1000:.2f} GHz\n")
                f.write("\n")
        
        # Memory Status
        memory = log.get("memory", {})
        if memory:
            f.write("### 3. Memory Status\n")
            vmem = memory.get("virtual_memory", {})
            percent = vmem.get("percent", {}).get("value", 0)
            f.write(f"> **Summary:** Using **{percent}%** of available RAM.\n\n")
            f.write(f"- **Total:** {vmem.get('total', {}).get('human_readable', 'N/A')}\n")
            f.write(f"- **Used:** {vmem.get('used', {}).get('human_readable', 'N/A')}\n")
            f.write(f"- **Available:** {vmem.get('available', {}).get('human_readable', 'N/A')}\n")
            f.write("\n")
        
        # Disk & Storage
        disk = log.get("disk", {})
        if disk:
            f.write("### 4. Disk & Storage\n")
            # Find main partition
            main_part = None
            for key, val in disk.items():
                if key not in ("io_counters", "io_counters_perdisk") and isinstance(val, dict):
                    metrics = val.get("metrics", {})
                    if metrics:
                        main_part = metrics
                        break
            
            if main_part:
                usage = main_part.get("usage_percent", {}).get("value", 0)
                free = main_part.get("free", {}).get("human_readable", "N/A")
                total = main_part.get("total", {}).get("human_readable", "N/A")
                f.write(f"* **Usage:** {usage}%\n")
                f.write(f"* **Free Space:** {free}\n")
                f.write(f"* **Total Space:** {total}\n")
                f.write("\n")
        
        # Network Activity
        network = log.get("network", {})
        if network:
            f.write("### 5. Network Activity\n")
            io = network.get("io_counters", {}).get("metrics", {})
            if io:
                f.write("| Direction | Bytes | Packets |\n")
                f.write("| :--- | :--- | :--- |\n")
                bytes_sent = io.get("bytes_sent", {}).get("human_readable") or io.get("bytes_sent", {}).get("value", 0)
                bytes_recv = io.get("bytes_recv", {}).get("human_readable") or io.get("bytes_recv", {}).get("value", 0)
                packets_sent = io.get("packets_sent", {}).get("value", 0)
                packets_recv = io.get("packets_recv", {}).get("value", 0)
                f.write(f"| **Sent** | {bytes_sent} | {packets_sent:,} |\n")
                f.write(f"| **Received** | {bytes_recv} | {packets_recv:,} |\n")
                f.write("\n")
        
        # Process Details
        process = log.get("process", {})
        if process:
            f.write("### 6. Process Details\n")
            pid = process.get("pid", "N/A")
            status = process.get("status", {}).get("value", "N/A")
            cpu_usage = process.get("cpu", {}).get("value", 0)
            mem_usage = process.get("memory", {}).get("percent", {}).get("value", 0)
            f.write(f"**Focus Process:** `smo_agent` (PID: {pid})\n")
            f.write(f"- **Status:** {status}\n")
            f.write(f"- **CPU Consumed:** {cpu_usage}%\n")
            f.write(f"- **Memory Consumed:** {mem_usage}%\n")
        
        # Trailing newline for readability
        f.write("\n")

    def export_logs(self) -> None:
        """Export metric logs to the specified format and path."""
        status_widget = None
        try:
            # Get status widget for feedback
            status_widget = self.query_one("#export-status", Static)
            status_widget.update("[yellow]⏳ Processing export...[/yellow]")
            
            export_path_str = self.query_one("#export_path", Input).value
            export_path_str = export_path_str.strip()
            
            if not export_path_str:
                self.notify("❌ Export path cannot be empty.", severity="error")
                if status_widget:
                    status_widget.update("[red]✗ Error: Path is empty[/red]")
                return
            
            # Validate path characters
            if any(c in export_path_str for c in ['<', '>', '"', '|', '?', '*']):
                self.notify("❌ Invalid characters in path", severity="error")
                if status_widget:
                    status_widget.update("[red]✗ Error: Invalid path characters[/red]")
                return

            # Expand user path (e.g., ~/logs) and resolve to absolute path
            try:
                export_path = Path(export_path_str).expanduser().resolve()
            except Exception as e:
                self.notify(f"❌ Invalid path format: {e}", severity="error")
                if status_widget:
                    status_widget.update(f"[red]✗ Error: Invalid path format[/red]")
                return

            # Check if format is selected
            radio_set = self.query_one("#export_format", RadioSet)
            pressed_button = radio_set.pressed_button
            if pressed_button is None:
                self.notify("❌ Please select an export format.", severity="error")
                if status_widget:
                    status_widget.update("[red]✗ Error: No format selected[/red]")
                return

            # Extract format from label
            format_label = pressed_button.label.plain.lower()
            if "json" in format_label:
                selected_format = "json"
            elif "csv" in format_label:
                selected_format = "csv"
            elif "markdown" in format_label:
                selected_format = "markdown"
            else:
                selected_format = "json"
            
            # Validate file extension matches format (allow .md or .markdown)
            if selected_format == "markdown":
                valid_exts = {".md", ".markdown"}
                if export_path.suffix.lower() not in valid_exts:
                    self.notify(
                        "⚠️  Extension mismatch: expected .md or .markdown for MARKDOWN format",
                        severity="warning",
                        timeout=5
                    )
            else:
                expected_ext = f".{selected_format}"
                if export_path.suffix.lower() != expected_ext:
                    self.notify(
                        f"⚠️  Extension mismatch: expected {expected_ext} for {selected_format.upper()} format",
                        severity="warning",
                        timeout=5
                    )

            if not self.METRICS_LOG_PATH.exists():
                self.notify(f"❌ Source log file not found: {self.METRICS_LOG_PATH}", severity="error")
                if status_widget:
                    status_widget.update("[red]✗ Error: No metrics data available[/red]")
                logger.error(f"Metrics log file not found: {self.METRICS_LOG_PATH}")
                return

            # Read and parse logs robustly
            if status_widget:
                status_widget.update("[yellow]⏳ Reading metrics data...[/yellow]")

            logs = []
            skipped = 0
            with open(self.METRICS_LOG_PATH, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        # Strip potential BOM
                        if line and line[0] == "\ufeff":
                            line = line.lstrip("\ufeff")

                        try:
                            record = json.loads(line)
                        except json.JSONDecodeError:
                            # Try to extract JSON substring if line contains logging prefixes
                            start = line.find("{")
                            end = line.rfind("}")
                            if start != -1 and end != -1 and end > start:
                                candidate = line[start:end+1]
                                record = json.loads(candidate)
                            else:
                                raise
                        logs.append(record)
                    except Exception:
                        skipped += 1

            if skipped:
                self.notify(f"⚠️  Skipped {skipped} invalid log line(s)", severity="warning")
                if status_widget:
                    status_widget.update(f"[yellow]⚠ Skipped {skipped} invalid line(s)[/yellow]")

            if not logs:
                self.notify("⚠️  No logs to export - metrics file is empty.", severity="warning")
                if status_widget:
                    status_widget.update("[yellow]⚠ Warning: No data to export[/yellow]")
                return

            # Create parent directories with proper error handling
            if status_widget:
                status_widget.update("[yellow]⏳ Creating directories...[/yellow]")
            
            try:
                export_path.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                self.notify(f"❌ Permission denied: Cannot create directory {export_path.parent}", severity="error")
                if status_widget:
                    status_widget.update("[red]✗ Error: Permission denied[/red]")
                logger.error(f"Permission denied creating directory: {export_path.parent}")
                return
            except Exception as e:
                self.notify(f"❌ Failed to create directory: {e}", severity="error")
                if status_widget:
                    status_widget.update(f"[red]✗ Error: Cannot create directory[/red]")
                logger.error(f"Failed to create directory {export_path.parent}: {e}")
                return

            # Test write permissions before attempting full export
            try:
                test_file = export_path.parent / ".write_test"
                test_file.touch()
                test_file.unlink()
            except PermissionError:
                self.notify(f"❌ Permission denied: Cannot write to {export_path.parent}", severity="error")
                if status_widget:
                    status_widget.update("[red]✗ Error: Cannot write to destination[/red]")
                logger.error(f"Permission denied writing to: {export_path.parent}")
                return
            except Exception as e:
                logger.warning(f"Write test failed (non-fatal): {e}")

            # Export based on format
            if status_widget:
                status_widget.update(f"[yellow]⏳ Exporting {len(logs)} entries as {selected_format.upper()}...[/yellow]")
            
            if selected_format == "json":
                # Add metadata wrapper for better structure
                export_data = {
                    "export_metadata": {
                        "export_date": datetime.now().isoformat(),
                        "total_entries": len(logs),
                        "format": "json"
                    },
                    "metrics": logs
                }
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2)

            elif selected_format == "csv":
                flat_logs = [self._flatten_dict(log) for log in logs]
                if flat_logs:
                    headers = sorted(list(set(key for log in flat_logs for key in log.keys())))
                    with open(export_path, "w", newline='', encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=headers)
                        writer.writeheader()
                        writer.writerows(flat_logs)
                else:
                    self.notify("⚠️  No valid data to export to CSV", severity="warning")
                    if status_widget:
                        status_widget.update("[yellow]⚠ No exportable data[/yellow]")
                    return

            elif selected_format == "markdown":
                # Write a clean Markdown file with a header and per-entry sections
                with open(export_path, "w", encoding="utf-8") as f:
                    # Top-level header and metadata
                    f.write("# SMO Metrics Export\n\n")
                    f.write(f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\\n")
                    f.write(f"**Total Entries:** {len(logs)}\\n\n")

                    for idx, log in enumerate(logs, 1):
                        if idx > 1:
                            f.write("\n---\n\n")  # Horizontal rule between entries
                        self._write_markdown_entry(f, log, idx)
            else:
                self.notify(f"❌ Unknown export format: {selected_format}", severity="error")
                if status_widget:
                    status_widget.update("[red]✗ Error: Invalid format[/red]")
                logger.error(f"Unknown export format: {selected_format}")
                return

            # Success!
            self.notify(
                f"✅ Successfully exported {len(logs)} entries to {export_path.name}",
                severity="information",
                timeout=10
            )
            if status_widget:
                status_widget.update(f"[green]✓ Success! Exported to:[/green] [cyan]{export_path}[/cyan]")
            logger.info(f"Logs successfully exported to {export_path}")

        except NoMatches as e:
            self.notify(f"❌ UI component not found: {e}", severity="error")
            if status_widget:
                status_widget.update("[red]✗ Error: UI component missing[/red]")
            logger.error(f"UI component not found during export: {e}")
        except PermissionError as e:
            self.notify(f"❌ Permission denied: {e}", severity="error")
            if status_widget:
                status_widget.update("[red]✗ Error: Permission denied[/red]")
            logger.error(f"Permission error during export: {e}")
        except IOError as e:
            self.notify(f"❌ File I/O error: {e}", severity="error")
            if status_widget:
                status_widget.update("[red]✗ Error: File I/O error[/red]")
            logger.error(f"File I/O error during export: {e}")
        except json.JSONDecodeError as e:
            self.notify(f"❌ Error parsing metrics data: {e}", severity="error")
            if status_widget:
                status_widget.update("[red]✗ Error: Data parsing failed[/red]")
            logger.error(f"Error parsing log JSON: {e}")
        except Exception as e:
            self.notify(f"❌ Export failed: {e}", severity="error")
            if status_widget:
                status_widget.update(f"[red]✗ Error: {str(e)[:60]}[/red]")
            logger.error(f"Failed to export logs: {e}", exc_info=True)

    # --- Config Defaults Restore ---

    def restore_config_to_defaults(self) -> None:
        """Restore configuration file to the project's default values from agent.py."""
        try:
            if not AGENT_DEFAULT_CONFIG:
                # If import failed above, inform the user gracefully
                self.notify("Default config not available (agent import failed).", severity="error")
                logger.error("AGENT_DEFAULT_CONFIG is empty; unable to restore defaults.")
                return

            # Ensure config folder exists
            self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

            # Backup current config if present
            try:
                if self.CONFIG_PATH.exists():
                    backup_path = self.CONFIG_PATH.with_suffix(self.CONFIG_PATH.suffix + ".bak")
                    content = self.CONFIG_PATH.read_text(encoding="utf-8")
                    backup_path.write_text(content, encoding="utf-8")
                    logger.info(f"Backed up existing config to {backup_path}")
            except Exception as be:
                # Non-fatal; proceed but log the backup failure
                logger.warning(f"Failed to backup existing config: {be}")

            # Use centralized save function to write defaults
            if save_config(AGENT_DEFAULT_CONFIG):
                # Refresh UI inputs to reflect restored defaults
                self.load_config_to_ui()
                self.notify("Configuration restored to defaults.", severity="information")
                logger.info("Configuration restored to defaults from config_loader.DEFAULT_CONFIG")
            else:
                raise IOError("Failed to save default configuration")

        except IOError as e:
            self.notify(f"File error while restoring defaults: {e}", severity="error")
            logger.error(f"File error while restoring defaults: {e}")
        except yaml.YAMLError as e:
            self.notify(f"YAML error while writing defaults: {e}", severity="error")
            logger.error(f"YAML error while writing defaults: {e}")
        except Exception as e:
            self.notify(f"Failed to restore defaults: {e}", severity="error")
            logger.error(f"Failed to restore defaults: {e}", exc_info=True)

# ----------------------------------------------------------------------------
# 3. RUN THE APP
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    app = TUIDashboardApp()
    app.run()

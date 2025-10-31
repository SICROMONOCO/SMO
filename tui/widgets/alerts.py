from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static
from rich.table import Table
from rich.text import Text
from datetime import datetime
import logging

from .metric_group import MetricGroup

logger = logging.getLogger(__name__)

class AlertsGroup(MetricGroup):
    """A widget to display system alerts and warnings."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static("Checking alerts...", id="alerts-renderable")

    def update_data(self, metrics: dict) -> None:
        """Update the alerts display with the latest snapshot data."""
        if not isinstance(metrics, dict):
            logger.debug("Metrics is not a dict")
            return
            
        # Alerts can come from two places:
        # 1. Direct alerts array in snapshot["alerts"]
        # 2. Alert fields attached to individual metrics
        
        alerts = []
        logger.debug(f"Processing alerts from metrics, has 'alerts' key: {'alerts' in metrics}")
        
        try:
            # Check for top-level alerts array
            if "alerts" in metrics and isinstance(metrics["alerts"], list):
                alerts.extend(metrics["alerts"])
            
            # Check for alerts attached to specific metrics
            # CPU alerts
            cpu_alert = metrics.get("cpu", {}).get("average", {}).get("cpu_percent", {}).get("alert")
            if cpu_alert and isinstance(cpu_alert, dict):
                alerts.append({
                    "metric": "cpu_percent",
                    **cpu_alert
                })
            
            # Memory alerts
            mem_alert = metrics.get("memory", {}).get("virtual_memory", {}).get("percent", {}).get("alert")
            if mem_alert and isinstance(mem_alert, dict):
                alerts.append({
                    "metric": "memory_percent",
                    **mem_alert
                })
            
            # Disk alerts - check all partitions
            disk_data = metrics.get("disk", {})
            if isinstance(disk_data, dict):
                # Partitions are at top level, not under "partitions" key
                for dev, part_data in disk_data.items():
                    if dev in ("io_counters", "io_counters_perdisk"):
                        continue
                    if isinstance(part_data, dict):
                        # Check if it's a partition with metrics
                        metrics_data = part_data.get("metrics", {})
                        if metrics_data:
                            disk_alert = metrics_data.get("usage_percent", {}).get("alert")
                            if disk_alert and isinstance(disk_alert, dict):
                                alerts.append({
                                    "metric": f"disk_usage:{dev}",
                                    **disk_alert
                                })
            
            # Network alerts
            net_alert = metrics.get("network", {}).get("io_counters", {}).get("metrics", {}).get("bytes_sent", {}).get("alert")
            if net_alert and isinstance(net_alert, dict):
                alerts.append({
                    "metric": "network_bytes_sent",
                    **net_alert
                })
            
            # Check fallback alerts
            if "alerts_fallback" in metrics and isinstance(metrics["alerts_fallback"], list):
                for fallback_alert in metrics["alerts_fallback"]:
                    if isinstance(fallback_alert, dict):
                        alerts.append(fallback_alert)
        except (AttributeError, KeyError, TypeError) as e:
            # Gracefully handle any errors in parsing metrics
            logger.debug(f"Error parsing alerts from metrics: {e}")
            alerts = []

        try:
            # Find the Static widget
            static_widget = self.query_one("#alerts-renderable", Static)
            logger.debug(f"Found alerts Static widget, total alerts found: {len(alerts)}")
            
            if not alerts:
                # Show "No alerts" message as a single line
                no_alert_text = Text("✓ No active alerts", style="bold green")
                static_widget.update(no_alert_text)
                logger.debug("Updated with 'No active alerts' message")
                return

            # Sort alerts by level priority (error > warning > info)
            level_priority = {"error": 0, "warning": 1, "info": 2}
            alerts.sort(key=lambda x: level_priority.get(str(x.get("level", "info")).lower(), 3))

            # Create a single line display for all alerts
            alerts_text = Text()
            
            for idx, alert in enumerate(alerts):
                if not isinstance(alert, dict):
                    continue
                    
                level = str(alert.get("level", "info")).lower()
                metric = str(alert.get("metric", "unknown"))
                message = str(alert.get("message", "No message"))
                
                # Format metric name for display (compact)
                display_metric = metric.replace("_", " ").title()
                if ":" in display_metric:
                    parts = display_metric.split(":", 1)
                    display_metric = parts[0].strip()
                
                # Add separator between alerts
                if idx > 0:
                    alerts_text.append(" | ", style="dim")
                
                # Color code by level with icon
                if level == "error":
                    alerts_text.append("🔴 ", style="bold red")
                    alerts_text.append(f"{display_metric}: ", style="bold red")
                elif level == "warning":
                    alerts_text.append("⚠ ", style="bold yellow")
                    alerts_text.append(f"{display_metric}: ", style="bold yellow")
                else:
                    alerts_text.append("ℹ ", style="bold blue")
                    alerts_text.append(f"{display_metric}: ", style="bold blue")
                
                # Add message (truncate if too long)
                max_msg_len = 40
                if len(message) > max_msg_len:
                    message = message[:max_msg_len] + "..."
                alerts_text.append(message, style="white")

            # Ensure we have content to display
            if len(alerts_text) == 0:
                alerts_text = Text("No alerts data", style="dim")
            
            static_widget.update(alerts_text)
        except Exception as e:
            # Fallback display on any error
            logger.error(f"Error rendering alerts: {e}", exc_info=True)
            error_text = Text(f"Error: {str(e)[:50]}", style="red")
            try:
                error_widget = self.query_one("#alerts-renderable", Static)
                error_widget.update(error_text)
            except Exception as e2:
                logger.error(f"Failed to update alerts widget: {e2}", exc_info=True)


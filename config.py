"""
Configuration module for SMO Service Manager.

This module contains all configuration variables for the PyQt6 GUI application,
including service definitions, ports, commands, and the MOCK_MODE toggle.
"""

from typing import Dict, List, Any

# ============================================================================
# MOCK MODE CONFIGURATION
# ============================================================================
# When True: Simulates service operations without executing real commands
# When False: Executes actual subprocess commands
MOCK_MODE: bool = True

# ============================================================================
# SERVICE DEFINITIONS
# ============================================================================
# Each service has:
# - name: Display name
# - port: Port number the service runs on (None if no specific port)
# - start_command: Command to start the service
# - stop_command: Command to stop the service (None = kill by PID)
# - description: Human-readable description

SERVICES: List[Dict[str, Any]] = [
    {
        "name": "Core API",
        "port": 8000,
        "start_command": ["python", "-m", "http.server", "8000"],
        "stop_command": None,  # Will use PID to kill
        "description": "Main API server for SMO services"
    },
    {
        "name": "Database",
        "port": 5432,
        "start_command": ["python", "-m", "http.server", "5432"],
        "stop_command": None,
        "description": "PostgreSQL database server"
    },
    {
        "name": "Background Worker",
        "port": None,
        "start_command": ["python", "-c", "import time; time.sleep(1000)"],
        "stop_command": None,
        "description": "Background task processor"
    }
]

# ============================================================================
# GUI CONFIGURATION
# ============================================================================
# Window settings
WINDOW_TITLE: str = "SMO - Service Management Orchestrator"
WINDOW_WIDTH: int = 1000
WINDOW_HEIGHT: int = 700
WINDOW_MIN_WIDTH: int = 800
WINDOW_MIN_HEIGHT: int = 600

# Update intervals (milliseconds)
STATUS_UPDATE_INTERVAL: int = 1000  # Update service status every 1 second
LOG_UPDATE_INTERVAL: int = 500      # Update log display every 0.5 seconds

# Mock mode settings
MOCK_START_DELAY: float = 2.0  # Seconds to simulate service start
MOCK_STOP_DELAY: float = 1.0   # Seconds to simulate service stop

# Process management settings
PROCESS_STOP_TIMEOUT: int = 5  # Seconds to wait for graceful process termination

# ============================================================================
# STYLING
# ============================================================================
# Dark mode color scheme
DARK_MODE_STYLESHEET: str = """
QMainWindow {
    background-color: #1e1e1e;
    color: #ffffff;
}

QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}

QTableWidget {
    background-color: #252525;
    alternate-background-color: #2d2d2d;
    gridline-color: #3d3d3d;
    border: 1px solid #3d3d3d;
    selection-background-color: #0078d4;
}

QTableWidget::item {
    padding: 8px;
}

QHeaderView::section {
    background-color: #2d2d2d;
    color: #ffffff;
    padding: 8px;
    border: 1px solid #3d3d3d;
    font-weight: bold;
}

QPushButton {
    background-color: #0078d4;
    color: #ffffff;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #1084d8;
}

QPushButton:pressed {
    background-color: #006cbd;
}

QPushButton:disabled {
    background-color: #3d3d3d;
    color: #7d7d7d;
}

QPushButton.start-button {
    background-color: #28a745;
}

QPushButton.start-button:hover {
    background-color: #2db84d;
}

QPushButton.stop-button {
    background-color: #dc3545;
}

QPushButton.stop-button:hover {
    background-color: #e04555;
}

QPushButton.restart-button {
    background-color: #ffc107;
}

QPushButton.restart-button:hover {
    background-color: #ffca2c;
}

QTextEdit {
    background-color: #0c0c0c;
    color: #00ff00;
    border: 1px solid #3d3d3d;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 9pt;
}

QLabel {
    color: #ffffff;
}

QStatusBar {
    background-color: #2d2d2d;
    color: #ffffff;
}

QGroupBox {
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    margin-top: 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
"""

# Status colors
STATUS_COLORS: Dict[str, str] = {
    "running": "#28a745",  # Green
    "stopped": "#6c757d",  # Gray
    "starting": "#ffc107", # Yellow
    "stopping": "#fd7e14", # Orange
    "error": "#dc3545"     # Red
}

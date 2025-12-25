"""
SMO Service Manager - PyQt6 GUI Application.

This is the main entry point for the Service Management Orchestrator GUI.
It provides a XAMPP-like control panel for managing local services.
"""

import sys
from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QTextEdit,
    QLabel, QGroupBox, QHeaderView, QStatusBar, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont

import config
from service_manager import ServiceManager, ServiceStatus


class ServiceSignals(QObject):
    """
    Qt signals for service state changes.
    
    Signals must be defined in a QObject subclass.
    """
    status_changed = pyqtSignal(str, str)  # service_name, status


class ServiceManagerGUI(QMainWindow):
    """
    Main GUI window for the SMO Service Manager.
    
    Provides a modern, dark-themed interface for managing services
    similar to XAMPP Control Panel.
    """
    
    def __init__(self):
        """Initialize the main window and components."""
        super().__init__()
        
        # Initialize service manager
        self.service_manager: ServiceManager = ServiceManager()
        self.signals: ServiceSignals = ServiceSignals()
        
        # Service table widgets cache
        self.service_widgets: Dict[str, Dict[str, QWidget]] = {}
        
        # Setup UI
        self._init_ui()
        
        # Setup timers for status updates
        self._setup_timers()
        
        # Initial UI update
        self._update_all_services()
    
    def _init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle(config.WINDOW_TITLE)
        self.setGeometry(100, 100, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.setMinimumSize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        
        # Apply dark mode stylesheet
        self.setStyleSheet(config.DARK_MODE_STYLESHEET)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Create splitter for services and logs
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Create services section
        services_group = self._create_services_section()
        splitter.addWidget(services_group)
        
        # Create log console section
        log_group = self._create_log_section()
        splitter.addWidget(log_group)
        
        # Set initial splitter sizes (70% services, 30% logs)
        splitter.setSizes([500, 200])
        
        main_layout.addWidget(splitter)
        
        # Create global action buttons
        actions_layout = self._create_global_actions()
        main_layout.addLayout(actions_layout)
        
        # Create status bar
        self._create_status_bar()
    
    def _create_header(self) -> QWidget:
        """
        Create the header section with title and mode indicator.
        
        Returns:
            QWidget containing the header
        """
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title_label = QLabel("SMO Service Manager")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Mock mode indicator
        mode_label = QLabel(f"Mode: {'MOCK' if self.service_manager.mock_mode else 'LIVE'}")
        mode_label.setStyleSheet(
            "background-color: #ffc107; color: #000000; "
            "padding: 5px 10px; border-radius: 3px; font-weight: bold;"
            if self.service_manager.mock_mode else
            "background-color: #28a745; color: #ffffff; "
            "padding: 5px 10px; border-radius: 3px; font-weight: bold;"
        )
        header_layout.addWidget(mode_label)
        
        return header_widget
    
    def _create_services_section(self) -> QGroupBox:
        """
        Create the services table section.
        
        Returns:
            QGroupBox containing the services table
        """
        group = QGroupBox("Services")
        layout = QVBoxLayout(group)
        
        # Create table
        self.services_table = QTableWidget()
        self.services_table.setColumnCount(6)
        self.services_table.setHorizontalHeaderLabels([
            "Service Name", "Status", "PID", "Port", "Description", "Actions"
        ])
        
        # Configure table
        self.services_table.setAlternatingRowColors(True)
        self.services_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.services_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Set column widths
        header = self.services_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.services_table.setColumnWidth(5, 280)
        
        # Populate table with services
        services = self.service_manager.get_all_services()
        self.services_table.setRowCount(len(services))
        
        for row, service in enumerate(services):
            # Service name
            name_item = QTableWidgetItem(service.name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            name_font = QFont()
            name_font.setBold(True)
            name_item.setFont(name_font)
            self.services_table.setItem(row, 0, name_item)
            
            # Status indicator
            status_item = QTableWidgetItem()
            self.services_table.setItem(row, 1, status_item)
            
            # PID
            pid_item = QTableWidgetItem("-")
            pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.services_table.setItem(row, 2, pid_item)
            
            # Port
            port_text = str(service.port) if service.port else "-"
            port_item = QTableWidgetItem(port_text)
            port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.services_table.setItem(row, 3, port_item)
            
            # Description
            desc_item = QTableWidgetItem(service.description)
            desc_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.services_table.setItem(row, 4, desc_item)
            
            # Action buttons
            actions_widget = self._create_action_buttons(service.name)
            self.services_table.setCellWidget(row, 5, actions_widget)
            
            # Cache widgets for updates
            self.service_widgets[service.name] = {
                "status_item": status_item,
                "pid_item": pid_item,
                "start_btn": actions_widget.findChild(QPushButton, "start"),
                "stop_btn": actions_widget.findChild(QPushButton, "stop"),
                "restart_btn": actions_widget.findChild(QPushButton, "restart")
            }
        
        # Adjust row heights
        for row in range(self.services_table.rowCount()):
            self.services_table.setRowHeight(row, 50)
        
        layout.addWidget(self.services_table)
        return group
    
    def _create_action_buttons(self, service_name: str) -> QWidget:
        """
        Create action buttons for a service row.
        
        Args:
            service_name: Name of the service
            
        Returns:
            QWidget containing the action buttons
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Start button
        start_btn = QPushButton("Start")
        start_btn.setObjectName("start")
        start_btn.setProperty("class", "start-button")
        start_btn.setStyleSheet(
            "background-color: #28a745; min-width: 70px;"
            "QPushButton:hover { background-color: #2db84d; }"
        )
        start_btn.clicked.connect(lambda: self._on_start_service(service_name))
        layout.addWidget(start_btn)
        
        # Stop button
        stop_btn = QPushButton("Stop")
        stop_btn.setObjectName("stop")
        stop_btn.setProperty("class", "stop-button")
        stop_btn.setStyleSheet(
            "background-color: #dc3545; min-width: 70px;"
            "QPushButton:hover { background-color: #e04555; }"
        )
        stop_btn.clicked.connect(lambda: self._on_stop_service(service_name))
        layout.addWidget(stop_btn)
        
        # Restart button
        restart_btn = QPushButton("Restart")
        restart_btn.setObjectName("restart")
        restart_btn.setProperty("class", "restart-button")
        restart_btn.setStyleSheet(
            "background-color: #ffc107; min-width: 70px;"
            "QPushButton:hover { background-color: #ffca2c; }"
        )
        restart_btn.clicked.connect(lambda: self._on_restart_service(service_name))
        layout.addWidget(restart_btn)
        
        return widget
    
    def _create_log_section(self) -> QGroupBox:
        """
        Create the log console section.
        
        Returns:
            QGroupBox containing the log console
        """
        group = QGroupBox("Console / Logs")
        layout = QVBoxLayout(group)
        
        # Create text edit for logs
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_console)
        
        # Create clear button
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self._clear_logs)
        layout.addWidget(clear_btn)
        
        return group
    
    def _create_global_actions(self) -> QHBoxLayout:
        """
        Create global action buttons.
        
        Returns:
            QHBoxLayout containing global action buttons
        """
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        # Start All button
        start_all_btn = QPushButton("Start All Services")
        start_all_btn.setStyleSheet(
            "background-color: #28a745; padding: 10px 20px; font-size: 11pt;"
            "QPushButton:hover { background-color: #2db84d; }"
        )
        start_all_btn.clicked.connect(self._on_start_all)
        layout.addWidget(start_all_btn)
        
        # Stop All button
        stop_all_btn = QPushButton("Stop All Services")
        stop_all_btn.setStyleSheet(
            "background-color: #dc3545; padding: 10px 20px; font-size: 11pt;"
            "QPushButton:hover { background-color: #e04555; }"
        )
        stop_all_btn.clicked.connect(self._on_stop_all)
        layout.addWidget(stop_all_btn)
        
        layout.addStretch()
        
        # Quit button
        quit_btn = QPushButton("Quit")
        quit_btn.setStyleSheet(
            "background-color: #6c757d; padding: 10px 20px; font-size: 11pt;"
            "QPushButton:hover { background-color: #5a6268; }"
        )
        quit_btn.clicked.connect(self._on_quit)
        layout.addWidget(quit_btn)
        
        return layout
    
    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _setup_timers(self) -> None:
        """Setup timers for periodic updates."""
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_all_services)
        self.status_timer.start(config.STATUS_UPDATE_INTERVAL)
        
        # Log update timer
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self._update_logs)
        self.log_timer.start(config.LOG_UPDATE_INTERVAL)
    
    def _update_all_services(self) -> None:
        """Update the display for all services."""
        for service in self.service_manager.get_all_services():
            self._update_service_display(service.name)
    
    def _update_service_display(self, service_name: str) -> None:
        """
        Update the display for a specific service.
        
        Args:
            service_name: Name of the service to update
        """
        service = self.service_manager.get_service_info(service_name)
        if not service or service_name not in self.service_widgets:
            return
        
        widgets = self.service_widgets[service_name]
        
        # Update status with LED-style indicator
        status_text = service.status.value.upper()
        status_color = config.STATUS_COLORS.get(service.status.value, "#6c757d")
        
        # Create status indicator with colored circle
        widgets["status_item"].setText(f"● {status_text}")
        widgets["status_item"].setForeground(QColor(status_color))
        
        # Update PID
        pid_text = str(service.pid) if service.pid else "-"
        widgets["pid_item"].setText(pid_text)
        
        # Update button states
        is_running = service.status == ServiceStatus.RUNNING
        is_stopped = service.status == ServiceStatus.STOPPED
        is_transitioning = service.status in (ServiceStatus.STARTING, ServiceStatus.STOPPING)
        
        widgets["start_btn"].setEnabled(is_stopped)
        widgets["stop_btn"].setEnabled(is_running)
        widgets["restart_btn"].setEnabled(is_running or is_stopped)
        
        # Disable all buttons during transition
        if is_transitioning:
            widgets["start_btn"].setEnabled(False)
            widgets["stop_btn"].setEnabled(False)
            widgets["restart_btn"].setEnabled(False)
    
    def _update_logs(self) -> None:
        """Update the log console with new messages."""
        logs = self.service_manager.get_logs()
        for log in logs:
            self.log_console.append(log)
        
        # Auto-scroll to bottom
        scrollbar = self.log_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _clear_logs(self) -> None:
        """Clear the log console."""
        self.log_console.clear()
    
    def _on_start_service(self, service_name: str) -> None:
        """
        Handle start service button click.
        
        Args:
            service_name: Name of the service to start
        """
        self.service_manager.start_service(service_name)
        self.status_bar.showMessage(f"Starting {service_name}...")
    
    def _on_stop_service(self, service_name: str) -> None:
        """
        Handle stop service button click.
        
        Args:
            service_name: Name of the service to stop
        """
        self.service_manager.stop_service(service_name)
        self.status_bar.showMessage(f"Stopping {service_name}...")
    
    def _on_restart_service(self, service_name: str) -> None:
        """
        Handle restart service button click.
        
        Args:
            service_name: Name of the service to restart
        """
        self.service_manager.restart_service(service_name)
        self.status_bar.showMessage(f"Restarting {service_name}...")
    
    def _on_start_all(self) -> None:
        """Handle start all services button click."""
        self.service_manager.start_all_services()
        self.status_bar.showMessage("Starting all services...")
    
    def _on_stop_all(self) -> None:
        """Handle stop all services button click."""
        self.service_manager.stop_all_services()
        self.status_bar.showMessage("Stopping all services...")
    
    def _on_quit(self) -> None:
        """Handle quit button click."""
        self.close()
    
    def closeEvent(self, event) -> None:
        """
        Handle window close event.
        
        Args:
            event: Close event
        """
        # Stop timers
        self.status_timer.stop()
        self.log_timer.stop()
        
        # Cleanup service manager
        self.service_manager.cleanup()
        
        event.accept()


def main() -> None:
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("SMO Service Manager")
    app.setOrganizationName("SICROMONOCO")
    
    # Create and show main window
    window = ServiceManagerGUI()
    window.show()
    
    # Run application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

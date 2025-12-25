"""
Service Manager module for SMO.

This module provides the backend logic for managing services (start, stop, restart).
It supports both mock mode (for testing) and real mode (with subprocess execution).
"""

import subprocess
import threading
import time
import queue
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import signal
import os

import config


class ServiceStatus(Enum):
    """Enumeration of possible service states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """
    Data class representing a service and its current state.
    
    Attributes:
        name: Service display name
        port: Port number (None if no specific port)
        status: Current service status
        pid: Process ID (None if not running)
        start_command: Command to start the service
        stop_command: Command to stop the service
        description: Service description
        process: Subprocess object (None in mock mode or when stopped)
    """
    name: str
    port: Optional[int]
    status: ServiceStatus = ServiceStatus.STOPPED
    pid: Optional[int] = None
    start_command: List[str] = field(default_factory=list)
    stop_command: Optional[List[str]] = None
    description: str = ""
    process: Optional[subprocess.Popen] = None


class ServiceManager:
    """
    Main service management class.
    
    Handles starting, stopping, and monitoring of services.
    Supports both mock mode and real subprocess execution.
    Uses threading to prevent blocking the GUI.
    """
    
    def __init__(self, mock_mode: bool = None):
        """
        Initialize the ServiceManager.
        
        Args:
            mock_mode: Override config.MOCK_MODE if provided
        """
        self.mock_mode: bool = mock_mode if mock_mode is not None else config.MOCK_MODE
        self.services: Dict[str, ServiceInfo] = {}
        self.log_queue: queue.Queue = queue.Queue()
        self._lock: threading.Lock = threading.Lock()
        
        # Initialize services from config
        self._initialize_services()
        
        self._log(f"ServiceManager initialized (MOCK_MODE={'ON' if self.mock_mode else 'OFF'})")
    
    def _initialize_services(self) -> None:
        """Initialize service objects from configuration."""
        for service_config in config.SERVICES:
            service = ServiceInfo(
                name=service_config["name"],
                port=service_config.get("port"),
                start_command=service_config["start_command"],
                stop_command=service_config.get("stop_command"),
                description=service_config.get("description", "")
            )
            self.services[service.name] = service
    
    def _log(self, message: str) -> None:
        """
        Add a log message to the queue.
        
        Args:
            message: Log message to add
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_queue.put(log_entry)
    
    def get_logs(self) -> List[str]:
        """
        Retrieve all pending log messages.
        
        Returns:
            List of log messages
        """
        logs = []
        while not self.log_queue.empty():
            try:
                logs.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        return logs
    
    def get_service_info(self, service_name: str) -> Optional[ServiceInfo]:
        """
        Get information about a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            ServiceInfo object or None if not found
        """
        return self.services.get(service_name)
    
    def get_all_services(self) -> List[ServiceInfo]:
        """
        Get information about all services.
        
        Returns:
            List of all ServiceInfo objects
        """
        return list(self.services.values())
    
    def start_service(self, service_name: str, callback: Optional[Callable] = None) -> bool:
        """
        Start a service asynchronously.
        
        Args:
            service_name: Name of the service to start
            callback: Optional callback function to call when complete
            
        Returns:
            True if start initiated successfully, False otherwise
        """
        service = self.services.get(service_name)
        if not service:
            self._log(f"ERROR: Service '{service_name}' not found")
            return False
        
        if service.status in (ServiceStatus.RUNNING, ServiceStatus.STARTING):
            self._log(f"Service '{service_name}' is already {service.status.value}")
            return False
        
        # Start in a separate thread to avoid blocking
        thread = threading.Thread(
            target=self._start_service_thread,
            args=(service_name, callback),
            daemon=True
        )
        thread.start()
        return True
    
    def _start_service_thread(self, service_name: str, callback: Optional[Callable]) -> None:
        """
        Thread function to start a service.
        
        Args:
            service_name: Name of the service to start
            callback: Optional callback function
        """
        service = self.services[service_name]
        
        with self._lock:
            service.status = ServiceStatus.STARTING
            self._log(f"Starting service '{service_name}'...")
        
        try:
            if self.mock_mode:
                # Mock mode: simulate start with delay
                time.sleep(config.MOCK_START_DELAY)
                with self._lock:
                    service.status = ServiceStatus.RUNNING
                    service.pid = os.getpid() + abs(hash(service_name)) % 10000
                    self._log(f"Service '{service_name}' started (mock PID: {service.pid})")
            else:
                # Real mode: execute subprocess
                try:
                    process = subprocess.Popen(
                        service.start_command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        shell=False  # Explicit for security
                    )
                    with self._lock:
                        service.process = process
                        service.pid = process.pid
                        service.status = ServiceStatus.RUNNING
                        port_info = f" on port {service.port}" if service.port else ""
                        self._log(f"Service '{service_name}' started (PID: {service.pid}{port_info})")
                except Exception as e:
                    with self._lock:
                        service.status = ServiceStatus.ERROR
                        self._log(f"ERROR: Failed to start '{service_name}': {str(e)}")
        except Exception as e:
            with self._lock:
                service.status = ServiceStatus.ERROR
                self._log(f"ERROR: Exception during start of '{service_name}': {str(e)}")
        
        if callback:
            callback(service_name, service.status)
    
    def stop_service(self, service_name: str, callback: Optional[Callable] = None) -> bool:
        """
        Stop a service asynchronously.
        
        Args:
            service_name: Name of the service to stop
            callback: Optional callback function to call when complete
            
        Returns:
            True if stop initiated successfully, False otherwise
        """
        service = self.services.get(service_name)
        if not service:
            self._log(f"ERROR: Service '{service_name}' not found")
            return False
        
        if service.status in (ServiceStatus.STOPPED, ServiceStatus.STOPPING):
            self._log(f"Service '{service_name}' is already {service.status.value}")
            return False
        
        # Stop in a separate thread to avoid blocking
        thread = threading.Thread(
            target=self._stop_service_thread,
            args=(service_name, callback),
            daemon=True
        )
        thread.start()
        return True
    
    def _stop_service_thread(self, service_name: str, callback: Optional[Callable]) -> None:
        """
        Thread function to stop a service.
        
        Args:
            service_name: Name of the service to stop
            callback: Optional callback function
        """
        service = self.services[service_name]
        
        with self._lock:
            service.status = ServiceStatus.STOPPING
            self._log(f"Stopping service '{service_name}'...")
        
        try:
            if self.mock_mode:
                # Mock mode: simulate stop with delay
                time.sleep(config.MOCK_STOP_DELAY)
                with self._lock:
                    service.status = ServiceStatus.STOPPED
                    service.pid = None
                    self._log(f"Service '{service_name}' stopped (mock)")
            else:
                # Real mode: terminate subprocess
                try:
                    if service.process:
                        service.process.terminate()
                        try:
                            service.process.wait(timeout=config.PROCESS_STOP_TIMEOUT)
                        except subprocess.TimeoutExpired:
                            service.process.kill()
                            service.process.wait()
                        
                        with self._lock:
                            service.process = None
                            service.pid = None
                            service.status = ServiceStatus.STOPPED
                            self._log(f"Service '{service_name}' stopped")
                    elif service.pid:
                        # Try to kill by PID if no process object
                        try:
                            os.kill(service.pid, signal.SIGTERM)
                            time.sleep(1)
                            with self._lock:
                                service.pid = None
                                service.status = ServiceStatus.STOPPED
                                self._log(f"Service '{service_name}' stopped (by PID)")
                        except ProcessLookupError:
                            with self._lock:
                                service.pid = None
                                service.status = ServiceStatus.STOPPED
                                self._log(f"Service '{service_name}' already stopped")
                except Exception as e:
                    with self._lock:
                        service.status = ServiceStatus.ERROR
                        self._log(f"ERROR: Failed to stop '{service_name}': {str(e)}")
        except Exception as e:
            with self._lock:
                service.status = ServiceStatus.ERROR
                self._log(f"ERROR: Exception during stop of '{service_name}': {str(e)}")
        
        if callback:
            callback(service_name, service.status)
    
    def restart_service(self, service_name: str, callback: Optional[Callable] = None) -> bool:
        """
        Restart a service (stop then start).
        
        Args:
            service_name: Name of the service to restart
            callback: Optional callback function to call when complete
            
        Returns:
            True if restart initiated successfully, False otherwise
        """
        service = self.services.get(service_name)
        if not service:
            self._log(f"ERROR: Service '{service_name}' not found")
            return False
        
        def restart_callback(name: str, status: ServiceStatus) -> None:
            """Callback after stop completes to initiate start."""
            if status == ServiceStatus.STOPPED:
                self.start_service(name, callback)
            elif callback:
                callback(name, status)
        
        if service.status == ServiceStatus.RUNNING:
            return self.stop_service(service_name, restart_callback)
        else:
            return self.start_service(service_name, callback)
    
    def start_all_services(self, callback: Optional[Callable] = None) -> None:
        """
        Start all services.
        
        Args:
            callback: Optional callback function
        """
        self._log("Starting all services...")
        for service_name in self.services.keys():
            self.start_service(service_name, callback)
    
    def stop_all_services(self, callback: Optional[Callable] = None) -> None:
        """
        Stop all services.
        
        Args:
            callback: Optional callback function
        """
        self._log("Stopping all services...")
        for service_name in self.services.keys():
            self.stop_service(service_name, callback)
    
    def cleanup(self) -> None:
        """Clean up all services (stop them if running)."""
        self._log("Cleaning up services...")
        for service in self.services.values():
            if service.status == ServiceStatus.RUNNING:
                if not self.mock_mode and service.process:
                    try:
                        service.process.terminate()
                        service.process.wait(timeout=config.PROCESS_STOP_TIMEOUT)
                    except Exception:
                        pass

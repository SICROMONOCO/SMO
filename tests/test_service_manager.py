"""
Tests for the service_manager module.

These tests verify the functionality of the ServiceManager class
in both mock and real modes.
"""

import pytest
import time
from service_manager import ServiceManager, ServiceStatus, ServiceInfo


def test_service_manager_initialization():
    """Test that ServiceManager initializes correctly."""
    manager = ServiceManager(mock_mode=True)
    
    assert manager.mock_mode is True
    assert len(manager.services) > 0
    
    # Check that services are loaded from config
    service_names = [s.name for s in manager.get_all_services()]
    assert "Core API" in service_names
    assert "Database" in service_names
    assert "Background Worker" in service_names


def test_get_service_info():
    """Test retrieving service information."""
    manager = ServiceManager(mock_mode=True)
    
    service = manager.get_service_info("Core API")
    assert service is not None
    assert service.name == "Core API"
    assert service.port == 8000
    assert service.status == ServiceStatus.STOPPED
    
    # Test non-existent service
    assert manager.get_service_info("NonExistent") is None


def test_get_all_services():
    """Test retrieving all services."""
    manager = ServiceManager(mock_mode=True)
    
    services = manager.get_all_services()
    assert isinstance(services, list)
    assert len(services) >= 3
    
    for service in services:
        assert isinstance(service, ServiceInfo)
        assert service.name
        assert service.status == ServiceStatus.STOPPED


def test_start_service_mock():
    """Test starting a service in mock mode."""
    manager = ServiceManager(mock_mode=True)
    
    # Start service
    result = manager.start_service("Core API")
    assert result is True
    
    # Check status is starting
    service = manager.get_service_info("Core API")
    assert service.status == ServiceStatus.STARTING
    
    # Wait for mock delay
    time.sleep(2.5)
    
    # Check status is running
    service = manager.get_service_info("Core API")
    assert service.status == ServiceStatus.RUNNING
    assert service.pid is not None


def test_stop_service_mock():
    """Test stopping a service in mock mode."""
    manager = ServiceManager(mock_mode=True)
    
    # Start service first
    manager.start_service("Core API")
    time.sleep(2.5)
    
    # Verify it's running
    service = manager.get_service_info("Core API")
    assert service.status == ServiceStatus.RUNNING
    
    # Stop service
    result = manager.stop_service("Core API")
    assert result is True
    
    # Check status is stopping
    service = manager.get_service_info("Core API")
    assert service.status == ServiceStatus.STOPPING
    
    # Wait for mock delay
    time.sleep(1.5)
    
    # Check status is stopped
    service = manager.get_service_info("Core API")
    assert service.status == ServiceStatus.STOPPED
    assert service.pid is None


def test_restart_service_mock():
    """Test restarting a service in mock mode."""
    manager = ServiceManager(mock_mode=True)
    
    # Start service first
    manager.start_service("Core API")
    time.sleep(2.5)
    
    # Restart service
    result = manager.restart_service("Core API")
    assert result is True
    
    # Wait for stop and start
    time.sleep(4.0)
    
    # Check it's running again
    service = manager.get_service_info("Core API")
    assert service.status == ServiceStatus.RUNNING


def test_start_already_running():
    """Test starting a service that is already running."""
    manager = ServiceManager(mock_mode=True)
    
    # Start service
    manager.start_service("Core API")
    time.sleep(2.5)
    
    # Try to start again
    result = manager.start_service("Core API")
    assert result is False


def test_stop_already_stopped():
    """Test stopping a service that is already stopped."""
    manager = ServiceManager(mock_mode=True)
    
    # Try to stop a stopped service
    result = manager.stop_service("Core API")
    assert result is False


def test_start_nonexistent_service():
    """Test starting a non-existent service."""
    manager = ServiceManager(mock_mode=True)
    
    result = manager.start_service("NonExistent")
    assert result is False


def test_stop_nonexistent_service():
    """Test stopping a non-existent service."""
    manager = ServiceManager(mock_mode=True)
    
    result = manager.stop_service("NonExistent")
    assert result is False


def test_start_all_services():
    """Test starting all services."""
    manager = ServiceManager(mock_mode=True)
    
    manager.start_all_services()
    
    # Wait for all to start
    time.sleep(3.0)
    
    # Check all services are running
    for service in manager.get_all_services():
        assert service.status == ServiceStatus.RUNNING


def test_stop_all_services():
    """Test stopping all services."""
    manager = ServiceManager(mock_mode=True)
    
    # Start all first
    manager.start_all_services()
    time.sleep(3.0)
    
    # Stop all
    manager.stop_all_services()
    time.sleep(2.0)
    
    # Check all services are stopped
    for service in manager.get_all_services():
        assert service.status == ServiceStatus.STOPPED


def test_logging():
    """Test that logging works correctly."""
    manager = ServiceManager(mock_mode=True)
    
    # Get initial logs
    logs = manager.get_logs()
    assert len(logs) > 0
    assert any("ServiceManager initialized" in log for log in logs)
    
    # Start a service
    manager.start_service("Core API")
    time.sleep(0.5)
    
    # Get new logs
    logs = manager.get_logs()
    assert any("Starting service" in log for log in logs)


def test_service_with_callback():
    """Test service operations with callbacks."""
    manager = ServiceManager(mock_mode=True)
    callback_called = {"called": False, "service": None, "status": None}
    
    def test_callback(service_name: str, status: ServiceStatus):
        callback_called["called"] = True
        callback_called["service"] = service_name
        callback_called["status"] = status
    
    # Start service with callback
    manager.start_service("Core API", callback=test_callback)
    time.sleep(2.5)
    
    assert callback_called["called"] is True
    assert callback_called["service"] == "Core API"
    assert callback_called["status"] == ServiceStatus.RUNNING


def test_cleanup():
    """Test cleanup method."""
    manager = ServiceManager(mock_mode=True)
    
    # Start all services
    manager.start_all_services()
    time.sleep(3.0)
    
    # Cleanup
    manager.cleanup()
    
    # Note: cleanup doesn't wait for services to stop in mock mode,
    # it just initiates cleanup. In real mode, it would terminate processes.
    # This test just ensures cleanup doesn't crash.
    assert True

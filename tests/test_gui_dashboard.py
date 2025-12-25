"""
Tests for the GUI Dashboard (Control Panel)
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gui_dashboard import app


@pytest.fixture
def client():
    """Create a test client for the GUI dashboard."""
    return TestClient(app)


def test_homepage_loads(client):
    """Test that the homepage loads successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert "SMO Control Panel" in response.text
    assert "System Monitoring & Orchestration" in response.text


def test_api_status_endpoint(client):
    """Test the status API endpoint."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "agent" in data
    assert "web" in data
    assert isinstance(data["agent"], bool)
    assert isinstance(data["web"], bool)


def test_api_metrics_endpoint(client):
    """Test the metrics API endpoint."""
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "memory" in data
    assert "disk" in data
    assert "network_mb" in data
    assert isinstance(data["cpu"], (int, float))
    assert isinstance(data["memory"], (int, float))


def test_api_logs_endpoint(client):
    """Test the logs API endpoint."""
    response = client.get("/api/logs")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert isinstance(data["entries"], list)


def test_api_config_get(client):
    """Test getting configuration."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "config" in data
    assert isinstance(data["config"], str)


def test_api_config_update_invalid_yaml(client):
    """Test updating configuration with invalid YAML."""
    response = client.post("/api/config", json={"config": "invalid: yaml: content:"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"


def test_homepage_contains_service_controls(client):
    """Test that homepage contains service control elements."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    
    # Check for service sections
    assert "SMO Agent" in html
    assert "Main Dashboard" in html
    
    # Check for control buttons
    assert "Start" in html
    assert "Stop" in html
    assert "Start All" in html
    assert "Stop All" in html


def test_homepage_contains_metrics_section(client):
    """Test that homepage contains metrics display."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    
    # Check for metrics labels
    assert "CPU Usage" in html
    assert "Memory Usage" in html
    assert "Disk Usage" in html
    assert "Network I/O" in html


def test_homepage_contains_tabs(client):
    """Test that homepage contains tab sections."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    
    # Check for tab buttons
    assert "Logs" in html
    assert "Configuration" in html

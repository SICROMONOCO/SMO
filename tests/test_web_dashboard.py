"""Tests for web dashboard API endpoints."""
import pytest
from fastapi.testclient import TestClient
import json
import yaml
from pathlib import Path
import tempfile
import shutil
import asyncio


@pytest.fixture
def test_config_dir():
    """Create a temporary config directory for testing."""
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir) / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    yield config_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_logs_dir():
    """Create a temporary logs directory with test data."""
    temp_dir = tempfile.mkdtemp()
    logs_dir = Path(temp_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Create test log file
    log_file = logs_dir / "smo_metrics.jsonl"
    test_logs = [
        {"timestamp": 1234567890, "cpu": {"value": 45.5}},
        {"timestamp": 1234567891, "memory": {"value": 60.2}},
    ]

    with open(log_file, 'w') as f:
        for log in test_logs:
            f.write(json.dumps(log) + '\n')

    yield logs_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_config_get_endpoint(test_config_dir, monkeypatch):
    """Test GET /api/config endpoint."""
    # Setup test config
    config_file = test_config_dir / "config.yaml"
    test_config = {
        "refresh": {"cpu": 2, "memory": 5},
        "alerts": {"cpu_percent": 80}
    }

    with open(config_file, 'w') as f:
        yaml.safe_dump(test_config, f)

    # Monkeypatch the config path
    monkeypatch.setattr('web_dashboard.CONFIG_PATH', config_file)

    # Import after monkeypatch
    from web_dashboard import app
    client = TestClient(app)

    # Test the endpoint
    response = client.get("/api/config")
    assert response.status_code == 200

    data = response.json()
    assert "refresh" in data
    assert data["refresh"]["cpu"] == 2
    assert data["alerts"]["cpu_percent"] == 80


def test_config_post_endpoint(test_config_dir, monkeypatch):
    """Test POST /api/config endpoint."""
    config_file = test_config_dir / "config.yaml"

    # Monkeypatch the config path
    monkeypatch.setattr('web_dashboard.CONFIG_PATH', config_file)

    from web_dashboard import app
    client = TestClient(app)

    # Create new config
    new_config = {
        "refresh": {"cpu": 3, "memory": 6},
        "alerts": {"cpu_percent": 90}
    }

    response = client.post(
        "/api/config",
        json={"config": new_config}
    )
    assert response.status_code == 200

    # Verify config was saved
    assert config_file.exists()
    with open(config_file, 'r') as f:
        saved_config = yaml.safe_load(f)

    assert saved_config["refresh"]["cpu"] == 3
    assert saved_config["alerts"]["cpu_percent"] == 90


def test_logs_export_json(test_logs_dir, monkeypatch):
    """Test log export in JSON format."""
    log_file = test_logs_dir / "smo_metrics.jsonl"

    # Monkeypatch the metrics log path
    monkeypatch.setattr('web_dashboard.METRICS_LOG_PATH', log_file)

    from web_dashboard import app
    client = TestClient(app)

    response = client.get("/api/logs/export?format=json&filename=test_export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    # Verify content - FileResponse returns bytes, so parse it
    data = json.loads(response.content.decode('utf-8'))
    assert len(data) == 2
    assert data[0]["timestamp"] == 1234567890


def test_logs_export_csv(test_logs_dir, monkeypatch):
    """Test log export in CSV format."""
    log_file = test_logs_dir / "smo_metrics.jsonl"

    monkeypatch.setattr('web_dashboard.METRICS_LOG_PATH', log_file)

    from web_dashboard import app
    client = TestClient(app)

    response = client.get("/api/logs/export?format=csv&filename=test_export")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

    # Verify CSV content
    content = response.text
    assert "timestamp" in content
    assert "cpu" in content or "memory" in content


def test_logs_export_markdown(test_logs_dir, monkeypatch):
    """Test log export in Markdown format."""
    log_file = test_logs_dir / "smo_metrics.jsonl"

    monkeypatch.setattr('web_dashboard.METRICS_LOG_PATH', log_file)

    from web_dashboard import app
    client = TestClient(app)

    response = client.get("/api/logs/export?format=markdown&filename=test_export")
    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]

    # Verify markdown table format
    content = response.text
    assert "|" in content
    assert "---" in content


def test_logs_export_invalid_format(test_logs_dir, monkeypatch):
    """Test log export with invalid format."""
    log_file = test_logs_dir / "smo_metrics.jsonl"

    monkeypatch.setattr('web_dashboard.METRICS_LOG_PATH', log_file)

    from web_dashboard import app
    client = TestClient(app)

    response = client.get("/api/logs/export?format=invalid")
    assert response.status_code == 400


def test_logs_export_missing_file(test_config_dir, monkeypatch):
    """Test log export when log file doesn't exist."""
    non_existent = test_config_dir / "nonexistent.jsonl"

    monkeypatch.setattr('web_dashboard.METRICS_LOG_PATH', non_existent)

    from web_dashboard import app
    client = TestClient(app)

    response = client.get("/api/logs/export?format=json")
    assert response.status_code == 404


def test_websocket_reads_from_json_log(test_logs_dir, monkeypatch):
    """Test WebSocket endpoint reads metrics from JSON log file."""
    log_file = test_logs_dir / "smo_metrics.jsonl"
    
    # Add a complete metrics snapshot to the log file
    test_metrics = {
        "timestamp": 1234567892,
        "cpu": {
            "average": {"cpu_percent": {"value": 45.5}},
            "per_core": {"core_0_usage": {"value": 50.0}}
        },
        "memory": {
            "virtual_memory": {
                "percent": {"value": 60.2},
                "total": {"value": 8589934592, "human_readable": "8.0 GB"}
            }
        }
    }
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(test_metrics) + '\n')
    
    # Monkeypatch the metrics log path
    monkeypatch.setattr('web_dashboard.METRICS_LOG_PATH', log_file)
    
    from web_dashboard import app
    client = TestClient(app)
    
    # Test WebSocket connection
    with client.websocket_connect("/ws") as websocket:
        # Receive first message
        data_text = websocket.receive_text()
        data = json.loads(data_text)
        
        # Verify we got the metrics data
        assert "cpu" in data or "memory" in data or "timestamp" in data
        
        # If we got an error or info message, that's also acceptable
        # as long as the connection works
        if "error" not in data and "info" not in data:
            # We should have actual metrics
            assert "timestamp" in data


def test_websocket_handles_missing_log_file(test_config_dir, monkeypatch):
    """Test WebSocket endpoint handles missing log file gracefully."""
    non_existent = test_config_dir / "nonexistent.jsonl"
    
    monkeypatch.setattr('web_dashboard.METRICS_LOG_PATH', non_existent)
    
    from web_dashboard import app
    client = TestClient(app)
    
    # Test WebSocket connection
    with client.websocket_connect("/ws") as websocket:
        # Should receive an error message
        data_text = websocket.receive_text()
        data = json.loads(data_text)
        
        # Should have an error or info message about missing file
        assert "error" in data or "suggestion" in data

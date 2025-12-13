"""Tests for logger functionality."""
import time
import json
import os
from logger import MetricsLogger


def test_logger_writes_jsonl():
    """Test that logger writes JSONL format correctly."""
    test_file = '/tmp/test_logger_jsonl.jsonl'
    if os.path.exists(test_file):
        os.remove(test_file)
    
    logger = MetricsLogger(test_file)

    # Test data
    test_snapshot = {
        'timestamp': time.time(),
        'process': {
            'type': 'dynamic',
            'pid': 12345,
            'uptime': {
                'value': 100.5,
                'unit': 'seconds'
            }
        }
    }

    # Log the snapshot
    logger.log(test_snapshot)
    
    # Verify file exists and contains data
    assert os.path.exists(test_file)
    
    with open(test_file, 'r') as f:
        line = f.readline()
        data = json.loads(line)
        assert 'timestamp' in data
        assert 'process' in data
        assert data['process']['pid'] == 12345


def test_logger_csv_export():
    """Test that CSV export works correctly."""
    test_file = '/tmp/test_logger_csv.jsonl'
    if os.path.exists(test_file):
        os.remove(test_file)
    
    logger = MetricsLogger(test_file)

    test_data = {
        'timestamp': time.time(),
        'cpu': {
            'average': {
                'cpu_percent': {
                    'value': 45.7
                }
            }
        }
    }

    logger.log(test_data)
    csv_output = logger.transform_to_csv(test_data)
    
    assert csv_output
    assert 'timestamp' in csv_output
    assert 'cpu' in csv_output


def test_logger_handles_alerts():
    """Test that logger properly handles alert-only snapshots."""
    test_file = '/tmp/test_logger_alerts.jsonl'
    if os.path.exists(test_file):
        os.remove(test_file)
    
    logger = MetricsLogger(test_file)

    # Alert-only snapshot should be ignored
    alert_snapshot = {
        'alert': 'test alert'
    }
    
    logger.log(alert_snapshot)
    
    # File should either not exist or be empty
    if os.path.exists(test_file):
        with open(test_file, 'r') as f:
            content = f.read()
            assert content == ''

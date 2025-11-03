"""Tests for logger type preservation to fix InfluxDB type conflicts."""
import time
from logger import MetricsLogger


def test_integer_type_preservation():
    """Test that integer fields like pid are preserved as integers."""
    logger = MetricsLogger('/tmp/test_logger.jsonl')
    # Disable InfluxDB for this test
    logger.influx_client = None

    # Test data with pid as integer
    test_snapshot = {
        'timestamp': time.time(),
        'process': {
            'type': 'dynamic',
            'pid': 12345,  # Integer - should stay integer
            'uptime': {
                'value': 100.5,  # Float - should stay float
                'unit': 'seconds'
            },
            'cpu': {
                'value': 25,  # Integer - should stay integer
                'unit': 'percent'
            }
        }
    }

    # Extract fields
    fields = list(logger._iter_numeric_fields(test_snapshot['process']))
    field_dict = dict(fields)

    # Verify types are preserved
    assert 'pid' in field_dict
    assert isinstance(field_dict['pid'], int), f"pid should be int, got {type(field_dict['pid']).__name__}"
    assert field_dict['pid'] == 12345

    assert 'uptime' in field_dict
    assert isinstance(field_dict['uptime'], float), f"uptime should be float, got {type(field_dict['uptime']).__name__}"
    assert field_dict['uptime'] == 100.5

    assert 'cpu' in field_dict
    assert isinstance(field_dict['cpu'], int), f"cpu should be int, got {type(field_dict['cpu']).__name__}"
    assert field_dict['cpu'] == 25


def test_float_type_preservation():
    """Test that float fields remain as floats."""
    logger = MetricsLogger('/tmp/test_logger.jsonl')
    logger.influx_client = None

    test_data = {
        'cpu': {
            'average': {
                'cpu_percent': {
                    'value': 45.7
                }
            }
        }
    }

    fields = list(logger._iter_numeric_fields(test_data['cpu']))
    field_dict = dict(fields)

    assert 'average_cpu_percent' in field_dict
    assert isinstance(field_dict['average_cpu_percent'], float)
    assert field_dict['average_cpu_percent'] == 45.7


def test_nested_value_extraction():
    """Test that nested values are correctly extracted with proper types."""
    logger = MetricsLogger('/tmp/test_logger.jsonl')
    logger.influx_client = None

    test_data = {
        'memory': {
            'virtual_memory': {
                'total': {
                    'value': 17179869184  # Large integer
                },
                'percent': {
                    'value': 85.3  # Float
                }
            }
        }
    }

    fields = list(logger._iter_numeric_fields(test_data['memory']))
    field_dict = dict(fields)

    # Check both fields exist and have correct types
    assert 'virtual_memory_total' in field_dict
    assert isinstance(field_dict['virtual_memory_total'], int)

    assert 'virtual_memory_percent' in field_dict
    assert isinstance(field_dict['virtual_memory_percent'], float)

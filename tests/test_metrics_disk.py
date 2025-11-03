import pytest
from metrics import disks as disk

def test_disk_metrics_structure():
    """Test the basic structure of disk metrics."""
    data = disk.get_disk_metrics()
    assert isinstance(data, dict), "Disk metrics should return a dictionary"

    # Test io counters structure
    if "io_counters" in data:
        assert isinstance(data["io_counters"], dict)
        assert "description" in data["io_counters"]
        assert "metrics" in data["io_counters"]

    # Test per-disk io counters
    if "io_counters_perdisk" in data:
        assert isinstance(data["io_counters_perdisk"], dict)
        assert "description" in data["io_counters_perdisk"]
        assert "metrics" in data["io_counters_perdisk"]

def test_disk_metrics_values():
    """Test that disk metrics contain valid values."""
    data = disk.get_disk_metrics()

    # Test disk partitions
    for key, partition_data in data.items():
        if isinstance(partition_data, dict) and "metrics" in partition_data:
            metrics = partition_data["metrics"]
            if "usage_percent" in metrics:
                assert isinstance(metrics["usage_percent"]["value"], (int, float))
                assert 0 <= metrics["usage_percent"]["value"] <= 100

            if "total_bytes" in metrics:
                assert isinstance(metrics["total_bytes"]["value"], int)
                assert metrics["total_bytes"]["value"] >= 0

def test_disk_metrics_helper_functions():
    """Test disk metrics helper functions."""
    # Test sanitize_key function
    assert disk.sanitize_key("test/path") == "test_path"
    assert disk.sanitize_key("C:\\Windows") == "C_Windows"
    assert disk.sanitize_key("multi  spaces") == "multi_spaces"

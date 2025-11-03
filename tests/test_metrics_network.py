import pytest
from metrics import networks as network

def test_network_metrics_structure():
    """Test the basic structure of network metrics."""
    data = network.get_network_metrics()
    assert isinstance(data, dict), "Network metrics should return a dictionary"

    # Test io counters structure
    if "io_counters" in data:
        assert isinstance(data["io_counters"], dict)
        assert "description" in data["io_counters"]
        assert "metrics" in data["io_counters"]

    # Test per-interface io counters
    if "io_counters_pernic" in data:
        assert isinstance(data["io_counters_pernic"], dict)
        assert "description" in data["io_counters_pernic"]
        assert "metrics" in data["io_counters_pernic"]

def test_network_interface_metrics():
    """Test network interface metrics."""
    data = network.get_network_metrics()

    # Test interfaces structure
    if "interfaces" in data:
        assert isinstance(data["interfaces"], dict)
        assert "description" in data["interfaces"]
        assert "interfaces" in data["interfaces"]

        # Test interface addresses
        for iface_name, iface_data in data["interfaces"]["interfaces"].items():
            assert "description" in iface_data
            assert "addresses" in iface_data
            assert isinstance(iface_data["addresses"], list)

            # Test address structure if any addresses exist
            if iface_data["addresses"]:
                addr = iface_data["addresses"][0]
                assert "family" in addr
                assert "address" in addr

def test_network_stats():
    """Test network interface statistics."""
    data = network.get_network_metrics()

    # Test stats structure
    if "stats" in data:
        assert isinstance(data["stats"], dict)
        assert "description" in data["stats"]
        assert "interfaces" in data["stats"]

        # Test interface stats
        for iface_name, iface_data in data["stats"]["interfaces"].items():
            assert "description" in iface_data
            assert "metrics" in iface_data
            metrics = iface_data["metrics"]

            # Test specific metrics
            if "isup" in metrics:
                assert isinstance(metrics["isup"]["value"], bool)
            if "speed" in metrics:
                assert isinstance(metrics["speed"]["value"], (int, float, type(None)))

from metrics import registry

def test_registry_gather_all():
    data = registry.gather_all()
    assert isinstance(data, dict)
    assert "cpu" in data
    assert "memory" in data
    assert "disk" in data
    assert "network" in data

def test_registry_timestamp():
    data = registry.gather_all()
    assert "timestamp" in data
    assert isinstance(data["timestamp"], float)

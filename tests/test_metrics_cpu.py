import pytest
from metrics import cpu

def test_cpu_percent_structure():
    data = cpu.get_cpu_metrics()
    assert "average" in data
    assert "cpu_percent" in data["average"]
    assert isinstance(data["average"]["cpu_percent"]["value"], (int, float))

def test_cpu_count():
    data = cpu.get_cpu_metrics()
    assert "count" in data
    assert isinstance(data["count"]["count"]["value"]["logical"], int)
    assert data["count"]["count"]["value"]["logical"] >= 1

def test_cpu_freq():
    data = cpu.get_cpu_metrics()
    assert "frequency" in data
    assert "current_freq" in data["frequency"]

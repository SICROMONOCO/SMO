from metrics import memory

def test_memory_virtual():
    data = memory.get_memory_metrics()
    assert "virtual_memory" in data
    assert "percent" in data["virtual_memory"]
    assert isinstance(data["virtual_memory"]["percent"]["value"], (int, float))

def test_memory_swap():
    data = memory.get_memory_metrics()
    assert "swap_memory" in data
    assert "used" in data["swap_memory"]

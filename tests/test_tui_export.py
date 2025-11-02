"""Tests for TUI export functionality."""
import json
import tempfile
from pathlib import Path


def test_path_expansion():
    """Test that various path formats are handled correctly."""
    # Test relative path
    relative_path = Path("logs/export.json")
    expanded = relative_path.expanduser().resolve()
    assert expanded.is_absolute()
    
    # Test absolute path
    absolute_path = Path("/tmp/export.json")
    expanded = absolute_path.expanduser().resolve()
    assert expanded.is_absolute()
    assert str(expanded) == "/tmp/export.json"
    
    # Test user path expansion
    user_path = Path("~/logs/export.json")
    expanded = user_path.expanduser().resolve()
    assert expanded.is_absolute()
    assert "~" not in str(expanded)


def test_export_path_creation():
    """Test that export paths are created correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test creating nested directories
        export_path = Path(tmpdir) / "nested" / "path" / "export.json"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write test data
        test_data = [{"metric": "cpu", "value": 50}]
        with open(export_path, "w") as f:
            json.dump(test_data, f)
        
        # Verify file was created
        assert export_path.exists()
        
        # Verify content
        with open(export_path, "r") as f:
            data = json.load(f)
        assert data == test_data

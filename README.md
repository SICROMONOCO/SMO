# 🚀 System Monitoring and Orchestration Tool (SMO)

<div align="center">

**A lightweight, modern system monitoring solution with real-time metrics, interactive TUI, and web-based dashboards.**

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

## 📋 Overview

SMO is a comprehensive system monitoring tool designed for DevOps engineers, system administrators, and developers who need lightweight, real-time visibility into system performance. Unlike heavyweight monitoring solutions, SMO requires no external databases or complex infrastructure—just Python and your terminal.

**Key Highlights:**
- ⚡ Zero external dependencies (database-free architecture)
- 📊 Real-time metrics collection and visualization
- 🎯 Dual interface options (Terminal TUI + Web Dashboard)
- 🔧 Highly configurable alerting system
- 📁 Simple file-based logging (JSONL format)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Real-time Metrics** | CPU, Memory, Disk, Network, and Process monitoring with live updates |
| **Interactive TUI** | Beautiful terminal-based dashboard with intuitive navigation |
| **Web Dashboard** | Modern browser interface with charts, graphs, and WebSocket integration |
| **Smart Alerts** | Configurable thresholds with customizable notifications |
| **File-Based Logging** | JSONL format for easy parsing, analysis, and integration |
| **Lightweight** | Minimal resource consumption, no database required |
| **Extensible** | Plugin-style architecture for custom metrics |

---

## 📦 Prerequisites

Before you begin, ensure you have:

- **Python 3.8 or higher** — [Download here](https://www.python.org/downloads/)
- **pip** — Included with Python 3.4+
- **Terminal** — bash, zsh, or compatible shell
- **~50MB disk space** — For logs and dependencies

---

## 🔧 Installation & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/SICROMONOCO/SMO.git
cd SMO
```

### Step 2: Create a Virtual Environment

Using a virtual environment isolates dependencies and prevents conflicts:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**What gets installed:**
- `psutil` — System and process utilities
- `rich` — Terminal formatting and TUI components
- `pyyaml` — Configuration file parsing
- `fastapi` & `uvicorn` — Web dashboard server
- `pytest` — Testing framework

---

## 🎯 Quick Start

SMO uses a **split architecture**: the Agent collects metrics in the background, while the TUI/Dashboard displays them. Both must run simultaneously for live data.

### Terminal 1: Start the Agent

```bash
source venv/bin/activate
python3 agent.py run
```

The agent silently collects metrics and writes to `logs/smo_metrics.jsonl`.

### Terminal 2: Launch the Dashboard

**Option A: Terminal UI (TUI)**

```bash
source venv/bin/activate
python3 -m tui.tui_dashboard
```

**Option B: Web Dashboard**

```bash
source venv/bin/activate
python3 -m uvicorn web_dashboard:app --host 0.0.0.0 --port 5000
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 📖 Usage Guide

### Agent Commands

The agent supports multiple modes:

```bash
# Continuous monitoring (background collection)
python3 agent.py run

# Single snapshot with output to console
python3 agent.py once

# Continuous with console output
python3 agent.py run --print

# View collected logs
python3 agent.py logs

# Launch TUI directly
python3 agent.py tui
```

### Dashboard Options

#### Terminal UI (TUI)

**Features:**
- Real-time metric visualization
- Multi-tab interface ("Live View", "Config Editor", "Logs Exporter")
- Keyboard navigation (arrow keys, enter)
- Resource-efficient rendering

**Keyboard Shortcuts:**
| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate between tabs |
| `←` / `→` | Switch specific tabs |
| `q` / `Ctrl+C` | Quit application |
| `Enter` | Expand/collapse sections |

#### Web Dashboard

**Features:**
- Live metrics via WebSocket connection
- Interactive configuration editor
- Export functionality (JSON, CSV, Markdown)
- Responsive design for mobile and desktop
- Visual charts and performance graphs

**Access:** [http://localhost:5000](http://localhost:5000)

---

## 🛠️ Configuration

Configure SMO by editing `config/config.yaml`:

```yaml
# Metric collection intervals (seconds)
refresh:
  cpu: 2              # CPU metrics every 2 seconds
  memory: 5           # Memory metrics every 5 seconds
  disk: 10            # Disk metrics every 10 seconds
  network: 5          # Network metrics every 5 seconds
  process: 2          # Process metrics every 2 seconds

# Alert thresholds (percentage or bytes)
alerts:
  cpu_percent: 80         # Alert if CPU > 80%
  memory_percent: 85      # Alert if memory > 85%
  disk_usage: 90          # Alert if disk > 90%
  network_bytes_sent: 1000000  # Alert if network > 1MB/s

# Agent settings
agent:
  snapshot_interval: 2    # Collect snapshot every 2 seconds

# Logging configuration
logging:
  format: json            # JSONL format for easy parsing

# Display preferences
display:
  show_snapshot_info: true
  pretty_max_depth: 2
  pretty_max_length: 1200
```

> **💡 Tip:** Changes to `config.yaml` are applied on next snapshot collection. No restart required!

---

## 📁 Project Structure

<details open>
<summary><b>Click to expand directory tree</b></summary>

```
SMO/
├── 📄 agent.py                  # Main agent runtime controller
├── 📄 app.py                    # TUI entry point
├── 📄 web_dashboard.py          # Web dashboard FastAPI server
├── 📄 logger.py                 # Metrics logging utilities
├── 📄 alerts.py                 # Alert processing engine
├── 📄 updater.py                # Threaded metrics updater
├── 📄 config_loader.py          # Configuration file parser
├── 📄 requirements.txt           # Python dependencies
├── 📁 config/
│   ├── 📄 config.yaml           # Main configuration file
│   └── 📄 config.yaml.bak       # Backup configuration
├── 📁 metrics/                  # Metrics collection modules
│   ├── 📄 registry.py           # Metrics registry
│   ├── 📄 cpu.py                # CPU metrics collector
│   ├── 📄 memory.py             # Memory metrics collector
│   ├── 📄 disk.py               # Disk metrics collector
│   ├── 📄 network.py            # Network metrics collector
│   └── 📄 process.py            # Process metrics collector
├── 📁 tui/                      # Terminal UI components
│   ├── 📄 tui_dashboard.py      # Main TUI dashboard
│   └── 📁 widgets/
│       ├── 📄 cpu_stats.py      # CPU widget component
│       ├── 📄 memory.py         # Memory widget component
│       ├── 📄 disk.py           # Disk widget component
│       ├── 📄 network.py        # Network widget component
│       ├── 📄 process.py        # Process widget component
│       ├── 📄 alerts.py         # Alerts widget component
│       ├── 📄 system_info.py    # System info widget
│       ├── 📄 metric_group.py   # Metric group container
│       └── 📄 __init__.py       # Widget package init
├── 📁 logs/                     # Auto-generated metric logs
│   └── 📄 smo_metrics.jsonl     # Collected metrics (JSONL)
├── 📁 tests/                    # Test suite
│   ├── 📄 test_metrics_cpu.py
│   ├── 📄 test_metrics_disk.py
│   ├── 📄 test_metrics_memory.py
│   ├── 📄 test_metrics_network.py
│   ├── 📄 test_registry.py
│   ├── 📄 test_web_dashboard.py
│   ├── 📄 test_tui_export.py
│   └── 📄 test_tui_widgets.py
├── 📁 remote_ssh/               # Remote access utilities
│   ├── 📄 ssh_manage.sh         # SSH management script
│    📄 ssh_test.sh           # SSH testing script
└──📄 README.md                 # This file

```

</details>

### Directory Descriptions

| Directory | Purpose |
|-----------|---------|
| `metrics/` | Modular collectors for each metric type; easily extensible |
| `tui/` | Rich terminal UI components using the Rich library |
| `config/` | YAML-based configuration with validation |
| `logs/` | JSONL output directory (auto-created) |
| `tests/` | Comprehensive pytest suite for all components |
| `remote_ssh/` | Tools for remote system monitoring over SSH |

---

## 📊 Log Format

Metrics are stored in **JSONL (JSON Lines)** format—one valid JSON object per line:

```json
{
  "timestamp": 1702497234.567,
  "cpu": {
    "average": {"cpu_percent": {"value": 45.2, "unit": "%"}},
    "per_core": {
      "core_0": {"cpu_percent": {"value": 40.1, "unit": "%"}},
      "core_1": {"cpu_percent": {"value": 50.3, "unit": "%"}}
    }
  },
  "memory": {
    "used": {"value": 8192, "unit": "MB"},
    "available": {"value": 16384, "unit": "MB"},
    "percent": {"value": 33.3, "unit": "%"}
  },
  "disk": {
    "/": {"used": {"value": 256, "unit": "GB"}, "percent": {"value": 50.0, "unit": "%"}}
  },
  "network": {
    "bytes_sent": {"value": 1024000, "unit": "bytes"},
    "bytes_recv": {"value": 2048000, "unit": "bytes"}
  },
  "process": {
    "top_processes": [
      {"pid": 1234, "name": "python", "memory_percent": 5.2, "cpu_percent": 2.1}
    ]
  }
}
```

**Why JSONL?**
- ✅ Human-readable but machine-parseable
- ✅ Easy to stream and process with standard tools
- ✅ Works with pandas, jq, and other data tools
- ✅ Simple to query and analyze

---

## 🧪 Testing

The project includes comprehensive tests for all components:

### Run All Tests

```bash
python3 -m pytest
```

### Run Specific Test Files

```bash
# Test metric collectors
python3 -m pytest tests/test_metrics_cpu.py
python3 -m pytest tests/test_metrics_disk.py

# Test web dashboard
python3 -m pytest tests/test_web_dashboard.py

# Test TUI components
python3 -m pytest tests/test_tui_widgets.py
```

### Run with Coverage

```bash
python3 -m pytest --cov=. --cov-report=html
```

### Test Configuration

Tests are configured in `tests/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### Development Setup

```bash
# Clone and setup
git clone https://github.com/SICROMONOCO/SMO.git
cd SMO
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create a feature branch
git checkout -b feature/your-feature-name
```

### Guidelines

- **Code Style:** Follow PEP 8 using `black` or `autopep8`
- **Testing:** All new features must include tests
- **Documentation:** Update README and docstrings for changes
- **Commits:** Use clear, descriptive commit messages
- **Pull Requests:** Include a detailed description of changes

### Areas for Contribution

- 🎯 New metric types (GPU, sensors, custom metrics)
- 🎨 UI/UX improvements for TUI and web dashboard
- 📚 Documentation and tutorials
- 🐛 Bug fixes and performance improvements
- 🧪 Additional test coverage

### Reporting Issues

Found a bug? [Open an issue](https://github.com/SICROMONOCO/SMO/issues) with:
- Clear title and description
- Steps to reproduce
- Expected vs. actual behavior
- Your environment (Python version, OS, etc.)

---

## 📝 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

**You are free to:**
- ✅ Use this software for commercial and private purposes
- ✅ Modify and distribute it
- ✅ Include it in your projects

**You must:**
- ✅ Include the original license and copyright notice
- ✅ Provide a copy of the license with distributions

---

## 🔗 Additional Resources

| Resource | Purpose |
|----------|---------|
| [USAGE.md](USAGE.md) | Detailed step-by-step usage instructions |
| [Issues](https://github.com/SICROMONOCO/SMO/issues) | Bug reports and feature requests |
| [Discussions](https://github.com/SICROMONOCO/SMO/discussions) | Community Q&A and ideas |

---

## 🙏 Acknowledgments

- **psutil** — Cross-platform system utilities
- **Rich** — Beautiful terminal formatting
- **FastAPI** — Modern async web framework
- **pytest** — Python testing framework

---

<div align="center">

**Made with ❤️ for system administrators and DevOps engineers**

[⭐ Star us on GitHub](https://github.com/SICROMONOCO/SMO) | [📧 Contact](mailto:sicro.monoco@gmail.com)

</div>

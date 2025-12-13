# System Monitoring and Orchestration Tool (SMO)

A lightweight, modern system monitoring tool with both a terminal-based TUI and a web dashboard.

## Features

- 📊 **Real-time Metrics**: CPU, Memory, Disk, Network, and Process monitoring
- 🖥️ **Interactive TUI**: Terminal-based dashboard with live updates
- 🌐 **Web Dashboard**: Browser-based interface with visual charts and graphs
- 📁 **File-Based Logging**: Simple JSONL format for easy processing
- 🔔 **Alerting System**: Configurable thresholds and notifications
- ⚡ **Lightweight**: No database dependencies, minimal overhead

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/SICROMONOCO/SMO.git
cd SMO
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Agent

Start the monitoring agent to collect metrics:

```bash
python3 agent.py run
```

The agent will continuously collect system metrics and log them to `logs/smo_metrics.jsonl`.

### Viewing Metrics

#### Terminal UI (TUI)

Launch the interactive terminal dashboard:

```bash
python3 agent.py tui
```

Or:

```bash
python3 app.py
```

The TUI provides real-time system metrics with an intuitive interface.

#### Web Dashboard

Start the web dashboard server:

```bash
python3 -m uvicorn web_dashboard:app --host 0.0.0.0 --port 5000
```

Then open your browser to: [http://localhost:5000](http://localhost:5000)

The web dashboard features:
- Live metrics via WebSocket
- Configuration editor
- Log export functionality (JSON, CSV, Markdown)

### Additional Commands

- **Single snapshot**: `python3 agent.py once`
- **View logs**: `python3 agent.py logs`
- **Print to console**: `python3 agent.py run --print`

## Configuration

Edit `config/config.yaml` to customize:
- Refresh intervals for each metric type
- Alert thresholds
- Display settings
- Logging format

Example configuration:
```yaml
refresh:
  cpu: 2
  memory: 5
  disk: 10
  network: 5
  process: 2

alerts:
  cpu_percent: 80
  memory_percent: 85
  disk_usage: 90
  network_bytes_sent: 1000000

agent:
  snapshot_interval: 2

logging:
  format: json

display:
  show_snapshot_info: true
  pretty_max_depth: 2
  pretty_max_length: 1200
```

## Project Structure

```
SMO/
├── agent.py              # Main agent runtime controller
├── app.py                # TUI entry point
├── web_dashboard.py      # Web dashboard server
├── logger.py             # Metrics logging utilities
├── alerts.py             # Alert processing
├── updater.py            # Threaded metrics updater
├── metrics/              # Metrics collectors
│   ├── registry.py       # Metrics registry
│   ├── cpu.py
│   ├── memory.py
│   ├── disk.py
│   ├── network.py
│   └── process.py
├── tui/                  # Terminal UI components
│   ├── tui_dashboard.py
│   └── widgets/
├── config/               # Configuration files
│   └── config.yaml
├── logs/                 # Metrics logs (auto-generated)
│   └── smo_metrics.jsonl
└── tests/                # Test suite
```

## Running Tests

Run the test suite:

```bash
python3 -m pytest
```

Run specific tests:

```bash
python3 -m pytest tests/test_metrics_cpu.py
python3 -m pytest tests/test_web_dashboard.py
```

## Log Format

Metrics are logged in JSONL (JSON Lines) format. Each line is a complete JSON object representing a snapshot:

```json
{
  "timestamp": 1702497234.567,
  "cpu": {
    "average": {"cpu_percent": {"value": 45.2, "unit": "%"}},
    "per_core": {...}
  },
  "memory": {...},
  "disk": {...},
  "network": {...},
  "system": {...},
  "process": {...}
}
```

## Documentation

- [USAGE.md](USAGE.md) - Detailed usage instructions and features

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

# SMO GUI Control Panel - Quick Start Guide

## Overview
The SMO GUI Control Panel provides an XAMPP-like web interface for managing the System Monitoring and Orchestration (SMO) tool. It offers a user-friendly way to start/stop services, monitor system metrics, view logs, and edit configuration - all from your browser.

## Quick Start

### 1. Prerequisites
Ensure you have installed the dependencies:
```bash
pip install -r requirements.txt
```

### 2. Launch the Control Panel

**Option A: Quick Launch (Recommended)**
```bash
python3 launch_gui.py
```
This will:
- Start the control panel server on port 8000
- Automatically open your default browser
- Display the control panel interface

**Option B: Manual Launch**
```bash
python3 gui_dashboard.py
```
Then manually open http://localhost:8000 in your browser.

## Features

### 1. Services Control Panel
Manage SMO services with visual controls:
- **SMO Agent**: Start/Stop the metrics collection agent
- **Main Dashboard**: Start/Stop the full-featured web dashboard (port 5000)
- **Status Indicators**: Real-time visual feedback (Running/Stopped)
- **Quick Actions**: Start All / Stop All buttons

### 2. System Metrics Display
View real-time system information:
- CPU Usage (percentage)
- Memory Usage (percentage)
- Disk Usage (percentage)
- Network I/O (total bytes sent)
- One-click refresh button

### 3. Log Viewer
Access application logs easily:
- View recent log entries (last 30)
- Formatted display with timestamps
- Shows CPU and Memory metrics from logs
- Refresh and Clear buttons

### 4. Configuration Editor
Edit SMO settings in the browser:
- YAML syntax highlighting
- Live configuration editing
- Validation on save
- Reload from file option
- Note: Changes require service restart to take effect

## Interface Layout

```
┌──────────────────────────────────────────────────────────┐
│               🚀 SMO Control Panel                       │
│        System Monitoring & Orchestration Dashboard       │
└──────────────────────────────────────────────────────────┘

┌────────────────────────┐  ┌────────────────────────────┐
│  📊 Services Control   │  │   📈 System Metrics        │
│                        │  │                            │
│  🤖 SMO Agent          │  │   CPU Usage:     2.5%      │
│  [Stopped]             │  │   Memory Usage:  13.1%     │
│  [▶️ Start] [⏹️ Stop] │  │   Disk Usage:    77.9%     │
│                        │  │   Network I/O:   67.55 MB  │
│  🌐 Main Dashboard     │  │                            │
│  [Stopped]             │  │   [🔄 Refresh Metrics]     │
│  [▶️ Start] [⏹️ Stop] │  │                            │
│  [🔗 Open]             │  └────────────────────────────┘
│                        │
│  [▶️ Start All]        │
│  [⏹️ Stop All]         │
└────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  [📝 Logs]  [⚙️ Configuration]                           │
│                                                          │
│  Log entries or Configuration editor shown here          │
└──────────────────────────────────────────────────────────┘
```

## Common Workflows

### Starting SMO for the First Time
1. Launch the GUI Control Panel: `python3 launch_gui.py`
2. Click "▶️ Start All" to start both Agent and Dashboard
3. Wait a few seconds for services to initialize
4. Click "🔗 Open" next to Main Dashboard to view full metrics
5. Click "🔄 Refresh Metrics" to see current system stats

### Viewing Logs
1. Open the control panel
2. Click the "📝 Logs" tab
3. Click "🔄 Refresh" to load recent logs
4. Review metric snapshots and timestamps

### Editing Configuration
1. Open the control panel
2. Click the "⚙️ Configuration" tab
3. Edit the YAML configuration
4. Click "💾 Save"
5. Stop and restart services for changes to take effect

### Stopping Services
1. Use individual "⏹️ Stop" buttons for specific services
2. Or click "⏹️ Stop All" to stop everything
3. Close the browser tab
4. Press Ctrl+C in terminal to stop the control panel

## Ports Used
- **8000**: GUI Control Panel (this interface)
- **5000**: Main Web Dashboard (full-featured monitoring)

## Tips
- The control panel automatically refreshes service status every 3 seconds
- Services can be started independently or all at once
- The agent must be running to collect metrics
- Configuration changes are validated for YAML syntax
- All services are gracefully stopped when closing the control panel

## Troubleshooting

### Control Panel Won't Start
- Check if port 8000 is already in use: `lsof -i :8000` (Linux/Mac)
- Ensure dependencies are installed: `pip install -r requirements.txt`

### Services Won't Start
- Check if ports 5000 is available for the main dashboard
- View the terminal output for error messages
- Check configuration file syntax in `config/config.yaml`

### Can't See Metrics
- Ensure the Agent service is started (green "Running" status)
- Click "🔄 Refresh Metrics" to update values
- Wait a few seconds after starting the agent

## Security Note
The control panel is designed for local use. When deploying to production:
- Change the host binding from `0.0.0.0` to `127.0.0.1` for localhost-only access
- Use a reverse proxy (nginx, Apache) for external access
- Implement authentication if exposing to network

## Support
For issues, feature requests, or contributions, visit:
https://github.com/SICROMONOCO/SMO

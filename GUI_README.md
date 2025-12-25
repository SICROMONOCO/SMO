# SMO Service Manager GUI

A professional PyQt6-based GUI application for managing local services, similar to XAMPP Control Panel.

## Features

- **Service Management**: Start, stop, and restart services with a single click
- **Real-time Status**: LED-style status indicators (green/red) showing service states
- **Process Monitoring**: View PID and port information for each service
- **Console Logs**: Real-time log panel showing service operations
- **Dark Mode**: Modern, professional dark theme interface
- **Mock Mode**: Test the GUI without running actual services

## Architecture

The application follows the **MVC (Model-View-Controller)** pattern:

- **Model**: `service_manager.py` - Backend logic for managing services
- **View**: `main.py` - PyQt6 GUI components
- **Config**: `config.py` - Configuration and styling

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the GUI

```bash
python main.py
```

### Mock Mode (Default)

By default, the application runs in **MOCK MODE** which simulates service operations without executing real commands. This is perfect for testing and development.

To change the mode, edit `config.py`:
```python
MOCK_MODE = False  # Set to False for real service management
```

### Managed Services

The GUI manages three services:

1. **Core API** (Port 8000) - Main API server
2. **Database** (Port 5432) - PostgreSQL database
3. **Background Worker** - Background task processor

### Features

- **Individual Control**: Each service has Start, Stop, and Restart buttons
- **Bulk Operations**: Use "Start All Services" or "Stop All Services" for batch operations
- **Status Monitoring**: Status updates every second with color-coded indicators:
  - 🟢 Green = Running
  - 🔴 Gray = Stopped
  - 🟡 Yellow = Starting
  - 🟠 Orange = Stopping
  - 🔴 Red = Error

## Configuration

Edit `config.py` to customize:

- **Services**: Add/remove services and configure ports
- **Mock Mode**: Toggle between mock and real mode
- **UI Settings**: Window size, update intervals, colors
- **Commands**: Customize start/stop commands for services

## Testing

Run the test suite:
```bash
pytest tests/test_service_manager.py -v
```

## Code Style

- **PEP 8** compliant
- **Type hints** throughout
- **Docstrings** for all classes and complex methods
- **Error handling** with try-except blocks

## Screenshots

The GUI provides a clean, professional interface with:
- Service table showing name, status, PID, port, description
- Action buttons for each service
- Collapsible log console
- Global control buttons

## Technical Details

- **Framework**: PyQt6
- **Threading**: Asynchronous service operations to prevent GUI freezing
- **Logging**: Queue-based logging system for thread-safe log display
- **Process Management**: Subprocess management with proper cleanup

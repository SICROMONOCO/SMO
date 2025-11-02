# System Monitoring and Orchestration Tool

This project is a comprehensive system monitoring tool with a Textual TUI, a web dashboard, and a remote monitoring agent.

## Installation Options

SMO can be deployed in two ways:

### 1. Docker Installation (Recommended for most users)

The entire application is containerized with Docker for easy deployment and development.

**Quick Start:**
```bash
./setup.sh
```

See [CONTAINERIZATION.md](CONTAINERIZATION.md) for details.

### 2. Standalone Installation (Direct host installation)

Install SMO and InfluxDB directly on your Linux system without Docker.

**Quick Start:**
```bash
sudo ./setup-standalone.sh
```

See [docs/STANDALONE_INSTALLATION.md](docs/STANDALONE_INSTALLATION.md) for details.

## Quick Start

### Easy Setup (Recommended)

Run the interactive setup script:

```bash
./setup.sh
```

The script will guide you through configuration and let you choose between:
- **Container Metrics Mode**: Monitor Docker containers (good for development)
- **Host Metrics Mode**: Monitor your actual Linux host machine (good for production)

### Manual Setup

See [CONTAINERIZATION.md](CONTAINERIZATION.md) for detailed containerization documentation.

## Features

- 📊 **Real-time Metrics**: CPU, Memory, Disk, Network, and Process monitoring
- 🖥️ **Interactive TUI**: Terminal-based dashboard with live updates
- 🌐 **Web Dashboard**: Browser-based interface with visual charts and graphs
- 💾 **InfluxDB Integration**: Time-series data storage and retrieval
- 🔔 **Alerting System**: Configurable thresholds and notifications
- 🐋 **Containerized**: Easy deployment with Docker Compose
- 🖧 **Host Monitoring**: Support for monitoring actual host machine metrics

## Prerequisites

Before using SMO, you need:

- **Docker Engine** (20.10.0 or later) - [Installation Guide](https://docs.docker.com/engine/install/)
- **Docker Compose** (v1.27.0+ or Docker Compose plugin v2.0.0+)
- **Linux** (for host metrics mode) or any OS with Docker support (for container metrics mode)

**Quick check:**
```bash
docker --version
docker compose version  # or: docker-compose --version
```

If Docker is not installed, see [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) for installation instructions or run the setup script which will provide guidance.

## Docker Compose Setup

The application is orchestrated using Docker Compose. The following services are defined:

| Service      | Description                                          |
|--------------|------------------------------------------------------|
| `smo-agent`  | The main monitoring agent that collects system metrics. |
| `smo-web`    | A FastAPI web dashboard with WebSockets for real-time metrics. |
| `smo-tui`    | A Textual-based TUI for interactive monitoring.       |
| `smo-db`     | An InfluxDB instance for storing metrics data.        |
| `smo-remote` | A minimal SSH server for testing remote monitoring.   |

### Prerequisites

- Docker
- Docker Compose
- Linux host (for host metrics mode)

### Running the Application

#### Container Metrics Mode (Default)

Monitors the Docker containers themselves:

```bash
# Copy environment template
cp .env.example .env

# Build and start
docker-compose up -d

# Run TUI
docker-compose run --rm smo-tui
```

**Access:**
- Web Dashboard: [http://localhost:5678](http://localhost:5678)
- InfluxDB UI: [http://localhost:8086](http://localhost:8086)

#### Host Metrics Mode (Linux Only)

Monitors your actual Linux host machine:

```bash
# Copy environment template
cp .env.example .env

# Build and start with host monitoring
docker-compose -f docker-compose.yml -f docker-compose.host.yml up -d

# Run TUI with host metrics
docker-compose -f docker-compose.yml -f docker-compose.host.yml run --rm smo-tui
```

**Access:**
- Web Dashboard: [http://localhost:5000](http://localhost:5000)
- InfluxDB UI: [http://localhost:8086](http://localhost:8086)

> **Note:** Host metrics mode requires privileged containers and is only available on Linux.

### Common Commands

**View logs:**
```bash
docker-compose logs -f
```

**Stop services:**
```bash
docker-compose down
```

**Restart services:**
```bash
docker-compose restart
```

## Documentation

- 📖 [CONTAINERIZATION.md](CONTAINERIZATION.md) - Docker containerization guide
- 🖥️ [STANDALONE_INSTALLATION.md](docs/STANDALONE_INSTALLATION.md) - Standalone (non-Docker) installation guide
- 📘 [USAGE.md](USAGE.md) - Application usage and features
- 🐳 [DOCKER_SETUP.md](docs/DOCKER_SETUP.md) - Docker installation guide
- 🔧 Configuration files in `config/` directory

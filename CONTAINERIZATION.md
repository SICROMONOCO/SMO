# SMO Containerization Guide

## Prerequisites

Before starting, ensure you have:

1. **Docker Engine** installed and running
   - For Ubuntu/Debian: See installation instructions below
   - For other distributions: Visit [Docker Installation Guide](https://docs.docker.com/engine/install/)
   
2. **Docker Compose** (v1.27.0+ or Docker Compose plugin v2.0.0+)
   - Usually included with Docker installation
   - The setup script will detect which version you have

### Quick Docker Installation (Ubuntu/Debian)

If you don't have Docker installed, see [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) for detailed installation instructions for all Linux distributions.

**Quick Ubuntu/Debian installation:**

```bash
# Install prerequisites
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine and Docker Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker and enable on boot
sudo systemctl start docker
sudo systemctl enable docker

# (Optional) Add your user to docker group to run without sudo
sudo usermod -aG docker $USER
newgrp docker  # Or log out and back in
```

## Overview

SMO (System Monitoring & Orchestration) can run in two modes:

1. **Container Metrics Mode** (default): Monitors the Docker containers themselves
2. **Host Metrics Mode**: Monitors the actual Linux host machine

## Quick Start

### Option 1: Easy Setup (Recommended)

Run the interactive setup script:

```bash
./setup.sh
```

The script will guide you through:
- Creating your `.env` configuration file
- Choosing between container or host metrics mode
- Building and starting all services

### Option 2: Manual Setup

#### Step 1: Configure Environment

Copy the example environment file and edit it:

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

**Important:** Change these default values:
- `INFLUXDB_TOKEN` - Use a strong random token
- `DOCKER_INFLUXDB_INIT_PASSWORD` - Use a strong password

#### Step 2A: Container Metrics Mode (Default)

This mode monitors the Docker containers themselves. Best for:
- Development and testing
- Learning how SMO works
- Monitoring containerized applications

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Access points:
# - Web Dashboard: http://localhost:5678
# - InfluxDB UI: http://localhost:8086

# Run TUI
docker-compose run --rm smo-tui
```

#### Step 2B: Host Metrics Mode (Linux Only)

This mode monitors your actual Linux host machine. Best for:
- Production monitoring
- Real server/VM monitoring
- Accurate system metrics

**Requirements:**
- Linux operating system
- Docker with privileged container support
- Root/sudo access

```bash
# Build images
docker-compose -f docker-compose.yml -f docker-compose.host.yml build

# Start services
docker-compose -f docker-compose.yml -f docker-compose.host.yml up -d

# Access points:
# - Web Dashboard: http://localhost:5000  (Note: port 5000, not 5678)
# - InfluxDB UI: http://localhost:8086

# Run TUI
docker-compose -f docker-compose.yml -f docker-compose.host.yml run --rm smo-tui
```

## Understanding Host Metrics Mode

### What It Does

When you use `docker-compose.host.yml`, the containers gain access to host-level system information:

1. **PID Namespace Sharing** (`pid: host`):
   - Container sees all host processes
   - psutil reports actual host process metrics
   - Shows real CPU and memory usage of host

2. **Host Filesystem Mounts**:
   - `/proc` → Real process information
   - `/sys` → Real system information
   - `/etc/os-release` → Real OS details

3. **Host Network Mode** (`network_mode: host`):
   - Accurate network interface metrics
   - Real network traffic statistics
   - No Docker network overhead in metrics

4. **Privileged Mode** (`privileged: true`):
   - Full access to host resources
   - Required for complete metric collection

### Security Considerations

⚠️ **Host metrics mode requires privileged containers**

This is necessary because:
- Need to access host `/proc` filesystem
- Need to see all host processes
- Need accurate system metrics

**Security best practices:**
- Only use on trusted hosts
- Don't expose containers to untrusted networks
- Use strong passwords in `.env` file
- Consider using Docker secrets in production
- Review and audit container access regularly

### Network Mode Differences

| Mode | Docker Network | InfluxDB URL | Web Dashboard Port |
|------|----------------|--------------|-------------------|
| Container | Bridge | `http://smo-db:8086` | 5678 |
| Host | Host | `http://localhost:8086` | 5000 |

In host network mode:
- Containers use `localhost` instead of service names
- Web dashboard runs on port 5000 (container port = host port)
- No port mapping needed (using host network directly)

## Docker Compose Files

SMO uses a simple, two-file Docker Compose structure:

1. **docker-compose.yml** - Base configuration for container metrics mode
2. **docker-compose.host.yml** - Extends base with host metrics mode settings

The setup script (`setup.sh`) automatically selects the appropriate files based on your choice.

## Common Commands

### View Logs

```bash
# Container mode
docker-compose logs -f

# Host mode
docker-compose -f docker-compose.yml -f docker-compose.host.yml logs -f

# Specific service
docker-compose logs -f smo-agent
```

### Stop Services

```bash
# Container mode
docker-compose down

# Host mode
docker-compose -f docker-compose.yml -f docker-compose.host.yml down
```

### Restart Services

```bash
# Container mode
docker-compose restart

# Host mode
docker-compose -f docker-compose.yml -f docker-compose.host.yml restart
```

### Access InfluxDB Shell

```bash
docker-compose exec smo-db influx
```

## Troubleshooting

### "Cannot connect to the Docker daemon" error

**Error message:**
```
❌ Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?
```

**This means Docker is not installed or not running. Solutions:**

See [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) for comprehensive troubleshooting.

**Quick solutions:**

1. **Check if Docker is installed:**
   ```bash
   docker --version
   ```
   If not found, install Docker using the instructions above.

2. **Check if Docker daemon is running:**
   ```bash
   sudo systemctl status docker
   ```
   
3. **Start Docker if it's stopped:**
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker  # Enable auto-start on boot
   ```

4. **Check permissions (if you get permission denied):**
   ```bash
   # Add your user to docker group
   sudo usermod -aG docker $USER
   newgrp docker  # Or log out and back in
   ```

5. **Verify Docker is working:**
   ```bash
   docker info
   docker run hello-world
   ```

### "Permission denied" errors in host mode

**Cause:** Insufficient permissions for privileged containers

**Solution:**
```bash
# Run with sudo
sudo docker-compose -f docker-compose.yml -f docker-compose.host.yml up -d
```

### Metrics show container values in host mode

**Cause:** Not using the host compose file

**Solution:** Always include both compose files:
```bash
docker-compose -f docker-compose.yml -f docker-compose.host.yml [command]
```

### Web dashboard shows "No data"

**Cause:** InfluxDB not initialized or wrong URL

**Solutions:**
1. Check InfluxDB is running: `docker-compose ps`
2. Check logs: `docker-compose logs smo-db`
3. Verify `.env` file has correct values
4. Wait 10-15 seconds for first metrics to be collected

### TUI shows "Connection refused"

**Cause:** Services not started or network issues

**Solution:**
```bash
# Check service status
docker-compose ps

# View agent logs
docker-compose logs smo-agent

# Restart services
docker-compose restart
```

## Environment Variables Reference

See `.env.example` for all available variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `INFLUXDB_URL` | InfluxDB connection URL | `http://smo-db:8086` |
| `INFLUXDB_TOKEN` | Authentication token | `my-super-secret-auth-token` |
| `INFLUXDB_ORG` | Organization name | `my-org` |
| `INFLUXDB_BUCKET` | Metrics bucket name | `smo-metrics` |
| `HOST_MONITOR` | Enable host monitoring | `true` |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Linux Host                      │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │         Docker Containers                 │  │
│  │                                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌────────┐ │  │
│  │  │ SMO      │→ │ InfluxDB │ ← │ Web    │ │  │
│  │  │ Agent    │  │          │   │ Dashboard│ │
│  │  └────┬─────┘  └──────────┘  └────────┘ │  │
│  │       │                                   │  │
│  │       ↓ (host mode)                       │  │
│  └───────┼───────────────────────────────────┘  │
│          │                                       │
│          ↓                                       │
│    ┌─────────────┐                              │
│    │ /proc /sys  │  ← Real host metrics        │
│    └─────────────┘                              │
└─────────────────────────────────────────────────┘
```

## Performance Impact

### Container Mode
- **CPU Impact:** ~1-2% of available container resources
- **Memory:** ~50-100 MB per container
- **Disk:** Minimal (logs only)

### Host Mode
- **CPU Impact:** ~0.5-1% of total host CPU
- **Memory:** ~50-100 MB
- **Disk:** Minimal (logs only)
- **Network:** Negligible overhead

## Production Deployment

For production use with host metrics:

1. **Use strong credentials:**
   ```bash
   # Generate strong token
   INFLUXDB_TOKEN=$(openssl rand -hex 32)
   # Update .env file
   ```

2. **Enable TLS for web dashboard** (recommended)

3. **Set resource limits** in docker-compose:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '0.5'
         memory: 256M
   ```

4. **Enable log rotation:**
   ```yaml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

5. **Use Docker secrets** instead of environment variables

## Next Steps

- Review [USAGE.md](USAGE.md) for application features
- Check [README.md](README.md) for architecture details
- Configure alerts in `config/config.yaml`
- Customize dashboard layouts

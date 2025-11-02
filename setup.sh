#!/bin/bash
# 
# SMO Setup Script
# Initializes the SMO monitoring system with proper environment configuration
#

set -e

echo "🚀 SMO System Monitoring Setup"
echo "================================"
echo ""

# Function to detect docker-compose command
detect_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null; then
        echo "docker compose"
    else
        return 1
    fi
}

# Check if Docker is installed and running
echo "🔍 Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo ""
    echo "📦 Please install Docker first:"
    echo ""
    echo "For Ubuntu/Debian:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y ca-certificates curl gnupg"
    echo "  sudo install -m 0755 -d /etc/apt/keyrings"
    echo "  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg"
    echo "  sudo chmod a+r /etc/apt/keyrings/docker.gpg"
    echo ""
    echo "  # Add Docker repository"
    echo "  echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \\"
    echo "    https://download.docker.com/linux/ubuntu \$(. /etc/os-release && echo \"\$VERSION_CODENAME\") stable\" | \\"
    echo "    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null"
    echo ""
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
    echo ""
    echo "For other distributions, visit: https://docs.docker.com/engine/install/"
    echo ""
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running!"
    echo ""
    echo "🔧 Please start Docker:"
    echo ""
    echo "  sudo systemctl start docker"
    echo "  sudo systemctl enable docker  # Enable auto-start on boot"
    echo ""
    echo "💡 If you see permission errors, add your user to the docker group:"
    echo "  sudo usermod -aG docker \$USER"
    echo "  newgrp docker  # Or log out and back in"
    echo ""
    exit 1
fi

# Detect docker-compose command
DOCKER_COMPOSE_CMD=$(detect_docker_compose)
if [ $? -ne 0 ]; then
    echo "❌ Docker Compose is not installed!"
    echo ""
    echo "📦 Please install Docker Compose:"
    echo ""
    echo "For Ubuntu/Debian (recommended - installs Docker Compose v2):"
    echo "  sudo apt-get install -y docker-compose-plugin"
    echo ""
    echo "Alternatively, install standalone docker-compose:"
    echo "  sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose"
    echo "  sudo chmod +x /usr/local/bin/docker-compose"
    echo ""
    exit 1
fi

echo "✅ Docker is installed and running"
echo "✅ Using: $DOCKER_COMPOSE_CMD"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and update:"
    echo "   - INFLUXDB_TOKEN (change from default)"
    echo "   - DOCKER_INFLUXDB_INIT_PASSWORD (change from default)"
    echo ""
    read -p "Press Enter to continue after editing .env, or Ctrl+C to exit..."
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🔧 Choose monitoring mode:"
echo "1) Container metrics (default - monitors the containers themselves)"
echo "2) Host metrics (monitors the actual Linux host machine)"
echo ""
read -p "Enter choice [1-2] (default: 1): " choice
choice=${choice:-1}

if [ "$choice" = "2" ]; then
    echo ""
    echo "🐧 Host Metrics Mode Selected"
    echo "================================"
    echo "This will monitor your actual Linux host machine."
    echo ""
    echo "Requirements:"
    echo "  - Linux operating system"
    echo "  - Docker with privileged container support"
    echo "  - Root/sudo access (for privileged containers)"
    echo ""
    echo "⚠️  Security Note: This mode requires privileged containers"
    echo "   to access host system metrics."
    echo ""
    read -p "Continue with host metrics mode? [y/N]: " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Cancelled. Falling back to container metrics mode."
        choice="1"
    else
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.host.yml"
        MODE="Host Metrics"
    fi
else
    COMPOSE_FILES="-f docker-compose.yml"
    MODE="Container Metrics"
fi

echo ""
echo "📦 Building Docker images..."
$DOCKER_COMPOSE_CMD $COMPOSE_FILES build

echo ""
echo "🚀 Starting services in $MODE mode..."
$DOCKER_COMPOSE_CMD $COMPOSE_FILES up -d smo-db smo-agent smo-web

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

echo ""
echo "✅ SMO is now running!"
echo ""
echo "📊 Access Points:"
echo "================================"

if [ "$choice" = "2" ]; then
    echo "  🌐 Web Dashboard:  http://localhost:5000"
    echo "  📈 InfluxDB UI:    http://localhost:8086"
else
    echo "  🌐 Web Dashboard:  http://localhost:5678"
    echo "  📈 InfluxDB UI:    http://localhost:8086"
fi

echo ""
echo "💻 To run the TUI:"
if [ "$choice" = "2" ]; then
    echo "  $DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.host.yml run --rm smo-tui"
else
    echo "  $DOCKER_COMPOSE_CMD run --rm smo-tui"
fi

echo ""
echo "📋 View logs:"
echo "  $DOCKER_COMPOSE_CMD $COMPOSE_FILES logs -f"

echo ""
echo "🛑 Stop services:"
echo "  $DOCKER_COMPOSE_CMD $COMPOSE_FILES down"

echo ""
echo "✨ Setup complete!"

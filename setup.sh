#!/bin/bash
# 
# SMO Setup Script
# Initializes the SMO monitoring system with proper environment configuration
#

set -e

echo "🚀 SMO System Monitoring Setup"
echo "================================"
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
docker-compose $COMPOSE_FILES build

echo ""
echo "🚀 Starting services in $MODE mode..."
docker-compose $COMPOSE_FILES up -d smo-db smo-agent smo-web

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
    echo "  docker-compose -f docker-compose.yml -f docker-compose.host.yml run --rm smo-tui"
else
    echo "  docker-compose run --rm smo-tui"
fi

echo ""
echo "📋 View logs:"
echo "  docker-compose $COMPOSE_FILES logs -f"

echo ""
echo "🛑 Stop services:"
echo "  docker-compose $COMPOSE_FILES down"

echo ""
echo "✨ Setup complete!"

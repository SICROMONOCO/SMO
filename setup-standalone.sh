#!/bin/bash
#
# SMO Standalone Installation Script
# ===================================
# Installs SMO and InfluxDB directly on the host system (non-containerized)
# Supports Ubuntu/Debian, Fedora/RHEL, and Arch Linux
#

set -e

echo "🚀 SMO Standalone Installation"
echo "==============================="
echo ""
echo "This will install SMO directly on your system (no Docker required)."
echo ""
echo "ℹ️  Installation Options:"
echo "  1. Full Installation (with InfluxDB) - Recommended for historical metrics"
echo "  2. Minimal Installation (without InfluxDB) - Simpler, file-based logging only"
echo ""
read -p "Install InfluxDB? [Y/n]: " install_influx
install_influx=${install_influx:-y}
if [ "$install_influx" = "n" ] || [ "$install_influx" = "N" ]; then
    SKIP_INFLUXDB=true
    echo "ℹ️  Skipping InfluxDB installation"
else
    SKIP_INFLUXDB=false
    echo "ℹ️  InfluxDB will be installed"
fi
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo "❌ Cannot detect OS. /etc/os-release not found."
    exit 1
fi

echo "✓ Detected OS: $OS"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Running as root. Will install system-wide."
    INSTALL_USER=$SUDO_USER
    INSTALL_GROUP=$(id -gn $SUDO_USER)
else
    echo "⚠️  Not running as root. Some steps may require sudo."
    INSTALL_USER=$USER
    INSTALL_GROUP=$(id -gn)
fi

INSTALL_DIR="/opt/smo"
CONFIG_DIR="/etc/smo"
LOG_DIR="/var/log/smo"
DATA_DIR="/var/lib/smo"

echo ""
echo "📁 Installation directories:"
echo "   Install:     $INSTALL_DIR"
echo "   Config:      $CONFIG_DIR"
echo "   Logs:        $LOG_DIR"
echo "   Data:        $DATA_DIR"
echo ""
read -p "Continue with installation? [y/N]: " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo "================================="
echo "Step 1: Installing Dependencies"
echo "================================="
echo ""

# Install Python3 and pip
case $OS in
    ubuntu|debian)
        echo "Installing dependencies for Ubuntu/Debian..."
        apt-get update
        apt-get install -y python3 python3-pip python3-venv curl wget gnupg2 lsb-release
        ;;
    fedora|rhel|centos)
        echo "Installing dependencies for Fedora/RHEL/CentOS..."
        dnf install -y python3 python3-pip curl wget gnupg2
        ;;
    arch|manjaro)
        echo "Installing dependencies for Arch Linux..."
        pacman -Sy --noconfirm python python-pip curl wget gnupg
        ;;
    *)
        echo "⚠️  Unsupported OS: $OS"
        echo "Please install Python 3.8+ and pip manually."
        exit 1
        ;;
esac

echo "✓ Python dependencies installed"
echo ""

if [ "$SKIP_INFLUXDB" = false ]; then
    echo "================================="
    echo "Step 2: Installing InfluxDB"
    echo "================================="
    echo ""

    # Check if InfluxDB is already installed
    if command -v influxd &> /dev/null; then
        echo "✓ InfluxDB is already installed"
        INFLUXDB_VERSION=$(influxd version | head -n1)
        echo "  Version: $INFLUXDB_VERSION"
    else
        case $OS in
            ubuntu|debian)
                echo "Installing InfluxDB for Ubuntu/Debian..."
                
                # Add InfluxDB repository
                wget -q https://repos.influxdata.com/influxdata-archive_compat.key
                echo '393e8779c89ac8d958f81f942f9ad7fb82a25e133faddaf92e15b16e6ac9ce4c influxdata-archive_compat.key' | sha256sum -c && cat influxdata-archive_compat.key | gpg --dearmor | tee /etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg > /dev/null
                echo "deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg] https://repos.influxdata.com/debian stable main" | tee /etc/apt/sources.list.d/influxdata.list
                rm influxdata-archive_compat.key
                
                apt-get update
                apt-get install -y influxdb2 influxdb2-cli
                ;;
            fedora|rhel|centos)
                echo "Installing InfluxDB for Fedora/RHEL/CentOS..."
                
                cat > /etc/yum.repos.d/influxdb.repo << 'EOF'
[influxdb]
name = InfluxDB Repository - RHEL
baseurl = https://repos.influxdata.com/rhel/\$releasever/\$basearch/stable
enabled = 1
gpgcheck = 1
gpgkey = https://repos.influxdata.com/influxdata-archive_compat.key
EOF
                
                dnf install -y influxdb2 influxdb2-cli
                ;;
            arch|manjaro)
                echo "Installing InfluxDB for Arch Linux..."
                pacman -Sy --noconfirm influxdb
                ;;
        esac
        
        echo "✓ InfluxDB installed"
    fi

    echo ""
else
    echo "================================="
    echo "Step 2: Skipping InfluxDB"
    echo "================================="
    echo ""
    echo "ℹ️  InfluxDB installation skipped (minimal installation mode)"
    echo "   Metrics will be logged to files only"
    echo ""
fi

echo "================================="
echo "Step 3: Setting Up Directories"
echo "================================="
echo ""

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$LOG_DIR"

if [ "$SKIP_INFLUXDB" = false ]; then
    mkdir -p "$DATA_DIR/influxdb"
fi

# Set ownership
if [ "$EUID" -eq 0 ]; then
    chown -R $INSTALL_USER:$INSTALL_GROUP "$INSTALL_DIR"
    chown -R $INSTALL_USER:$INSTALL_GROUP "$LOG_DIR"
    if [ "$SKIP_INFLUXDB" = false ]; then
        chown -R influxdb:influxdb "$DATA_DIR/influxdb" 2>/dev/null || chown -R $INSTALL_USER:$INSTALL_GROUP "$DATA_DIR/influxdb"
    fi
fi

echo "✓ Directories created"
echo ""

echo "================================="
echo "Step 4: Installing SMO"
echo "================================="
echo ""

# Copy SMO files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Copying files from $SCRIPT_DIR to $INSTALL_DIR..."

# Copy application files
cp -r "$SCRIPT_DIR"/*.py "$INSTALL_DIR/" 2>/dev/null || true
cp -r "$SCRIPT_DIR"/metrics "$INSTALL_DIR/" 2>/dev/null || true
cp -r "$SCRIPT_DIR"/tui "$INSTALL_DIR/" 2>/dev/null || true
cp -r "$SCRIPT_DIR"/config "$INSTALL_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR"/requirements.txt "$INSTALL_DIR/"

# Create symbolic link for config
ln -sf "$INSTALL_DIR/config" "$CONFIG_DIR/config"

echo "✓ SMO files copied"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
cd "$INSTALL_DIR"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "✓ Python dependencies installed"
echo ""

echo "================================="
echo "Step 5: Configuring Environment"
echo "================================="
echo ""

if [ "$SKIP_INFLUXDB" = false ]; then
    # Generate random tokens
    INFLUX_TOKEN=$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
    INFLUX_PASSWORD=$(openssl rand -hex 16 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)

    # Create .env file with InfluxDB enabled
    cat > "$INSTALL_DIR/.env" << EOF
# InfluxDB Configuration
INFLUXDB_ENABLED=true
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=$INFLUX_TOKEN
INFLUXDB_ORG=smo-org
INFLUXDB_BUCKET=smo-metrics

# InfluxDB Admin Credentials
INFLUXDB_ADMIN_USER=admin
INFLUXDB_ADMIN_PASSWORD=$INFLUX_PASSWORD
INFLUXDB_ADMIN_TOKEN=$INFLUX_TOKEN

# Host Monitoring Configuration
HOST_MONITOR=true
EOF

    chmod 600 "$INSTALL_DIR/.env"

    echo "✓ Environment configured with InfluxDB"
    echo ""
    echo "   InfluxDB Admin User: admin"
    echo "   InfluxDB Admin Password: $INFLUX_PASSWORD"
    echo "   InfluxDB Token: $INFLUX_TOKEN"
    echo ""
    echo "   ⚠️  IMPORTANT: Save these credentials! They are also in $INSTALL_DIR/.env"
    echo ""
else
    # Create .env file with InfluxDB disabled
    cat > "$INSTALL_DIR/.env" << EOF
# InfluxDB Configuration
INFLUXDB_ENABLED=false

# Host Monitoring Configuration
HOST_MONITOR=true
EOF

    chmod 600 "$INSTALL_DIR/.env"

    echo "✓ Environment configured (InfluxDB disabled)"
    echo "   Metrics will be logged to files in $LOG_DIR"
    echo ""
fi

if [ "$SKIP_INFLUXDB" = false ]; then
    echo "================================="
    echo "Step 6: Configuring InfluxDB"
    echo "================================="
    echo ""

    # Configure InfluxDB
    cat > /etc/influxdb/config.toml << EOF
[meta]
  dir = "$DATA_DIR/influxdb/meta"

[data]
  dir = "$DATA_DIR/influxdb/data"
  engine = "tsm1"
  wal-dir = "$DATA_DIR/influxdb/wal"

[http]
  bind-address = ":8086"
  enabled = true
EOF

    # Start InfluxDB
    echo "Starting InfluxDB service..."
    systemctl enable influxdb --now 2>/dev/null || systemctl start influxdb 2>/dev/null || {
        echo "⚠️  Warning: Could not start InfluxDB via systemctl"
        echo "   You may need to start it manually"
    }

    # Wait for InfluxDB to be ready
    echo "Waiting for InfluxDB to be ready..."
    INFLUX_READY=0
    for i in {1..30}; do
        if curl -s http://localhost:8086/health > /dev/null 2>&1; then
            echo "✓ InfluxDB is ready"
            INFLUX_READY=1
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ InfluxDB failed to start within 30 seconds"
            echo "   Check logs: journalctl -u influxdb -n 50"
            echo "   Common issues:"
            echo "   - Port 8086 already in use: sudo netstat -tlnp | grep 8086"
            echo "   - Permission issues: check ownership of $DATA_DIR/influxdb"
            echo ""
            echo "   You can continue without InfluxDB by setting INFLUXDB_ENABLED=false in $INSTALL_DIR/.env"
            read -p "Continue anyway? [y/N]: " continue_anyway
            if [ "$continue_anyway" != "y" ] && [ "$continue_anyway" != "Y" ]; then
                exit 1
            fi
            INFLUX_READY=0
            break
        fi
        sleep 1
    done

    if [ $INFLUX_READY -eq 1 ]; then
        # Check if InfluxDB is already initialized
        echo "Checking InfluxDB initialization status..."
        # Try to get the setup status from the API
        # Response format: {"allowed":true/false,...}
        SETUP_RESPONSE=$(curl -s http://localhost:8086/api/v2/setup)

        # Check if we got a valid response
        if [ -z "$SETUP_RESPONSE" ]; then
            echo "⚠️  Could not check InfluxDB status"
            echo "Attempting initialization anyway..."
            ONBOARDING_ALLOWED="true"
        elif echo "$SETUP_RESPONSE" | grep -q '"allowed"[[:space:]]*:[[:space:]]*false'; then
            ONBOARDING_ALLOWED="false"
        else
            ONBOARDING_ALLOWED="true"
        fi

        if [ "$ONBOARDING_ALLOWED" = "false" ]; then
            echo "⚠️  InfluxDB is already initialized"
            echo ""
            echo "If you need to reinitialize InfluxDB with new credentials:"
            echo "  1. Stop InfluxDB: sudo systemctl stop influxdb"
            echo "  2. Remove data: sudo rm -rf $DATA_DIR/influxdb/*"
            echo "  3. Restart setup: sudo ./setup-standalone.sh"
            echo ""
            echo "Continuing with existing InfluxDB setup..."
            echo "Make sure to use the existing credentials in $INSTALL_DIR/.env"
        else
            # Initialize InfluxDB
            echo "Initializing InfluxDB with new credentials..."
            
            # Run influx setup and capture output
            SETUP_OUTPUT=$(influx setup \
                --username admin \
                --password "$INFLUX_PASSWORD" \
                --org smo-org \
                --bucket smo-metrics \
                --token "$INFLUX_TOKEN" \
                --force \
                2>&1)
            
            SETUP_EXIT_CODE=$?
            
            if [ $SETUP_EXIT_CODE -eq 0 ]; then
                echo "✓ InfluxDB initialized successfully"
            else
                echo "⚠️  InfluxDB setup command had issues:"
                echo "$SETUP_OUTPUT"
                echo ""
                echo "Verifying InfluxDB configuration..."
                
                # Verify that we can authenticate with the token
                AUTH_CHECK=$(curl -s -w "%{http_code}" -o /dev/null \
                    -H "Authorization: Token $INFLUX_TOKEN" \
                    http://localhost:8086/api/v2/buckets)
                
                if [ "$AUTH_CHECK" = "200" ]; then
                    echo "✓ InfluxDB is accessible with provided credentials"
                else
                    echo "❌ Cannot authenticate with InfluxDB. HTTP status: $AUTH_CHECK"
                    echo "Please check the credentials and try again"
                    echo "You may need to manually initialize InfluxDB or disable it"
                    echo ""
                    echo "To disable InfluxDB and use file-based logging only:"
                    echo "  echo 'INFLUXDB_ENABLED=false' >> $INSTALL_DIR/.env"
                    read -p "Continue anyway? [y/N]: " continue_anyway
                    if [ "$continue_anyway" != "y" ] && [ "$continue_anyway" != "Y" ]; then
                        exit 1
                    fi
                fi
            fi
        fi

        echo "✓ InfluxDB configured and running"
    fi

    echo ""
else
    echo "================================="
    echo "Step 6: InfluxDB Configuration Skipped"
    echo "================================="
    echo ""
    echo "ℹ️  InfluxDB not installed (minimal installation mode)"
    echo ""
fi

echo "================================="
echo "Step 7: Creating Systemd Services"
echo "================================="
echo ""

# Create SMO Agent service
if [ "$SKIP_INFLUXDB" = false ]; then
    # With InfluxDB dependency
    cat > /etc/systemd/system/smo-agent.service << EOF
[Unit]
Description=SMO (System Monitoring Observer) Agent
Documentation=file://$INSTALL_DIR/README.md
After=network.target influxdb.service
Wants=network-online.target influxdb.service

[Service]
Type=simple
User=$INSTALL_USER
Group=$INSTALL_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/agent.py run
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=smo-agent

# Security hardening
NoNewPrivileges=true
PrivateTmp=false

[Install]
WantedBy=multi-user.target
EOF
else
    # Without InfluxDB dependency
    cat > /etc/systemd/system/smo-agent.service << EOF
[Unit]
Description=SMO (System Monitoring Observer) Agent
Documentation=file://$INSTALL_DIR/README.md
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$INSTALL_USER
Group=$INSTALL_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/agent.py run
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=smo-agent

# Security hardening
NoNewPrivileges=true
PrivateTmp=false

[Install]
WantedBy=multi-user.target
EOF
fi

# Create SMO Web Dashboard service
cat > /etc/systemd/system/smo-web.service << EOF
[Unit]
Description=SMO Web Dashboard
Documentation=file://$INSTALL_DIR/README.md
After=network.target smo-agent.service
Wants=network-online.target
Requires=smo-agent.service

[Service]
Type=simple
User=$INSTALL_USER
Group=$INSTALL_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/uvicorn web_dashboard:app --host 0.0.0.0 --port 5000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=smo-web

# Security hardening
NoNewPrivileges=true
PrivateTmp=false

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

echo "✓ Systemd services created"
echo ""

echo "================================="
echo "Step 8: Starting Services"
echo "================================="
echo ""

# Enable and start services
systemctl enable smo-agent smo-web
systemctl start smo-agent smo-web

# Wait a moment for services to start
sleep 3

# Check service status
echo "Checking service status..."
if systemctl is-active --quiet smo-agent; then
    echo "✓ SMO Agent is running"
else
    echo "❌ SMO Agent failed to start. Check logs: journalctl -u smo-agent"
fi

if systemctl is-active --quiet smo-web; then
    echo "✓ SMO Web Dashboard is running"
else
    echo "❌ SMO Web Dashboard failed to start. Check logs: journalctl -u smo-web"
fi

echo ""

echo "================================="
echo "Step 9: Firewall Configuration"
echo "================================="
echo ""

# Configure firewall if available
if command -v ufw &> /dev/null; then
    echo "Configuring UFW firewall..."
    if [ "$SKIP_INFLUXDB" = false ]; then
        ufw allow 8086/tcp comment 'InfluxDB'
    fi
    ufw allow 5000/tcp comment 'SMO Web Dashboard'
    echo "✓ UFW rules added"
elif command -v firewall-cmd &> /dev/null; then
    echo "Configuring firewalld..."
    if [ "$SKIP_INFLUXDB" = false ]; then
        firewall-cmd --permanent --add-port=8086/tcp
    fi
    firewall-cmd --permanent --add-port=5000/tcp
    firewall-cmd --reload
    echo "✓ Firewalld rules added"
else
    if [ "$SKIP_INFLUXDB" = false ]; then
        echo "⚠️  No firewall detected. Ensure ports 8086 and 5000 are accessible if needed."
    else
        echo "⚠️  No firewall detected. Ensure port 5000 is accessible if needed."
    fi
fi

echo ""

echo "=========================================="
echo "✅ SMO Standalone Installation Complete!"
echo "=========================================="
echo ""
echo "📊 Access Points:"
echo "   🌐 Web Dashboard:  http://localhost:5000"
if [ "$SKIP_INFLUXDB" = false ]; then
    echo "   📈 InfluxDB UI:    http://localhost:8086"
fi
echo ""
echo "   To access remotely, use your server's IP address:"
echo "   🌐 Web Dashboard:  http://YOUR_SERVER_IP:5000"
if [ "$SKIP_INFLUXDB" = false ]; then
    echo "   📈 InfluxDB UI:    http://YOUR_SERVER_IP:8086"
fi
echo ""
if [ "$SKIP_INFLUXDB" = false ]; then
    echo "🔑 Credentials:"
    echo "   InfluxDB User:     admin"
    echo "   InfluxDB Password: $INFLUX_PASSWORD"
    echo "   InfluxDB Token:    $INFLUX_TOKEN"
    echo ""
    echo "   💾 Saved in: $INSTALL_DIR/.env"
    echo ""
fi
echo "📋 Useful Commands:"
echo "   View agent logs:     journalctl -u smo-agent -f"
echo "   View web logs:       journalctl -u smo-web -f"
if [ "$SKIP_INFLUXDB" = false ]; then
    echo "   View InfluxDB logs:  journalctl -u influxdb -f"
fi
echo ""
echo "   Restart agent:       systemctl restart smo-agent"
echo "   Restart web:         systemctl restart smo-web"
if [ "$SKIP_INFLUXDB" = false ]; then
    echo "   Restart InfluxDB:    systemctl restart influxdb"
    echo ""
    echo "   Stop all services:   systemctl stop smo-agent smo-web influxdb"
    echo "   Start all services:  systemctl start influxdb smo-agent smo-web"
else
    echo ""
    echo "   Stop all services:   systemctl stop smo-agent smo-web"
    echo "   Start all services:  systemctl start smo-agent smo-web"
fi
echo ""
echo "💻 Run TUI Dashboard:"
echo "   cd $INSTALL_DIR"
echo "   source venv/bin/activate"
echo "   python3 -m tui.tui_dashboard"
echo ""
if [ "$SKIP_INFLUXDB" = true ]; then
    echo "ℹ️  Installation Mode: Minimal (without InfluxDB)"
    echo "   Metrics are logged to: $LOG_DIR/smo_metrics.jsonl"
    echo "   The web dashboard and TUI read from these log files"
    echo ""
fi
echo "✨ Installation complete!"
echo ""

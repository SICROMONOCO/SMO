#!/bin/bash
#
# SMO Standalone Uninstall Script
# ================================
# Removes SMO and optionally InfluxDB from the host system
#

set -e

echo "🗑️  SMO Standalone Uninstall"
echo "============================"
echo ""

INSTALL_DIR="/opt/smo"
CONFIG_DIR="/etc/smo"
LOG_DIR="/var/log/smo"
DATA_DIR="/var/lib/smo"

echo "This will remove SMO from your system."
echo ""
echo "Directories to be removed:"
echo "   $INSTALL_DIR"
echo "   $CONFIG_DIR"
echo "   $LOG_DIR"
echo "   $DATA_DIR"
echo ""
read -p "Continue with uninstall? [y/N]: " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo ""
echo "Stopping SMO services..."
systemctl stop smo-agent smo-web 2>/dev/null || true
systemctl disable smo-agent smo-web 2>/dev/null || true

echo "Removing systemd service files..."
rm -f /etc/systemd/system/smo-agent.service
rm -f /etc/systemd/system/smo-web.service
systemctl daemon-reload

echo "Removing SMO directories..."
rm -rf "$INSTALL_DIR"
rm -rf "$CONFIG_DIR"
rm -rf "$LOG_DIR"
rm -rf "$DATA_DIR"

echo ""
echo "✅ SMO has been uninstalled."
echo ""

read -p "Do you also want to remove InfluxDB? [y/N]: " remove_influx

if [ "$remove_influx" = "y" ] || [ "$remove_influx" = "Y" ]; then
    echo ""
    echo "Stopping InfluxDB..."
    systemctl stop influxdb 2>/dev/null || true
    systemctl disable influxdb 2>/dev/null || true
    
    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        OS="unknown"
    fi
    
    case $OS in
        ubuntu|debian)
            echo "Removing InfluxDB (Ubuntu/Debian)..."
            apt-get remove -y influxdb2 influxdb2-cli
            apt-get autoremove -y
            rm -f /etc/apt/sources.list.d/influxdata.list
            ;;
        fedora|rhel|centos)
            echo "Removing InfluxDB (Fedora/RHEL/CentOS)..."
            dnf remove -y influxdb2 influxdb2-cli
            rm -f /etc/yum.repos.d/influxdb.repo
            ;;
        arch|manjaro)
            echo "Removing InfluxDB (Arch Linux)..."
            pacman -R --noconfirm influxdb
            ;;
        *)
            echo "⚠️  Cannot auto-remove InfluxDB on this OS."
            echo "Please remove manually if desired."
            ;;
    esac
    
    echo ""
    read -p "Remove InfluxDB data directory? (This will delete all stored metrics) [y/N]: " remove_data
    
    if [ "$remove_data" = "y" ] || [ "$remove_data" = "Y" ]; then
        rm -rf /var/lib/influxdb
        echo "✅ InfluxDB data removed"
    fi
    
    echo "✅ InfluxDB has been uninstalled."
fi

echo ""
echo "✨ Uninstall complete!"
echo ""

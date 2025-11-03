from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
import json
import os
import yaml
import tempfile
from pathlib import Path
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from starlette.websockets import WebSocketDisconnect, WebSocketState
from starlette.background import BackgroundTask
from typing import Dict, Any
import csv
from io import StringIO
from dotenv import load_dotenv

app = FastAPI()

# Configuration paths
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
METRICS_LOG_PATH = PROJECT_ROOT / "logs" / "smo_metrics.jsonl"

# Load environment variables from .env file
# This is important for standalone installations where .env contains InfluxDB credentials
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Pydantic models
class ConfigUpdate(BaseModel):
    config: Dict[str, Any]

html = r"""
<!DOCTYPE html>
<html>
    <head>
        <title>SMO Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #0a0a0a;
                color: #f0f0f0;
                padding: 20px;
                line-height: 1.6;
            }

            .header {
                text-align: center;
                margin-bottom: 30px;
                padding: 20px;
                background: linear-gradient(135deg, #1a1a1a, #2a2a2a);
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }

            h1 {
                color: #4a9eff;
                font-size: 2.5em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            }

            .subtitle {
                color: #888;
                font-size: 1.1em;
            }

            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }

            .metric-group {
                background: #121212;
                border: 2px solid #4a4a4a;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
                transition: transform 0.2s, box-shadow 0.2s;
            }

            .metric-group:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.4);
            }

            .metric-group-title {
                background: #2a2a2a;
                color: #e0e0e0;
                padding: 10px 15px;
                margin: -20px -20px 20px -20px;
                border-radius: 8px 8px 0 0;
                font-weight: bold;
                font-size: 1.3em;
                border-bottom: 3px solid #4a4a4a;
            }

            .metric-row {
                display: flex;
                align-items: center;
                margin-bottom: 15px;
                padding: 8px 0;
            }

            .metric-label {
                font-weight: bold;
                color: #4dd0e1;
                min-width: 140px;
                font-size: 0.95em;
            }

            .metric-value {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 5px;
            }

            .progress-bar-container {
                width: 100%;
                height: 24px;
                background: #1a1a1a;
                border-radius: 12px;
                overflow: hidden;
                border: 1px solid #333;
                position: relative;
            }

            .progress-bar {
                height: 100%;
                border-radius: 12px;
                transition: width 0.5s ease, background 0.3s ease;
                position: relative;
                background: linear-gradient(90deg, var(--bar-color), var(--bar-color-light));
            }

            .progress-text {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-weight: bold;
                font-size: 0.9em;
                color: #fff;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                z-index: 1;
            }

            .info-text {
                color: #bbb;
                font-size: 0.9em;
                margin-top: 3px;
            }

            .info-text span {
                margin-right: 15px;
            }

            .value-good { color: #4caf50; }
            .value-warning { color: #ff9800; }
            .value-critical { color: #f44336; }
            .value-info { color: #2196f3; }

            .bar-good {
                --bar-color: #4caf50;
                --bar-color-light: #66bb6a;
            }
            .bar-warning {
                --bar-color: #ff9800;
                --bar-color-light: #ffa726;
            }
            .bar-critical {
                --bar-color: #f44336;
                --bar-color-light: #ef5350;
            }

            .stat-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 10px;
                margin-top: 10px;
            }

            .stat-item {
                background: #1a1a1a;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #333;
            }

            .stat-item-label {
                color: #888;
                font-size: 0.85em;
                margin-bottom: 3px;
            }

            .stat-item-value {
                font-weight: bold;
                font-size: 1.1em;
                color: #4dd0e1;
            }

            .alert-banner {
                background: #2a1a1a;
                border: 2px solid #ff6b6b;
                border-radius: 8px;
                padding: 15px 20px;
                margin-bottom: 20px;
                color: #ffaaaa;
            }

            .alert-title {
                font-weight: bold;
                font-size: 1.1em;
                margin-bottom: 8px;
                color: #ff6b6b;
            }

            .alert-item {
                padding: 5px 0;
                border-left: 3px solid #ff6b6b;
                padding-left: 10px;
                margin: 5px 0;
            }

            .no-data {
                color: #666;
                font-style: italic;
                text-align: center;
                padding: 40px;
            }

            @media (max-width: 768px) {
                .dashboard-grid {
                    grid-template-columns: 1fr;
                }

                h1 {
                    font-size: 1.8em;
                }
            }

            .loading {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid rgba(255,255,255,.3);
                border-radius: 50%;
                border-top-color: #4a9eff;
                animation: spin 1s ease-in-out infinite;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            /* Tab Navigation */
            .tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                border-bottom: 2px solid #4a4a4a;
                padding-bottom: 10px;
            }

            .tab-button {
                background: #1a1a1a;
                border: 2px solid #4a4a4a;
                border-bottom: none;
                color: #888;
                padding: 12px 24px;
                cursor: pointer;
                border-radius: 8px 8px 0 0;
                font-size: 1em;
                font-weight: bold;
                transition: all 0.3s ease;
            }

            .tab-button:hover {
                background: #2a2a2a;
                color: #f0f0f0;
            }

            .tab-button.active {
                background: #2a2a2a;
                color: #4a9eff;
                border-color: #4a9eff;
            }

            .tab-content {
                display: none;
            }

            .tab-content.active {
                display: block;
            }

            /* Config Editor Styles */
            .config-editor {
                background: #121212;
                border: 2px solid #4a4a4a;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }

            .config-section {
                margin-bottom: 20px;
            }

            .config-section-title {
                color: #4a9eff;
                font-size: 1.2em;
                font-weight: bold;
                margin-bottom: 10px;
                padding-bottom: 5px;
                border-bottom: 1px solid #4a4a4a;
            }

            .config-field {
                margin-bottom: 15px;
            }

            .config-label {
                display: block;
                color: #4dd0e1;
                font-weight: bold;
                margin-bottom: 5px;
            }

            .config-input {
                width: 100%;
                padding: 10px;
                background: #1a1a1a;
                border: 1px solid #4a4a4a;
                border-radius: 5px;
                color: #f0f0f0;
                font-size: 1em;
            }

            .config-input:focus {
                outline: none;
                border-color: #4a9eff;
            }

            .button {
                background: #4a9eff;
                color: #fff;
                border: none;
                padding: 12px 24px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 1em;
                font-weight: bold;
                margin-right: 10px;
                transition: background 0.3s ease;
            }

            .button:hover {
                background: #3a8eef;
            }

            .button-success {
                background: #4caf50;
            }

            .button-success:hover {
                background: #45a049;
            }

            .button-danger {
                background: #f44336;
            }

            .button-danger:hover {
                background: #da190b;
            }

            /* Log Exporter Styles */
            .log-exporter {
                background: #121212;
                border: 2px solid #4a4a4a;
                border-radius: 10px;
                padding: 20px;
            }

            .export-format {
                margin-bottom: 20px;
            }

            .format-option {
                display: inline-block;
                margin-right: 20px;
                margin-bottom: 10px;
            }

            .format-option input[type="radio"] {
                margin-right: 5px;
            }

            .format-option label {
                cursor: pointer;
                color: #f0f0f0;
            }

            /* Notification Toast */
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: #2a2a2a;
                border: 2px solid #4a9eff;
                border-radius: 5px;
                padding: 15px 20px;
                max-width: 300px;
                z-index: 1000;
                animation: slideIn 0.3s ease;
            }

            .notification.success {
                border-color: #4caf50;
            }

            .notification.error {
                border-color: #f44336;
            }

            @keyframes slideIn {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🖥️ SMO Dashboard</h1>
            <div class="subtitle">System Monitoring & Orchestration - Live Metrics</div>
        </div>

        <!-- Tab Navigation -->
        <div class="tabs">
            <button class="tab-button active" onclick="switchTab('metrics')">📊 Live Metrics</button>
            <button class="tab-button" onclick="switchTab('config')">⚙️ Config Editor</button>
            <button class="tab-button" onclick="switchTab('logs')">📄 Log Exporter</button>
        </div>

        <!-- Live Metrics Tab -->
        <div id="metrics-tab" class="tab-content active">
            <div id="alerts-container"></div>

            <div class="dashboard-grid">
            <div class="metric-group" id="cpu-group">
                <div class="metric-group-title">⚡ CPU Stats</div>
                <div id="cpu-content" class="no-data">
                    <div class="loading"></div> Loading CPU data...
                </div>
            </div>

            <div class="metric-group" id="memory-group">
                <div class="metric-group-title">💾 Memory</div>
                <div id="memory-content" class="no-data">
                    <div class="loading"></div> Loading memory data...
                </div>
            </div>

            <div class="metric-group" id="disk-group">
                <div class="metric-group-title">💿 Disk Usage</div>
                <div id="disk-content" class="no-data">
                    <div class="loading"></div> Loading disk data...
                </div>
            </div>

            <div class="metric-group" id="network-group">
                <div class="metric-group-title">🌐 Network I/O</div>
                <div id="network-content" class="no-data">
                    <div class="loading"></div> Loading network data...
                </div>
            </div>

            <div class="metric-group" id="system-group">
                <div class="metric-group-title">ℹ️ System Info</div>
                <div id="system-content" class="no-data">
                    <div class="loading"></div> Loading system data...
                </div>
            </div>

            <div class="metric-group" id="process-group">
                <div class="metric-group-title">🔄 Process Metrics</div>
                <div id="process-content" class="no-data">
                    <div class="loading"></div> Loading process data...
                </div>
            </div>
        </div>
        </div>

        <!-- Config Editor Tab -->
        <div id="config-tab" class="tab-content">
            <div class="config-editor">
                <h2 style="color: #4a9eff; margin-bottom: 20px;">⚙️ Configuration Editor</h2>
                <div id="config-form"></div>
                <div style="margin-top: 20px;">
                    <button class="button button-success" onclick="saveConfig()">💾 Save Configuration</button>
                    <button class="button button-danger" onclick="resetConfig()">🔄 Reset to Defaults</button>
                </div>
            </div>
        </div>

        <!-- Log Exporter Tab -->
        <div id="logs-tab" class="tab-content">
            <div class="log-exporter">
                <h2 style="color: #4a9eff; margin-bottom: 20px;">📄 Log Exporter</h2>

                <div class="export-format">
                    <h3 style="color: #4dd0e1; margin-bottom: 10px;">Select Export Format:</h3>
                    <div class="format-option">
                        <input type="radio" id="format-json" name="export-format" value="json" checked>
                        <label for="format-json">JSON</label>
                    </div>
                    <div class="format-option">
                        <input type="radio" id="format-csv" name="export-format" value="csv">
                        <label for="format-csv">CSV</label>
                    </div>
                    <div class="format-option">
                        <input type="radio" id="format-markdown" name="export-format" value="markdown">
                        <label for="format-markdown">Markdown</label>
                    </div>
                </div>

                <div class="config-field">
                    <label class="config-label" for="export-filename">Export Filename:</label>
                    <input type="text" id="export-filename" class="config-input" placeholder="smo_metrics_export" value="smo_metrics_export">
                </div>

                <div style="margin-top: 20px;">
                    <button class="button button-success" onclick="exportLogs()">📥 Export Logs</button>
                </div>

                <div id="export-status" style="margin-top: 20px;"></div>
            </div>
        </div>

        <script>
            // Tab switching functionality
            function switchTab(tabName) {
                // Hide all tabs
                document.querySelectorAll('.tab-content').forEach(tab => {
                    tab.classList.remove('active');
                });
                document.querySelectorAll('.tab-button').forEach(btn => {
                    btn.classList.remove('active');
                });

                // Show selected tab
                document.getElementById(tabName + '-tab').classList.add('active');
                event.target.classList.add('active');

                // Load config when switching to config tab
                if (tabName === 'config') {
                    loadConfig();
                }
            }

            // Notification system
            function showNotification(message, type = 'info') {
                const notification = document.createElement('div');
                notification.className = `notification ${type}`;
                notification.textContent = message;
                document.body.appendChild(notification);

                setTimeout(() => {
                    notification.remove();
                }, 3000);
            }

            // Config Editor Functions
            async function loadConfig() {
                try {
                    const response = await fetch('/api/config');
                    const config = await response.json();

                    const formHtml = generateConfigForm(config);
                    document.getElementById('config-form').innerHTML = formHtml;
                } catch (error) {
                    showNotification('Failed to load configuration: ' + error.message, 'error');
                }
            }

            function generateConfigForm(config, prefix = '') {
                let html = '';

                for (const [key, value] of Object.entries(config)) {
                    const fullKey = prefix ? `${prefix}.${key}` : key;

                    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                        html += `<div class="config-section">`;
                        html += `<div class="config-section-title">${key.replace(/_/g, ' ').toUpperCase()}</div>`;
                        html += generateConfigForm(value, fullKey);
                        html += `</div>`;
                    } else {
                        html += `<div class="config-field">`;
                        html += `<label class="config-label" for="config-${fullKey.replace(/\./g, '-')}">${key.replace(/_/g, ' ')}:</label>`;
                        html += `<input type="text" id="config-${fullKey.replace(/\./g, '-')}" class="config-input" value="${value}" data-key="${fullKey}">`;
                        html += `</div>`;
                    }
                }

                return html;
            }

            async function saveConfig() {
                try {
                    const inputs = document.querySelectorAll('#config-form input[data-key]');
                    const config = {};

                    inputs.forEach(input => {
                        const keys = input.dataset.key.split('.');
                        let current = config;

                        for (let i = 0; i < keys.length - 1; i++) {
                            if (!current[keys[i]]) {
                                current[keys[i]] = {};
                            }
                            current = current[keys[i]];
                        }

                        // Try to parse as boolean first, then number, otherwise keep as string
                        let value = input.value;
                        if (value === 'true' || value === 'false') {
                            value = value === 'true';
                        } else if (!isNaN(value) && value !== '' && value.trim() !== '') {
                            // Only convert to number if it's actually a numeric string
                            value = Number(value);
                        }

                        current[keys[keys.length - 1]] = value;
                    });

                    const response = await fetch('/api/config', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ config })
                    });

                    if (response.ok) {
                        showNotification('Configuration saved successfully!', 'success');
                    } else {
                        throw new Error('Failed to save configuration');
                    }
                } catch (error) {
                    showNotification('Failed to save configuration: ' + error.message, 'error');
                }
            }

            async function resetConfig() {
                if (!confirm('Are you sure you want to reset to default configuration?')) {
                    return;
                }

                try {
                    const response = await fetch('/api/config/reset', {
                        method: 'POST'
                    });

                    if (response.ok) {
                        showNotification('Configuration reset to defaults!', 'success');
                        loadConfig();
                    } else {
                        throw new Error('Failed to reset configuration');
                    }
                } catch (error) {
                    showNotification('Failed to reset configuration: ' + error.message, 'error');
                }
            }

            // Log Exporter Functions
            async function exportLogs() {
                try {
                    const format = document.querySelector('input[name="export-format"]:checked').value;
                    const filename = document.getElementById('export-filename').value || 'smo_metrics_export';

                    const response = await fetch(`/api/logs/export?format=${format}&filename=${filename}`);

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `${filename}.${format}`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);

                        showNotification('Logs exported successfully!', 'success');
                    } else {
                        throw new Error('Failed to export logs');
                    }
                } catch (error) {
                    showNotification('Failed to export logs: ' + error.message, 'error');
                }
            }

            function getUsageClass(value, type = 'general') {
                if (type === 'disk') {
                    if (value < 70) return 'good';
                    if (value < 90) return 'warning';
                    return 'critical';
                }
                if (value < 50) return 'good';
                if (value < 80) return 'warning';
                return 'critical';
            }

            function formatBytes(bytes, decimals = 2) {
                if (bytes === 0) return '0 B';
                const k = 1024;
                const dm = decimals < 0 ? 0 : decimals;
                const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
            }

            function createProgressBar(label, value, total = 100, unit = '%') {
                const percentage = total > 0 ? (value / total) * 100 : 0;
                const usageClass = getUsageClass(percentage, label.toLowerCase().includes('disk') ? 'disk' : 'general');

                return `
                    <div class="metric-row">
                        <div class="metric-label">${label}:</div>
                        <div class="metric-value">
                            <div class="progress-bar-container">
                                <div class="progress-bar bar-${usageClass}" style="width: ${percentage}%"></div>
                                <div class="progress-text">${value.toFixed(1)}${unit}</div>
                            </div>
                        </div>
                    </div>
                `;
            }

            function updateCPU(cpu) {
                if (!cpu) return;

                let html = '';

                // Average CPU
                const avg = cpu.average?.cpu_percent;
                if (avg) {
                    html += createProgressBar('Average CPU', avg.value || 0);
                }

                // Per-core CPU (show first 8 cores if available)
                const perCore = cpu.per_core;
                if (perCore) {
                    let coreCount = 0;
                    const coreGrid = [];

                    for (let key in perCore) {
                        if (coreCount < 8) {
                            const match = key.match(/^core_(\d+)_usage$/);
                            if (!match) continue; // Skip if pattern doesn't match exactly
                            const coreNum = match[1];
                            const usage = perCore[key]?.value || 0;
                            coreGrid.push(`
                                <div class="stat-item">
                                    <div class="stat-item-label">Core ${coreNum}</div>
                                    <div class="stat-item-value value-${getUsageClass(usage)}">${usage.toFixed(1)}%</div>
                                </div>
                            `);
                            coreCount++;
                        }
                    }

                    if (coreGrid.length > 0) {
                        html += '<div class="stat-grid">' + coreGrid.join('') + '</div>';
                    }
                }

                document.getElementById('cpu-content').innerHTML = html || '<div class="no-data">No CPU data available</div>';
            }

            function updateMemory(memory) {
                if (!memory) return;

                let html = '';

                // Virtual Memory
                const vmem = memory.virtual_memory;
                if (vmem) {
                    const percent = vmem.percent?.value || 0;
                    html += createProgressBar('Virtual Memory', percent);

                    html += `<div class="info-text">`;
                    if (vmem.total?.human_readable) html += `<span><strong>Total:</strong> ${vmem.total.human_readable}</span>`;
                    if (vmem.used?.human_readable) html += `<span class="value-warning"><strong>Used:</strong> ${vmem.used.human_readable}</span>`;
                    if (vmem.available?.human_readable) html += `<span class="value-good"><strong>Available:</strong> ${vmem.available.human_readable}</span>`;
                    html += `</div>`;
                }

                // Swap Memory
                const swap = memory.swap_memory;
                if (swap) {
                    const percent = swap.percent?.value || 0;
                    html += createProgressBar('Swap Memory', percent);

                    html += `<div class="info-text">`;
                    if (swap.total?.human_readable) html += `<span><strong>Total:</strong> ${swap.total.human_readable}</span>`;
                    if (swap.used?.human_readable) html += `<span class="value-warning"><strong>Used:</strong> ${swap.used.human_readable}</span>`;
                    if (swap.free?.human_readable) html += `<span class="value-good"><strong>Free:</strong> ${swap.free.human_readable}</span>`;
                    html += `</div>`;
                }

                document.getElementById('memory-content').innerHTML = html || '<div class="no-data">No memory data available</div>';
            }

            function updateDisk(disk) {
                if (!disk) return;

                let html = '';

                // Find partitions (exclude io_counters keys)
                const partitions = Object.keys(disk).filter(k => !k.includes('io_counters') && disk[k].metrics);

                partitions.forEach(partKey => {
                    const part = disk[partKey];
                    const metrics = part.metrics;

                    if (metrics && metrics.usage_percent) {
                        const usage = metrics.usage_percent.value || 0;
                        const mountpoint = part.mountpoint || partKey;

                        html += createProgressBar(mountpoint, usage);

                        html += `<div class="info-text">`;
                        if (metrics.total?.human_readable) html += `<span><strong>Total:</strong> ${metrics.total.human_readable}</span>`;
                        if (metrics.used?.human_readable) html += `<span class="value-warning"><strong>Used:</strong> ${metrics.used.human_readable}</span>`;
                        if (metrics.free?.human_readable) html += `<span class="value-good"><strong>Free:</strong> ${metrics.free.human_readable}</span>`;
                        html += `</div>`;
                    }
                });

                document.getElementById('disk-content').innerHTML = html || '<div class="no-data">No disk data available</div>';
            }

            function updateNetwork(network) {
                if (!network || !network.io_counters) return;

                const io = network.io_counters;
                let html = '<div class="stat-grid">';

                if (io.bytes_sent?.value !== undefined) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">📤 Bytes Sent</div>
                            <div class="stat-item-value value-info">${formatBytes(io.bytes_sent.value)}</div>
                        </div>
                    `;
                }

                if (io.bytes_recv?.value !== undefined) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">📥 Bytes Received</div>
                            <div class="stat-item-value value-good">${formatBytes(io.bytes_recv.value)}</div>
                        </div>
                    `;
                }

                if (io.packets_sent?.value !== undefined) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Packets Sent</div>
                            <div class="stat-item-value">${io.packets_sent.value.toLocaleString()}</div>
                        </div>
                    `;
                }

                if (io.packets_recv?.value !== undefined) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Packets Received</div>
                            <div class="stat-item-value">${io.packets_recv.value.toLocaleString()}</div>
                        </div>
                    `;
                }

                html += '</div>';

                document.getElementById('network-content').innerHTML = html;
            }

            function updateSystem(system) {
                if (!system) return;

                let html = '<div class="stat-grid">';

                if (system.hostname?.value) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Hostname</div>
                            <div class="stat-item-value">${system.hostname.value}</div>
                        </div>
                    `;
                }

                if (system.platform?.value) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Platform</div>
                            <div class="stat-item-value">${system.platform.value}</div>
                        </div>
                    `;
                }

                if (system.uptime?.human_readable) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Uptime</div>
                            <div class="stat-item-value value-good">${system.uptime.human_readable}</div>
                        </div>
                    `;
                }

                if (system.boot_time?.value) {
                    const bootDate = new Date(system.boot_time.value * 1000);
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Boot Time</div>
                            <div class="stat-item-value">${bootDate.toLocaleString()}</div>
                        </div>
                    `;
                }

                html += '</div>';

                document.getElementById('system-content').innerHTML = html;
            }

            function updateProcess(process) {
                if (!process || !process.agent_process) return;

                const agent = process.agent_process;
                let html = '<div class="stat-grid">';

                if (agent.pid?.value) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Process ID</div>
                            <div class="stat-item-value">${agent.pid.value}</div>
                        </div>
                    `;
                }

                if (agent.status?.value) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Status</div>
                            <div class="stat-item-value value-good">${agent.status.value}</div>
                        </div>
                    `;
                }

                if (agent.cpu_percent?.value !== undefined) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">CPU Usage</div>
                            <div class="stat-item-value value-${getUsageClass(agent.cpu_percent.value)}">${agent.cpu_percent.value.toFixed(1)}%</div>
                        </div>
                    `;
                }

                if (agent.memory_percent?.value !== undefined) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Memory Usage</div>
                            <div class="stat-item-value value-${getUsageClass(agent.memory_percent.value)}">${agent.memory_percent.value.toFixed(1)}%</div>
                        </div>
                    `;
                }

                if (agent.num_threads?.value) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Threads</div>
                            <div class="stat-item-value">${agent.num_threads.value}</div>
                        </div>
                    `;
                }

                html += '</div>';

                document.getElementById('process-content').innerHTML = html;
            }

            function updateAlerts(alerts) {
                const container = document.getElementById('alerts-container');

                if (!alerts || alerts.length === 0) {
                    container.innerHTML = '';
                    return;
                }

                let html = '<div class="alert-banner"><div class="alert-title">⚠️ Active Alerts</div>';
                alerts.forEach(alert => {
                    html += `<div class="alert-item">${alert}</div>`;
                });
                html += '</div>';

                container.innerHTML = html;
            }

            // WebSocket configuration
            const RECONNECT_DELAY_MS = 5000;
            const NO_DATA_TIMEOUT_MS = 10000;  // Show error if no data received after 10 seconds
            let reconnectAttempts = 0;
            let dataReceived = false;

            // Show connection error in all metric panels
            function showConnectionError(message) {
                const errorHtml = `
                    <div class="no-data" style="color: #ff6b6b;">
                        <div style="font-size: 2em; margin-bottom: 10px;">⚠️</div>
                        <div style="font-weight: bold; margin-bottom: 10px;">${message}</div>
                        <div style="color: #888; font-size: 0.9em;">
                            Check that InfluxDB is running and the agent is collecting metrics.<br>
                            See browser console for details.
                        </div>
                    </div>
                `;

                document.getElementById('cpu-content').innerHTML = errorHtml;
                document.getElementById('memory-content').innerHTML = errorHtml;
                document.getElementById('disk-content').innerHTML = errorHtml;
                document.getElementById('network-content').innerHTML = errorHtml;
                document.getElementById('system-content').innerHTML = errorHtml;
                document.getElementById('process-content').innerHTML = errorHtml;
            }

            // Determine WebSocket protocol based on page protocol
            const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            const ws = new WebSocket(wsProtocol + window.location.host + "/ws");

            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);

                    if (data.error) {
                        console.error('Error from server:', data.error);
                        showConnectionError(data.error);
                        if (data.suggestion) {
                            console.error('Suggestion:', data.suggestion);
                        }
                        if (data.url) {
                            console.error('InfluxDB URL:', data.url);
                        }
                        if (data.bucket) {
                            console.error('Bucket:', data.bucket);
                        }
                        return;
                    }

                    // Mark that we've received data
                    if (!dataReceived) {
                        dataReceived = true;
                        console.log('✓ Successfully connected to metrics stream');
                    }

                    // Update each metric group
                    if (data.cpu) updateCPU(data.cpu);
                    if (data.memory) updateMemory(data.memory);
                    if (data.disk) updateDisk(data.disk);
                    if (data.network) updateNetwork(data.network);
                    if (data.system) updateSystem(data.system);
                    if (data.process) updateProcess(data.process);
                    if (data.alerts) updateAlerts(data.alerts.active_alerts?.value);

                } catch (e) {
                    console.error('Error parsing metrics:', e);
                }
            };

            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                showConnectionError('WebSocket connection error');
            };

            ws.onclose = function() {
                console.log('WebSocket connection closed. Reconnecting in ' + (RECONNECT_DELAY_MS / 1000) + ' seconds...');
                reconnectAttempts++;

                if (!dataReceived) {
                    showConnectionError('Connection to metrics server lost');
                }

                setTimeout(() => {
                    location.reload();
                }, RECONNECT_DELAY_MS);
            };

            // Timeout to check if we've received any data
            setTimeout(() => {
                if (!dataReceived) {
                    console.warn(`No metrics data received after ${NO_DATA_TIMEOUT_MS / 1000} seconds`);
                    showConnectionError('No metrics data available');
                }
            }, NO_DATA_TIMEOUT_MS);
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

# Configuration API endpoints
@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    try:
        if not CONFIG_PATH.exists():
            raise HTTPException(status_code=404, detail="Configuration file not found")

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        return JSONResponse(content=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config")
async def update_config(config_update: ConfigUpdate):
    """Update configuration."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_update.config, f, default_flow_style=False, sort_keys=False)

        return JSONResponse(content={"status": "success", "message": "Configuration saved successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/reset")
async def reset_config():
    """Reset configuration to defaults."""
    try:
        # Default configuration (same as in agent.py)
        default_config = {
            "refresh": {"cpu": 2, "memory": 5, "disk": 10, "network": 5, "process": 2},
            "logging": {"format": "json"},
            "agent": {"snapshot_interval": 2},
            "display": {"show_snapshot_info": True, "pretty_max_depth": 2, "pretty_max_length": 1200},
            "alerts": {
                "cpu_percent": 80,
                "memory_percent": 85,
                "disk_usage": 90,
                "network_bytes_sent": 1000000
            }
        }

        # Try to import from agent module, fallback to hardcoded default
        try:
            from agent import DEFAULT_CONFIG
            default_config = DEFAULT_CONFIG
        except ImportError:
            pass  # Use hardcoded default above

        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(default_config, f, default_flow_style=False, sort_keys=False)

        return JSONResponse(content={"status": "success", "message": "Configuration reset to defaults"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Log export API endpoints
@app.get("/api/logs/export")
async def export_logs(format: str = "json", filename: str = "smo_metrics_export"):
    """Export logs in specified format."""
    try:
        # Validate format against allowlist and map to safe file extensions
        format_mapping = {
            "json": {"ext": "json", "media": "application/json"},
            "csv": {"ext": "csv", "media": "text/csv"},
            "markdown": {"ext": "md", "media": "text/markdown"}
        }

        if format not in format_mapping:
            raise HTTPException(status_code=400, detail=f"Invalid format. Use one of: {', '.join(format_mapping.keys())}")

        format_info = format_mapping[format]

        if not METRICS_LOG_PATH.exists():
            raise HTTPException(status_code=404, detail="Metrics log file not found")

        # Read all logs
        logs = []
        with open(METRICS_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        if not logs:
            raise HTTPException(status_code=404, detail="No logs to export")

        # Generate export file
        if format == "json":
            content = json.dumps(logs, indent=2)
        elif format == "csv":
            content = _logs_to_csv(logs)
        elif format == "markdown":
            content = _logs_to_markdown(logs)

        # Create temporary file for download with cleanup task
        # Use validated extension from mapping to prevent path injection
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'.{format_info["ext"]}') as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Cleanup function to remove temp file after response
        def cleanup():
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        return FileResponse(
            tmp_path,
            media_type=format_info["media"],
            filename=f"{filename}.{format_info['ext']}",
            background=BackgroundTask(cleanup)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> dict:
    """Flatten a nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def _logs_to_csv(logs: list) -> str:
    """Convert logs to CSV format."""
    flat_logs = [_flatten_dict(log) for log in logs]
    if not flat_logs:
        return ""

    # Get all unique headers
    headers = sorted(list(set(key for log in flat_logs for key in log.keys())))

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(flat_logs)

    return output.getvalue()

def _logs_to_markdown(logs: list) -> str:
    """Convert logs to Markdown table format."""
    flat_logs = [_flatten_dict(log) for log in logs]
    if not flat_logs:
        return ""

    headers = sorted(list(set(key for log in flat_logs for key in log.keys())))

    # Create markdown table
    lines = []
    lines.append(f"| {' | '.join(headers)} |")
    lines.append(f"| {' | '.join(['---'] * len(headers))} |")

    for log in flat_logs:
        row = [str(log.get(h, '')) for h in headers]
        lines.append(f"| {' | '.join(row)} |")

    return '\n'.join(lines)

def _unflatten_fields(flat_dict):
    """Convert flat field names back to nested structure.

    Example: {'average_cpu_percent_value': 45.2} -> {'average': {'cpu_percent': {'value': 45.2}}}
    """
    result = {}
    for key, value in flat_dict.items():
        parts = key.split('_')
        current = result

        # Navigate/create nested structure
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the final value
        current[parts[-1]] = {'value': value}

    return result

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    url = os.environ.get("INFLUXDB_URL", "http://smo-db:8086")
    token = os.environ.get("INFLUXDB_TOKEN", "my-super-secret-token")
    org = os.environ.get("INFLUXDB_ORG", "my-org")
    bucket = os.environ.get("INFLUXDB_BUCKET", "smo-metrics")

    # Log connection attempt for debugging
    print(f"WebSocket connecting to InfluxDB at {url}")
    print(f"  Organization: {org}")
    print(f"  Bucket: {bucket}")
    print(f"  Token: {'*' * max(0, len(token) - 10) + token[-10:] if len(token) > 10 else '***'}")

    try:
        async with InfluxDBClientAsync(url=url, token=token, org=org) as client:
            query_api = client.query_api()

            while True:
                try:
                    query = f'from(bucket: "{bucket}") |> range(start: -1m) |> last()'
                    tables = await query_api.query(query)

                    results = {}
                    for table in tables:
                        for record in table.records:
                            measurement = record.get_measurement()
                            field = record.get_field()
                            value = record.get_value()
                            if measurement not in results:
                                results[measurement] = {}
                            results[measurement][field] = value

                    # Unflatten each measurement's fields back to nested structure
                    unflattened_results = {}
                    for measurement, flat_fields in results.items():
                        unflattened_results[measurement] = _unflatten_fields(flat_fields)

                    await websocket.send_text(json.dumps(unflattened_results, indent=2))
                except WebSocketDisconnect:
                    print("WebSocket client disconnected")
                    break
                except Exception as e:
                    error_msg = str(e)
                    print(f"Error querying InfluxDB: {error_msg}")
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_text(json.dumps({
                            "error": f"InfluxDB query error: {error_msg}",
                            "url": url,
                            "bucket": bucket
                        }))
                    else:
                        break

                await asyncio.sleep(1)
    except Exception as e:
        error_msg = str(e)
        print(f"Failed to connect to InfluxDB: {error_msg}")
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps({
                    "error": f"Failed to connect to InfluxDB at {url}: {error_msg}",
                    "url": url,
                    "suggestion": "Check that InfluxDB is running and credentials are correct"
                }))
        except:
            pass

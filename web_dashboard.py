from fastapi import FastAPI, WebSocket, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
import json
import os
import yaml
import tempfile
import time
import platform
import socket
import psutil
from pathlib import Path
from starlette.websockets import WebSocketDisconnect, WebSocketState
from starlette.background import BackgroundTask
from typing import Dict, Any
import csv
from io import StringIO
from dotenv import load_dotenv
from config_loader import load_config, save_config, get_config_path, DEFAULT_CONFIG

app = FastAPI()

# Configuration paths
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = get_config_path()
METRICS_LOG_PATH = PROJECT_ROOT / "logs" / "smo_metrics.jsonl"

# Load environment variables from .env file if it exists
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
            @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&display=swap');

            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Manrope', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: radial-gradient(140% 140% at 10% 10%, #1c2342 0%, #0f1224 40%, #0a0c18 75%);
                color: #f6f7fb;
                padding: 32px 16px;
                line-height: 1.6;
            }

            .page {
                max-width: 1380px;
                margin: 0 auto;
            }

            .header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                margin-bottom: 24px;
                padding: 18px 20px;
                background: rgba(18, 22, 44, 0.85);
                border-radius: 16px;
                border: 1px solid rgba(112, 143, 255, 0.15);
                box-shadow: 0 12px 36px rgba(0,0,0,0.35);
            }

            .header-left h1 {
                color: #e8ecff;
                font-size: 1.9em;
                margin-bottom: 4px;
                letter-spacing: 0.2px;
            }

            .subtitle {
                color: #9fb2d5;
                font-size: 0.98em;
            }

            .header-badges {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }

            .badge {
                background: rgba(111, 169, 255, 0.12);
                border: 1px solid rgba(111, 169, 255, 0.25);
                color: #cfe1ff;
                border-radius: 12px;
                padding: 10px 12px;
                font-weight: 600;
                font-size: 0.95em;
            }

            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
                gap: 14px;
                margin-bottom: 14px;
            }

            .metric-group {
                background: rgba(14, 16, 30, 0.85);
                border: 1px solid rgba(120, 145, 255, 0.14);
                border-radius: 14px;
                padding: 14px 14px 18px 14px;
                box-shadow: 0 10px 28px rgba(0,0,0,0.33);
                transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
            }

            .metric-group:hover {
                transform: translateY(-2px);
                border-color: rgba(169, 196, 255, 0.4);
                box-shadow: 0 14px 34px rgba(0,0,0,0.38);
            }

            .metric-group-title {
                display: flex;
                align-items: center;
                justify-content: space-between;
                color: #e9edff;
                padding: 8px 10px;
                margin: -6px -4px 12px -4px;
                font-weight: 700;
                font-size: 1.05em;
                letter-spacing: 0.1px;
            }

            .metric-row {
                display: flex;
                align-items: center;
                margin-bottom: 12px;
                padding: 4px 0;
                gap: 12px;
            }

            .metric-label {
                font-weight: 700;
                color: #c4d4ff;
                min-width: 120px;
                font-size: 0.92em;
            }

            .metric-value {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 4px;
            }

            .progress-bar-container {
                width: 100%;
                height: 18px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                overflow: hidden;
                border: 1px solid rgba(255,255,255,0.06);
                position: relative;
            }

            .progress-bar {
                height: 100%;
                border-radius: 12px;
                transition: width 0.35s ease, background 0.3s ease;
                position: relative;
                background: linear-gradient(90deg, var(--bar-color), var(--bar-color-light));
            }

            .progress-text {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-weight: 700;
                font-size: 0.8em;
                color: #eaf0ff;
                letter-spacing: 0.1px;
                z-index: 1;
            }

            .info-text {
                color: #a9b5d5;
                font-size: 0.86em;
                margin-top: 2px;
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }

            .info-text span {
                margin-right: 0;
            }

            .value-good { color: #6fe3a6; }
            .value-warning { color: #ffb84d; }
            .value-critical { color: #ff6b6b; }
            .value-info { color: #7ac6ff; }

            .bar-good {
                --bar-color: #4acb8a;
                --bar-color-light: #5fe3a6;
            }
            .bar-warning {
                --bar-color: #ffad42;
                --bar-color-light: #ffc76a;
            }
            .bar-critical {
                --bar-color: #f75c7a;
                --bar-color-light: #ff7b97;
            }

            .stat-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 8px;
                margin-top: 8px;
            }

            .stat-item {
                background: rgba(255,255,255,0.03);
                padding: 10px 12px;
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.04);
            }

            .stat-item-label {
                color: #9fb2d5;
                font-size: 0.82em;
                margin-bottom: 2px;
            }

            .stat-item-value {
                font-weight: 700;
                font-size: 1.04em;
                color: #dfe8ff;
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
                display: inline-flex;
                gap: 8px;
                padding: 6px;
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 12px;
                margin-bottom: 18px;
            }

            .tab-button {
                background: transparent;
                border: 1px solid transparent;
                color: #9fb2d5;
                padding: 10px 14px;
                cursor: pointer;
                border-radius: 10px;
                font-size: 0.95em;
                font-weight: 700;
                transition: all 0.2s ease;
            }

            .tab-button:hover {
                color: #e9edff;
                border-color: rgba(255,255,255,0.12);
                background: rgba(255,255,255,0.04);
            }

            .tab-button.active {
                color: #111321;
                background: linear-gradient(135deg, #8ec5ff, #70a2ff);
                border-color: transparent;
                box-shadow: 0 8px 20px rgba(0,0,0,0.25);
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
        <div class="page">
            <div class="header">
                <div class="header-left">
                    <h1>SMO Dashboard</h1>
                    <div class="subtitle">System monitoring & live orchestration</div>
                </div>
                <div class="header-badges">
                    <div class="badge" id="badge-uptime">Live</div>
                    <div class="badge" id="badge-refresh">1s refresh</div>
                </div>
            </div>

            <!-- Tab Navigation -->
            <div class="tabs">
                <button class="tab-button active" onclick="switchTab('metrics')">Live Metrics</button>
                <button class="tab-button" onclick="switchTab('config')">Config</button>
                <button class="tab-button" onclick="switchTab('logs')">Exports</button>
            </div>

            <!-- Live Metrics Tab -->
            <div id="metrics-tab" class="tab-content active">
                <div id="alerts-container"></div>

                <div class="dashboard-grid">
                <div class="metric-group" id="cpu-group">
                    <div class="metric-group-title">CPU Stats</div>
                    <div id="cpu-content" class="no-data">
                        <div class="loading"></div> Loading CPU data...
                    </div>
                </div>

                <div class="metric-group" id="memory-group">
                    <div class="metric-group-title">Memory</div>
                    <div id="memory-content" class="no-data">
                        <div class="loading"></div> Loading memory data...
                    </div>
                </div>

                <div class="metric-group" id="disk-group">
                    <div class="metric-group-title">Disk Usage</div>
                    <div id="disk-content" class="no-data">
                        <div class="loading"></div> Loading disk data...
                    </div>
                </div>

                <div class="metric-group" id="network-group">
                    <div class="metric-group-title">Network I/O</div>
                    <div id="network-content" class="no-data">
                        <div class="loading"></div> Loading network data...
                    </div>
                </div>

                <div class="metric-group" id="system-group">
                    <div class="metric-group-title">System Info</div>
                    <div id="system-content" class="no-data">
                        <div class="loading"></div> Loading system data...
                    </div>
                </div>

                <div class="metric-group" id="process-group">
                    <div class="metric-group-title">Process Metrics</div>
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

                // CPU Count and Frequency
                const count = cpu.count?.count;
                const freq = cpu.frequency?.current_freq;
                if (count || freq) {
                    html += '<div class="stat-grid">';
                    if (count?.value) {
                        const countVal = count.value;
                        if (typeof countVal === 'object') {
                            html += `
                                <div class="stat-item">
                                    <div class="stat-item-label">Physical Cores</div>
                                    <div class="stat-item-value">${countVal.physical || 'N/A'}</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-item-label">Logical Cores</div>
                                    <div class="stat-item-value">${countVal.logical || 'N/A'}</div>
                                </div>
                            `;
                        } else {
                            html += `
                                <div class="stat-item">
                                    <div class="stat-item-label">CPU Cores</div>
                                    <div class="stat-item-value">${count.value}</div>
                                </div>
                            `;
                        }
                    }
                    if (freq?.value) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Frequency</div>
                                <div class="stat-item-value">${(freq.value).toFixed(0)} MHz</div>
                            </div>
                        `;
                    }
                    html += '</div>';
                }

                // Load Average
                const load = cpu.load?.load_average;
                if (load && load.value) {
                    const loadVal = load.value;
                    html += '<div class="stat-grid">';
                    if (loadVal['1min'] !== undefined) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Load (1m)</div>
                                <div class="stat-item-value">${loadVal['1min'].toFixed(2)}</div>
                            </div>
                        `;
                    }
                    if (loadVal['5min'] !== undefined) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Load (5m)</div>
                                <div class="stat-item-value">${loadVal['5min'].toFixed(2)}</div>
                            </div>
                        `;
                    }
                    if (loadVal['15min'] !== undefined) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Load (15m)</div>
                                <div class="stat-item-value">${loadVal['15min'].toFixed(2)}</div>
                            </div>
                        `;
                    }
                    html += '</div>';
                }

                // CPU Stats (context switches, interrupts, etc.)
                const stats = cpu.stats;
                if (stats) {
                    html += '<div style="margin-top: 10px;"><strong>CPU Statistics:</strong></div>';
                    html += '<div class="stat-grid">';
                    
                    if (stats.ctx_switches?.value !== undefined) {
                        const ctxVal = stats.ctx_switches.value;
                        const formatted = ctxVal >= 1000000 ? (ctxVal / 1000000).toFixed(2) + 'M' : 
                                        ctxVal >= 1000 ? (ctxVal / 1000).toFixed(2) + 'K' : ctxVal;
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Context Switches</div>
                                <div class="stat-item-value">${formatted}</div>
                            </div>
                        `;
                    }
                    
                    if (stats.interrupts?.value !== undefined) {
                        const intVal = stats.interrupts.value;
                        const formatted = intVal >= 1000000 ? (intVal / 1000000).toFixed(2) + 'M' : 
                                        intVal >= 1000 ? (intVal / 1000).toFixed(2) + 'K' : intVal;
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Interrupts</div>
                                <div class="stat-item-value">${formatted}</div>
                            </div>
                        `;
                    }
                    
                    if (stats.soft_interrupts?.value !== undefined) {
                        const sintVal = stats.soft_interrupts.value;
                        const formatted = sintVal >= 1000000 ? (sintVal / 1000000).toFixed(2) + 'M' : 
                                        sintVal >= 1000 ? (sintVal / 1000).toFixed(2) + 'K' : sintVal;
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Soft Interrupts</div>
                                <div class="stat-item-value">${formatted}</div>
                            </div>
                        `;
                    }
                    
                    if (stats.syscalls?.value !== undefined) {
                        const sysVal = stats.syscalls.value;
                        const formatted = sysVal >= 1000000 ? (sysVal / 1000000).toFixed(2) + 'M' : 
                                        sysVal >= 1000 ? (sysVal / 1000).toFixed(2) + 'K' : sysVal;
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Syscalls</div>
                                <div class="stat-item-value">${formatted}</div>
                            </div>
                        `;
                    }
                    
                    html += '</div>';
                }

                // Per-core CPU (show all cores)
                const perCore = cpu.per_core;
                if (perCore) {
                    const coreGrid = [];

                    for (let key in perCore) {
                        const match = key.match(/^core_(\d+)_usage$/);
                        if (!match) continue;
                        const coreNum = match[1];
                        const usage = perCore[key]?.value || 0;
                        coreGrid.push(`
                            <div class="stat-item">
                                <div class="stat-item-label">Core ${coreNum}</div>
                                <div class="stat-item-value value-${getUsageClass(usage)}">${usage.toFixed(1)}%</div>
                            </div>
                        `);
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
                        const device = part.device || partKey;
                        const fstype = part.fstype || 'N/A';

                        html += createProgressBar(mountpoint, usage);

                        html += `<div class="info-text">`;
                        if (metrics.total?.human_readable) html += `<span><strong>Total:</strong> ${metrics.total.human_readable}</span>`;
                        if (metrics.used?.human_readable) html += `<span class="value-warning"><strong>Used:</strong> ${metrics.used.human_readable}</span>`;
                        if (metrics.free?.human_readable) html += `<span class="value-good"><strong>Free:</strong> ${metrics.free.human_readable}</span>`;
                        html += `</div>`;
                        
                        html += '<div class="info-text" style="margin-top: 5px;">';
                        html += `<span><strong>FS:</strong> ${fstype}</span>`;
                        html += `<span><strong>Device:</strong> ${device}</span>`;
                        html += '</div>';
                    }
                });

                // System-wide I/O Counters
                const ioCounters = disk.io_counters?.metrics;
                if (ioCounters) {
                    html += '<div style="margin-top: 15px;"><strong>Disk I/O Statistics:</strong></div>';
                    html += '<div class="stat-grid">';
                    
                    if (ioCounters.read_count?.value !== undefined) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Read Count</div>
                                <div class="stat-item-value">${ioCounters.read_count.value.toLocaleString()}</div>
                            </div>
                        `;
                    }
                    
                    if (ioCounters.write_count?.value !== undefined) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Write Count</div>
                                <div class="stat-item-value">${ioCounters.write_count.value.toLocaleString()}</div>
                            </div>
                        `;
                    }
                    
                    if (ioCounters.read_bytes?.human_readable) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Read Bytes</div>
                                <div class="stat-item-value">${ioCounters.read_bytes.human_readable}</div>
                            </div>
                        `;
                    }
                    
                    if (ioCounters.write_bytes?.human_readable) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Write Bytes</div>
                                <div class="stat-item-value">${ioCounters.write_bytes.human_readable}</div>
                            </div>
                        `;
                    }
                    
                    html += '</div>';
                }

                document.getElementById('disk-content').innerHTML = html || '<div class="no-data">No disk data available</div>';
            }

            function updateNetwork(network) {
                if (!network) return;

                let html = '';

                // Overall I/O Counters
                const io = (network.io_counters && network.io_counters.metrics) || network.io_counters;
                if (io) {
                    html += '<div class="stat-grid">';

                    const bytesSent = io.bytes_sent?.value ?? io.bytes_sent;
                    const bytesRecv = io.bytes_recv?.value ?? io.bytes_recv;
                    const packetsSent = io.packets_sent?.value ?? io.packets_sent;
                    const packetsRecv = io.packets_recv?.value ?? io.packets_recv;
                    const errIn = io.errin?.value ?? io.errin;
                    const errOut = io.errout?.value ?? io.errout;
                    const dropIn = io.dropin?.value ?? io.dropin;
                    const dropOut = io.dropout?.value ?? io.dropout;

                    if (bytesSent !== undefined) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">📤 Bytes Sent</div>
                                <div class="stat-item-value value-info">${formatBytes(bytesSent)}</div>
                            </div>
                        `;
                    }

                    if (bytesRecv !== undefined) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">📥 Bytes Received</div>
                                <div class="stat-item-value value-good">${formatBytes(bytesRecv)}</div>
                            </div>
                        `;
                    }

                    if (packetsSent !== undefined) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Packets Sent</div>
                                <div class="stat-item-value">${packetsSent.toLocaleString()}</div>
                            </div>
                        `;
                    }

                    if (packetsRecv !== undefined) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Packets Received</div>
                                <div class="stat-item-value">${packetsRecv.toLocaleString()}</div>
                            </div>
                        `;
                    }

                    if (errIn !== undefined || errOut !== undefined) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Errors (In/Out)</div>
                                <div class="stat-item-value value-warning">${errIn || 0} / ${errOut || 0}</div>
                            </div>
                        `;
                    }

                    if (dropIn !== undefined || dropOut !== undefined) {
                        html += `
                            <div class="stat-item">
                                <div class="stat-item-label">Drops (In/Out)</div>
                                <div class="stat-item-value value-warning">${dropIn || 0} / ${dropOut || 0}</div>
                            </div>
                        `;
                    }

                    html += '</div>';
                }

                // Active Network Interfaces (addresses from interfaces section)
                const ifaceAddresses = (network.interfaces && network.interfaces.interfaces) || network.interfaces;
                if (ifaceAddresses && typeof ifaceAddresses === 'object') {
                    html += '<div style="margin-top: 15px;"><strong>Active Network Interfaces:</strong></div>';
                    html += '<div class="stat-grid">';

                    for (const [iface, ifaceData] of Object.entries(ifaceAddresses)) {
                        const addresses = ifaceData.addresses || [];
                        let ipv4 = '';
                        let mac = '';
                        for (const addr of addresses) {
                            if (addr.family === 2 || addr.family === "2") {
                                ipv4 = addr.address;
                            }
                            if (addr.family === 17 || addr.family === "17" || addr.family === "-1") {
                                mac = addr.address;
                            }
                        }

                        if (ipv4 || mac) {
                            html += `
                                <div class="stat-item" style="grid-column: span 2;">
                                    <div class="stat-item-label">${iface}</div>
                                    <div class="stat-item-value" style="font-size: 0.9em;">
                                        ${ipv4 ? 'IP: ' + ipv4 : ''}
                                        ${ipv4 && mac ? ' | ' : ''}
                                        ${mac ? 'MAC: ' + mac : ''}
                                    </div>
                                </div>
                            `;
                        }
                    }
                    html += '</div>';
                }

                document.getElementById('network-content').innerHTML = html || '<div class="no-data">No network data available</div>';
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

                if (system.os_release?.value) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">OS Release</div>
                            <div class="stat-item-value">${system.os_release.value}</div>
                        </div>
                    `;
                }

                if (system.architecture?.value) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Architecture</div>
                            <div class="stat-item-value">${system.architecture.value}</div>
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
                if (!process) return;

                const agent = process.agent_process || process;
                let html = '<div class="stat-grid">';

                const pid = agent.pid?.value ?? agent.pid;
                if (pid) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Process ID</div>
                            <div class="stat-item-value">${pid}</div>
                        </div>
                    `;
                }

                const status = agent.status?.value ?? agent.status;
                if (status) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Status</div>
                            <div class="stat-item-value value-good">${status}</div>
                        </div>
                    `;
                }

                const cpuPct = agent.cpu_percent?.value ?? agent.cpu_percent;
                if (cpuPct !== undefined) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">CPU Usage</div>
                            <div class="stat-item-value value-${getUsageClass(cpuPct)}">${Number(cpuPct).toFixed(1)}%</div>
                        </div>
                    `;
                }

                const memPct = agent.memory_percent?.value ?? agent.memory_percent;
                if (memPct !== undefined) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Memory Usage</div>
                            <div class="stat-item-value value-${getUsageClass(memPct)}">${Number(memPct).toFixed(1)}%</div>
                        </div>
                    `;
                }

                const threads = agent.num_threads?.value ?? agent.num_threads ?? agent.threads?.count?.value;
                if (threads) {
                    html += `
                        <div class="stat-item">
                            <div class="stat-item-label">Threads</div>
                            <div class="stat-item-value">${threads}</div>
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
                            Check that the agent is running and collecting metrics.<br>
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

                    // Handle info messages (e.g., waiting for data)
                    if (data.info) {
                        console.log('Info:', data.info);
                        // Don't mark as error, just wait
                        return;
                    }

                    if (data.error) {
                        console.error('Error from server:', data.error);
                        showConnectionError(data.error);
                        if (data.suggestion) {
                            console.error('Suggestion:', data.suggestion);
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

# Server-side helpers to enrich snapshots for the web UI
def _build_system_info():
    try:
        boot_ts = psutil.boot_time()
        now = time.time()
        return {
            "hostname": {"value": socket.gethostname()},
            "platform": {"value": platform.system()},
            "os_release": {"value": platform.release()},
            "architecture": {"value": platform.machine()},
            "uptime": {"human_readable": _format_seconds(now - boot_ts)},
            "boot_time": {"value": boot_ts},
        }
    except Exception:
        return None


def _format_seconds(seconds: float) -> str:
    secs = int(seconds)
    mins, sec = divmod(secs, 60)
    hrs, mins = divmod(mins, 60)
    days, hrs = divmod(hrs, 24)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hrs:
        parts.append(f"{hrs}h")
    if mins:
        parts.append(f"{mins}m")
    if sec or not parts:
        parts.append(f"{sec}s")
    return " ".join(parts)


def _normalize_process_payload(snapshot: dict) -> dict:
    proc = snapshot.get("process")
    if not proc or "agent_process" in proc:
        return snapshot

    cpu_percent = None
    if isinstance(proc.get("cpu"), dict):
        cpu_percent = proc["cpu"].get("value")
    if cpu_percent is None:
        cpu_percent = proc.get("cpu_percent", {}).get("value")

    mem_percent = None
    if isinstance(proc.get("memory"), dict):
        mem_percent = proc["memory"].get("percent", {}).get("value")

    threads = None
    if isinstance(proc.get("threads"), dict):
        threads = proc["threads"].get("count", {}).get("value")

    agent_process = {
        "pid": {"value": proc.get("pid")},
        "status": {"value": proc.get("status", "running")},
        "cpu_percent": {"value": cpu_percent} if cpu_percent is not None else None,
        "memory_percent": {"value": mem_percent} if mem_percent is not None else None,
        "num_threads": {"value": threads} if threads is not None else None,
    }

    # Drop Nones to keep payload small
    agent_process = {k: v for k, v in agent_process.items() if v is not None}
    proc = dict(proc)
    proc["agent_process"] = agent_process
    snapshot["process"] = proc
    return snapshot

@app.get("/")
async def get():
    return HTMLResponse(html)

# Simple favicon placeholder to avoid 404 noise
@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

# Configuration API endpoints
@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    try:
        config = load_config()
        return JSONResponse(content=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config")
async def update_config(config_update: ConfigUpdate):
    """Update configuration."""
    try:
        if save_config(config_update.config):
            return JSONResponse(content={"status": "success", "message": "Configuration saved successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/reset")
async def reset_config():
    """Reset configuration to defaults."""
    try:
        if save_config(DEFAULT_CONFIG):
            return JSONResponse(content={"status": "success", "message": "Configuration reset to defaults"})
        else:
            raise HTTPException(status_code=500, detail="Failed to reset configuration")
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

        # Read all logs with tolerant parsing (skip malformed lines)
        logs = []
        skipped = 0
        with open(METRICS_LOG_PATH, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                try:
                    # Strip potential BOM
                    if line and line[0] == "\ufeff":
                        line = line.lstrip("\ufeff")

                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        # Fallback: extract JSON object substring if the line has prefixes
                        start = line.find("{")
                        end = line.rfind("}")
                        if start != -1 and end != -1 and end > start:
                            record = json.loads(line[start:end+1])
                        else:
                            raise
                    logs.append(record)
                except Exception:
                    skipped += 1

        if skipped:
            print(f"[export_logs] skipped {skipped} malformed log line(s)")

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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that streams metrics from the JSON log file.
    
    This implementation reads directly from the metrics log file for real-time updates.
    """
    await websocket.accept()

    print(f"WebSocket client connected - streaming from {METRICS_LOG_PATH}")

    parse_failures = 0
    try:
        while True:
            try:
                # Read the last line from the metrics log file (most recent snapshot)
                if not METRICS_LOG_PATH.exists():
                    await websocket.send_text(json.dumps({
                        "error": "Metrics log file not found",
                        "suggestion": "Make sure the agent is running and collecting metrics"
                    }))
                    await asyncio.sleep(2)
                    continue

                # Read the most recent metrics snapshot from the log file
                # Use a more efficient approach to read the last line
                last_line = None
                try:
                    with open(METRICS_LOG_PATH, "rb") as f:
                        # Seek to end of file
                        f.seek(0, 2)
                        file_size = f.tell()
                        
                        # If file is empty, nothing to read
                        if file_size == 0:
                            await asyncio.sleep(1)
                            continue
                        
                        # Read backwards to find the last complete line
                        # Use a generous 1MB chunk to handle very large JSON lines (observed ~75KB)
                        # while still bounding memory use for frequent reads
                        chunk_size = min(1024 * 1024, file_size)
                        f.seek(max(0, file_size - chunk_size))
                        
                        # Read the chunk and split into lines
                        chunk = f.read().decode('utf-8', errors='ignore')
                        lines = chunk.strip().split('\n')
                        
                        # Skip the first line if we started mid-file (it's likely incomplete)
                        # Get the last complete line
                        if len(lines) > 1 and file_size > chunk_size:
                            # We started in the middle, skip first partial line
                            lines = lines[1:]
                        
                        # Get the last non-empty line
                        for line in reversed(lines):
                            if line.strip():
                                last_line = line
                                break
                except IOError as e:
                    print(f"Error reading metrics file: {e}")
                    await asyncio.sleep(1)
                    continue

                # Try to parse the most recent valid line (scan backwards)
                parsed = None

                def _try_parse(text: str):
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        start = text.find("{")
                        end = text.rfind("}")
                        if start != -1 and end != -1 and end > start:
                            return json.loads(text[start:end+1])
                        # As a last resort, try parsing from the last '{' to end (handles concatenated objects)
                        last = text.rfind("{")
                        if last != -1:
                            return json.loads(text[last:])
                        raise

                for candidate in reversed(lines):
                    candidate = candidate.strip()
                    if not candidate:
                        continue
                    if candidate.startswith("\ufeff"):
                        candidate = candidate.lstrip("\ufeff")
                    try:
                        parsed = _try_parse(candidate)
                        break
                    except Exception:
                        continue

                if parsed is not None:
                    parse_failures = 0
                    parsed = _normalize_process_payload(parsed)
                    if "system" not in parsed:
                        sys_info = _build_system_info()
                        if sys_info:
                            parsed["system"] = sys_info
                    await websocket.send_text(json.dumps(parsed, indent=2))
                else:
                    parse_failures += 1
                    if parse_failures <= 3 or parse_failures % 20 == 0:
                        print(f"Warning: no valid metrics lines found ({parse_failures})")
                    if parse_failures % 10 == 0:
                        await websocket.send_text(json.dumps({
                            "info": "Waiting for a valid metrics line...",
                            "suggestion": "Ensure the agent writes valid JSON lines to logs/smo_metrics.jsonl"
                        }))
                    else:
                        # Avoid flooding; small delay already at loop end
                        pass

            except WebSocketDisconnect:
                print("WebSocket client disconnected")
                break
            except Exception as e:
                error_msg = str(e)
                print(f"Error streaming metrics: {error_msg}")
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps({
                        "error": f"Error streaming metrics: {error_msg}"
                    }))
                else:
                    break

            # Wait before reading the next snapshot (1 second refresh rate)
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        # Graceful shutdown
        pass
    except Exception as e:
        error_msg = str(e)
        print(f"WebSocket error: {error_msg}")
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps({
                    "error": f"WebSocket error: {error_msg}"
                }))
        except Exception:
            pass

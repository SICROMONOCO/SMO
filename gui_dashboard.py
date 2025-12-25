#!/usr/bin/env python3
"""
SMO GUI Dashboard
-----------------
A web-based GUI control panel (like XAMPP) for the SMO system monitoring tool.

Features:
  - Start/Stop SMO Agent
  - Start/Stop Web Dashboard  
  - Real-time status monitoring
  - Configuration editor
  - Logs viewer
  - System metrics display
  - Modern responsive web interface
"""

from fastapi import FastAPI, WebSocket, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess
import platform
import os
import sys
import asyncio
import json
import yaml
from pathlib import Path
from datetime import datetime
import psutil
from typing import Dict, Any, Optional
import signal

# Get project root
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config_loader import load_config, save_config, get_config_path

# Create FastAPI app
app = FastAPI(title="SMO GUI Dashboard", version="1.0.0")

# Global process tracking
processes: Dict[str, Optional[subprocess.Popen]] = {
    'agent': None,
    'web': None
}

# Models
class ConfigUpdate(BaseModel):
    config: Dict[str, Any]

class ServiceControl(BaseModel):
    action: str  # 'start' or 'stop'

def get_process_info(pid: int) -> Optional[Dict[str, Any]]:
    """Get information about a running process."""
    try:
        proc = psutil.Process(pid)
        return {
            'pid': pid,
            'name': proc.name(),
            'status': proc.status(),
            'cpu_percent': proc.cpu_percent(interval=0.1),
            'memory_mb': proc.memory_info().rss / (1024 * 1024),
            'create_time': proc.create_time()
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def is_process_running(process: Optional[subprocess.Popen]) -> bool:
    """Check if a process is running."""
    if process is None:
        return False
    return process.poll() is None

def kill_process_tree(pid: int):
    """Kill a process and all its children."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        
        parent.terminate()
        
        # Wait for termination
        gone, alive = psutil.wait_procs([parent] + children, timeout=3)
        
        # Force kill if still alive
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the main dashboard HTML."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMO Control Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }
        
        .service-item {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }
        
        .service-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .service-title {
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }
        
        .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .status.running {
            background: #d4edda;
            color: #155724;
        }
        
        .status.stopped {
            background: #f8d7da;
            color: #721c24;
        }
        
        .service-desc {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 15px;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
        }
        
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .btn-start {
            background: #28a745;
            color: white;
        }
        
        .btn-stop {
            background: #dc3545;
            color: white;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-info {
            background: #17a2b8;
            color: white;
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 15px;
        }
        
        .metric {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
        }
        
        .metric-label {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }
        
        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
        }
        
        .logs-container {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 15px;
        }
        
        .log-entry {
            margin-bottom: 10px;
            padding: 5px;
            border-left: 3px solid #667eea;
            padding-left: 10px;
        }
        
        .log-time {
            color: #4ec9b0;
        }
        
        textarea {
            width: 100%;
            min-height: 300px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            margin: 15px 0;
        }
        
        .quick-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        .full-width {
            grid-column: 1 / -1;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1em;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
        }
        
        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 SMO Control Panel</h1>
            <p>System Monitoring & Orchestration Dashboard</p>
        </div>
        
        <div class="dashboard-grid">
            <!-- Services Control -->
            <div class="card">
                <h2>📊 Services Control</h2>
                
                <!-- Agent Service -->
                <div class="service-item">
                    <div class="service-header">
                        <div class="service-title">🤖 SMO Agent</div>
                        <span class="status" id="agent-status">Checking...</span>
                    </div>
                    <div class="service-desc">Collects system metrics continuously</div>
                    <div class="button-group">
                        <button class="btn-start" onclick="startService('agent')">▶️ Start</button>
                        <button class="btn-stop" onclick="stopService('agent')">⏹️ Stop</button>
                    </div>
                </div>
                
                <!-- Web Dashboard Service -->
                <div class="service-item">
                    <div class="service-header">
                        <div class="service-title">🌐 Main Dashboard</div>
                        <span class="status" id="web-status">Checking...</span>
                    </div>
                    <div class="service-desc">Full-featured web monitoring interface</div>
                    <div class="button-group">
                        <button class="btn-start" onclick="startService('web')">▶️ Start</button>
                        <button class="btn-stop" onclick="stopService('web')">⏹️ Stop</button>
                        <button class="btn-info" onclick="openMainDashboard()">🔗 Open</button>
                    </div>
                </div>
                
                <div class="quick-actions">
                    <button class="btn-primary" onclick="startAll()">▶️ Start All</button>
                    <button class="btn-secondary" onclick="stopAll()">⏹️ Stop All</button>
                </div>
            </div>
            
            <!-- System Metrics -->
            <div class="card">
                <h2>📈 System Metrics</h2>
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="metric-label">CPU Usage</div>
                        <div class="metric-value" id="cpu-metric">--</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Memory Usage</div>
                        <div class="metric-value" id="memory-metric">--</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Disk Usage</div>
                        <div class="metric-value" id="disk-metric">--</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Network I/O</div>
                        <div class="metric-value" id="network-metric">--</div>
                    </div>
                </div>
                <button class="btn-primary" style="margin-top: 15px; width: 100%;" onclick="refreshMetrics()">
                    🔄 Refresh Metrics
                </button>
            </div>
        </div>
        
        <!-- Tabbed Content -->
        <div class="card full-width">
            <div class="tabs">
                <button class="tab active" onclick="switchTab('logs')">📝 Logs</button>
                <button class="tab" onclick="switchTab('config')">⚙️ Configuration</button>
            </div>
            
            <div id="logs-tab" class="tab-content active">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3>Application Logs</h3>
                    <div class="button-group">
                        <button class="btn-primary" onclick="refreshLogs()">🔄 Refresh</button>
                        <button class="btn-secondary" onclick="clearLogsDisplay()">🗑️ Clear</button>
                    </div>
                </div>
                <div class="logs-container" id="logs-display">
                    <div style="text-align: center; color: #888;">Loading logs...</div>
                </div>
            </div>
            
            <div id="config-tab" class="tab-content">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3>Configuration Editor</h3>
                    <div class="button-group">
                        <button class="btn-primary" onclick="saveConfig()">💾 Save</button>
                        <button class="btn-secondary" onclick="reloadConfig()">🔄 Reload</button>
                    </div>
                </div>
                <p style="color: #666; margin-bottom: 10px;">⚠️ Note: Changes require service restart to take effect</p>
                <textarea id="config-editor"></textarea>
            </div>
        </div>
    </div>
    
    <script>
        // State management
        let currentTab = 'logs';
        let statusCheckInterval = null;
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            refreshStatus();
            refreshMetrics();
            refreshLogs();
            reloadConfig();
            
            // Auto-refresh status every 3 seconds
            statusCheckInterval = setInterval(refreshStatus, 3000);
        });
        
        // Tab switching
        function switchTab(tabName) {
            currentTab = tabName;
            
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelector(`button[onclick="switchTab('${tabName}')"]`).classList.add('active');
            
            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${tabName}-tab`).classList.add('active');
        }
        
        // Service control
        async function startService(serviceId) {
            try {
                const response = await fetch(`/api/service/${serviceId}/start`, {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    alert(`${serviceId.toUpperCase()} service started successfully!`);
                    refreshStatus();
                } else {
                    alert(`Failed to start ${serviceId}: ${data.message}`);
                }
            } catch (error) {
                alert(`Error starting ${serviceId}: ${error.message}`);
            }
        }
        
        async function stopService(serviceId) {
            try {
                const response = await fetch(`/api/service/${serviceId}/stop`, {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    alert(`${serviceId.toUpperCase()} service stopped successfully!`);
                    refreshStatus();
                } else {
                    alert(`Failed to stop ${serviceId}: ${data.message}`);
                }
            } catch (error) {
                alert(`Error stopping ${serviceId}: ${error.message}`);
            }
        }
        
        async function startAll() {
            await startService('agent');
            await new Promise(resolve => setTimeout(resolve, 2000));
            await startService('web');
        }
        
        async function stopAll() {
            await stopService('web');
            await stopService('agent');
        }
        
        // Status refresh
        async function refreshStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                for (const [serviceId, isRunning] of Object.entries(data)) {
                    const statusEl = document.getElementById(`${serviceId}-status`);
                    if (statusEl) {
                        statusEl.textContent = isRunning ? 'Running' : 'Stopped';
                        statusEl.className = `status ${isRunning ? 'running' : 'stopped'}`;
                    }
                }
            } catch (error) {
                console.error('Error refreshing status:', error);
            }
        }
        
        // Metrics refresh
        async function refreshMetrics() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();
                
                document.getElementById('cpu-metric').textContent = `${data.cpu}%`;
                document.getElementById('memory-metric').textContent = `${data.memory}%`;
                document.getElementById('disk-metric').textContent = `${data.disk}%`;
                document.getElementById('network-metric').textContent = `${data.network_mb} MB`;
            } catch (error) {
                console.error('Error refreshing metrics:', error);
            }
        }
        
        // Logs management
        async function refreshLogs() {
            try {
                const response = await fetch('/api/logs');
                const data = await response.json();
                
                const logsDisplay = document.getElementById('logs-display');
                
                if (data.entries.length === 0) {
                    logsDisplay.innerHTML = '<div style="text-align: center; color: #888;">No logs available. Start the agent to begin collecting metrics.</div>';
                    return;
                }
                
                logsDisplay.innerHTML = data.entries.map(entry => `
                    <div class="log-entry">
                        <span class="log-time">[${entry.timestamp}]</span> ${entry.content}
                    </div>
                `).join('');
            } catch (error) {
                document.getElementById('logs-display').innerHTML = 
                    `<div style="color: #f44336;">Error loading logs: ${error.message}</div>`;
            }
        }
        
        function clearLogsDisplay() {
            document.getElementById('logs-display').innerHTML = 
                '<div style="text-align: center; color: #888;">Logs cleared. Click refresh to reload.</div>';
        }
        
        // Configuration management
        async function reloadConfig() {
            try {
                const response = await fetch('/api/config');
                const data = await response.json();
                document.getElementById('config-editor').value = data.config;
            } catch (error) {
                alert(`Error loading configuration: ${error.message}`);
            }
        }
        
        async function saveConfig() {
            try {
                const configText = document.getElementById('config-editor').value;
                
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ config: configText })
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    alert('Configuration saved successfully!\\n\\nRestart services for changes to take effect.');
                } else {
                    alert(`Failed to save configuration: ${data.message}`);
                }
            } catch (error) {
                alert(`Error saving configuration: ${error.message}`);
            }
        }
        
        function openMainDashboard() {
            window.open('http://localhost:5000', '_blank');
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/status")
async def get_status():
    """Get the status of all services."""
    return {
        'agent': is_process_running(processes['agent']),
        'web': is_process_running(processes['web'])
    }

@app.post("/api/service/{service_id}/start")
async def start_service(service_id: str):
    """Start a specific service."""
    global processes
    
    if service_id not in ['agent', 'web']:
        raise HTTPException(status_code=400, detail="Invalid service ID")
    
    # Check if already running
    if is_process_running(processes[service_id]):
        return {"status": "info", "message": f"{service_id} is already running"}
    
    try:
        if service_id == 'agent':
            # Start agent
            processes[service_id] = subprocess.Popen(
                [sys.executable, 'agent.py', 'run'],
                cwd=PROJECT_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        elif service_id == 'web':
            # Start main web dashboard
            config = load_config()
            port = config.get('web', {}).get('port', 5000)
            processes[service_id] = subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', 'web_dashboard:app', 
                 '--host', '0.0.0.0', '--port', str(port)],
                cwd=PROJECT_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        
        # Give it a moment to start
        await asyncio.sleep(1)
        
        return {"status": "success", "message": f"{service_id} started successfully"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/service/{service_id}/stop")
async def stop_service(service_id: str):
    """Stop a specific service."""
    global processes
    
    if service_id not in ['agent', 'web']:
        raise HTTPException(status_code=400, detail="Invalid service ID")
    
    try:
        process = processes[service_id]
        
        if not is_process_running(process):
            return {"status": "info", "message": f"{service_id} is not running"}
        
        # Kill process and its children
        kill_process_tree(process.pid)
        processes[service_id] = None
        
        return {"status": "success", "message": f"{service_id} stopped successfully"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/metrics")
async def get_metrics():
    """Get current system metrics."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        
        return {
            'cpu': round(cpu_percent, 1),
            'memory': round(memory.percent, 1),
            'disk': round(disk.percent, 1),
            'network_mb': round(net_io.bytes_sent / (1024 * 1024), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
async def get_logs():
    """Get recent log entries."""
    log_file = PROJECT_ROOT / "logs" / "smo_metrics.jsonl"
    
    if not log_file.exists():
        return {"entries": []}
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-30:] if len(lines) > 30 else lines
        
        entries = []
        for line in recent_lines:
            try:
                log_entry = json.loads(line)
                timestamp = log_entry.get('timestamp', 'N/A')
                
                if isinstance(timestamp, (int, float)):
                    dt = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    dt = timestamp
                
                # Extract key info
                cpu = log_entry.get('cpu', {}).get('average', {}).get('cpu_percent', {}).get('value', 'N/A')
                mem = log_entry.get('memory', {}).get('virtual_memory', {}).get('percent', {}).get('value', 'N/A')
                
                content = f"CPU: {cpu}% | Memory: {mem}%"
                
                entries.append({
                    'timestamp': dt,
                    'content': content
                })
            except json.JSONDecodeError:
                continue
        
        return {"entries": entries}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
async def get_config():
    """Get current configuration as YAML string."""
    try:
        config = load_config()
        config_yaml = yaml.dump(config, default_flow_style=False, sort_keys=False)
        return {"config": config_yaml}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config")
async def update_config(request: Request):
    """Update configuration from YAML string."""
    try:
        data = await request.json()
        config_text = data.get('config', '')
        
        # Parse YAML
        new_config = yaml.safe_load(config_text)
        
        # Save configuration
        if save_config(new_config):
            return {"status": "success", "message": "Configuration saved"}
        else:
            return {"status": "error", "message": "Failed to save configuration"}
    
    except yaml.YAMLError as e:
        return {"status": "error", "message": f"Invalid YAML: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}




def main():
    """Main entry point for the GUI dashboard application."""
    import uvicorn
    
    print("=" * 60)
    print("🚀 SMO GUI Dashboard - Control Panel")
    print("=" * 60)
    print()
    print("Starting control panel server...")
    print()
    print("📍 Access the dashboard at: http://localhost:8000")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Cleanup on exit
    def cleanup():
        """Cleanup processes on exit."""
        print("\n\n🔧 Cleaning up processes...")
        for service_id, process in processes.items():
            if is_process_running(process):
                try:
                    kill_process_tree(process.pid)
                    print(f"   Stopped {service_id} service")
                except Exception:
                    pass
        print("✅ Cleanup complete")
    
    import atexit
    atexit.register(cleanup)
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
    except KeyboardInterrupt:
        print("\n\n⚠️  Server stopped by user")
        cleanup()


if __name__ == '__main__':
    main()


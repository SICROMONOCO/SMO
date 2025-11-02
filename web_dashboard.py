from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import asyncio
import json
import os
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from starlette.websockets import WebSocketDisconnect, WebSocketState

app = FastAPI()

html = """
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
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🖥️ SMO Dashboard</h1>
            <div class="subtitle">System Monitoring & Orchestration - Live Metrics</div>
        </div>
        
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
        
        <script>
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
                        if (key.includes('_usage') && coreCount < 8) {
                            const match = key.match(/core_(\d+)_usage/);
                            if (!match) continue; // Skip if pattern doesn't match
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
            
            // Determine WebSocket protocol based on page protocol
            const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            var ws = new WebSocket(wsProtocol + window.location.host + "/ws");
            
            ws.onmessage = function(event) {
                try {
                    var data = JSON.parse(event.data);
                    
                    if (data.error) {
                        console.error('Error from server:', data.error);
                        return;
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
            };
            
            ws.onclose = function() {
                console.log('WebSocket connection closed');
                setTimeout(() => {
                    location.reload();
                }, 5000);
            };
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    url = os.environ.get("INFLUXDB_URL", "http://smo-db:8086")
    token = os.environ.get("INFLUXDB_TOKEN", "my-super-secret-token")
    org = os.environ.get("INFLUXDB_ORG", "my-org")
    bucket = os.environ.get("INFLUXDB_BUCKET", "smo-metrics")

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

                await websocket.send_text(json.dumps(results, indent=2))
            except WebSocketDisconnect:
                break
            except Exception as e:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps({"error": str(e)}))
                else:
                    break

            await asyncio.sleep(1)

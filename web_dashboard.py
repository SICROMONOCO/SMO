import json
from pathlib import Path
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

METRICS_LOG_PATH = Path(__file__).parent / "logs" / "smo_metrics.jsonl"

@app.route('/')
def index():
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Live Metrics Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #121212; color: #e0e0e0; }
            #metrics { white-space: pre-wrap; font-family: monospace; background-color: #1e1e1e; padding: 1em; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>Live Metrics Dashboard</h1>
        <div id="metrics">Loading...</div>
        <script>
            async function fetchMetrics() {
                try {
                    const response = await fetch('/api/metrics');
                    const data = await response.json();
                    document.getElementById('metrics').textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    console.error('Error fetching metrics:', error);
                    document.getElementById('metrics').textContent = 'Error loading metrics.';
                }
            }
            setInterval(fetchMetrics, 2000);
            fetchMetrics();
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route('/api/metrics')
def get_metrics():
    if not METRICS_LOG_PATH.exists():
        return jsonify({"error": "Metrics log file not found."}), 404

    try:
        with open(METRICS_LOG_PATH, "r", encoding="utf-8") as f:
            last_line = None
            for line in f:
                if line.strip():
                    last_line = line

            if last_line:
                return jsonify(json.loads(last_line))
            else:
                return jsonify({"error": "No metrics found in log file."}), 404
    except (json.JSONDecodeError, IOError) as e:
        return jsonify({"error": f"Error reading metrics: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)

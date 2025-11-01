from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import asyncio
import json
import os
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Live Metrics</title>
    </head>
    <body>
        <h1>Live Metrics Dashboard</h1>
        <pre id='metrics'></pre>
        <script>
            var ws = new WebSocket("ws://localhost:5678/ws");
            ws.onmessage = function(event) {
                var metrics = document.getElementById('metrics')
                var data = JSON.parse(event.data)
                metrics.textContent = JSON.stringify(data, null, 2)
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
            except Exception as e:
                await websocket.send_text(json.dumps({"error": str(e)}))

            await asyncio.sleep(1)

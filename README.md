# System Monitoring and Orchestration Tool

This project is a comprehensive system monitoring tool with a Textual TUI, a web dashboard, and a remote monitoring agent. The entire application is containerized with Docker for easy deployment and development.

## Docker Compose Setup

The application is orchestrated using Docker Compose. The following services are defined in `docker-compose.yml`:

| Service      | Description                                          |
|--------------|------------------------------------------------------|
| `smo-agent`  | The main monitoring agent that collects system metrics. |
| `smo-web`    | A FastAPI web dashboard with WebSockets for real-time metrics. |
| `smo-tui`    | A Textual-based TUI for interactive monitoring.       |
| `smo-db`     | An InfluxDB instance for storing metrics data.        |
| `smo-remote` | A minimal SSH server for testing remote monitoring.   |

### Prerequisites

- Docker
- Docker Compose

### Running the Application

1. **Build the images:**
   ```bash
   docker-compose build
   ```

2. **Run the services in detached mode:**
   ```bash
   docker-compose up -d
   ```

3. **Access the components:**
   - **Web Dashboard:** [http://localhost:5678](http://localhost:5678)
   - **InfluxDB UI:** [http://localhost:8086](http://localhost:8086)
   - **SSH Remote:** `ssh remoteuser@localhost -p 2222` (use the private key in `remote_ssh/id_rsa`)

4. **Run the TUI:**
   The TUI is an interactive service and should be run in an attached terminal:
   ```bash
   docker-compose run --rm smo-tui
   ```

5. **View logs:**
   ```bash
   docker-compose logs -f
   ```

6. **Stop the services:**
   ```bash
   docker-compose down
   ```

# SMO Installation Quick Reference

## Choose Your Installation Method

### Docker Installation (Containerized)
**Best for:** Development, testing, multiple instances, easy updates

```bash
./setup.sh
```

- ✅ No system modifications
- ✅ Easy to remove
- ✅ Isolated from host
- ✅ Works on any OS with Docker
- ⚠️ Requires Docker installed
- ⚠️ Higher resource overhead

**Documentation:** [CONTAINERIZATION.md](../CONTAINERIZATION.md)

---

### Standalone Installation (Native)
**Best for:** Production, dedicated servers, lower overhead

```bash
sudo ./setup-standalone.sh
```

- ✅ Native systemd integration
- ✅ Lower resource usage
- ✅ Direct host access
- ✅ Traditional service management
- ⚠️ Modifies system
- ⚠️ Linux only

**Documentation:** [STANDALONE_INSTALLATION.md](STANDALONE_INSTALLATION.md)

---

## Quick Comparison

| Feature | Docker | Standalone |
|---------|--------|------------|
| **Installation** | `./setup.sh` | `sudo ./setup-standalone.sh` |
| **Requirements** | Docker installed | Root access, Linux |
| **Isolation** | Yes | No |
| **Resource Usage** | Higher | Lower |
| **System Integration** | Limited | Native (systemd) |
| **Updates** | Rebuild containers | Manual updates |
| **Removal** | `docker-compose down` | `./uninstall-standalone.sh` |
| **Multi-instance** | Easy | Complex |
| **Backup** | Volume backups | Native tools |

## Access Points

### Docker Installation
- Web Dashboard: http://localhost:5678 (container mode) or http://localhost:5000 (host mode)
- InfluxDB UI: http://localhost:8086

### Standalone Installation
- Web Dashboard: http://localhost:5000
- InfluxDB UI: http://localhost:8086

## Common Commands

### Docker Installation
```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Run TUI
docker-compose run --rm smo-tui
```

### Standalone Installation
```bash
# View logs
sudo journalctl -u smo-agent -f

# Restart services
sudo systemctl restart smo-agent smo-web

# Stop services
sudo systemctl stop smo-agent smo-web

# Run TUI
cd /opt/smo
source venv/bin/activate
python3 -m tui.tui_dashboard
```

## Need Help?

- Docker installation issues: [docs/DOCKER_SETUP.md](DOCKER_SETUP.md)
- Standalone installation: [docs/STANDALONE_INSTALLATION.md](STANDALONE_INSTALLATION.md)
- General usage: [USAGE.md](../USAGE.md)

# Docker Setup Guide for SMO

This guide helps you set up Docker and Docker Compose for running SMO.

## Quick Installation

### Ubuntu/Debian

```bash
# Update package index
sudo apt-get update

# Install prerequisites
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine and Docker Compose
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
docker --version
docker compose version
```

### Fedora/RHEL/CentOS

```bash
# Install Docker
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
docker --version
docker compose version
```

### Arch Linux

```bash
# Install Docker
sudo pacman -S docker docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
docker --version
docker compose version
```

## Post-Installation Steps

### 1. Add your user to the docker group (optional but recommended)

This allows you to run Docker commands without `sudo`:

```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Activate the changes (or log out and back in)
newgrp docker

# Verify you can run docker without sudo
docker run hello-world
```

### 2. Verify Docker is working

```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker compose version

# Check Docker daemon status
sudo systemctl status docker

# Test Docker with hello-world
docker run hello-world
```

## Common Issues and Solutions

### Issue: "Cannot connect to the Docker daemon"

**Symptoms:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?
```

**Solutions:**

1. **Check if Docker service is running:**
   ```bash
   sudo systemctl status docker
   ```

2. **Start Docker service if stopped:**
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker  # Enable auto-start on boot
   ```

3. **Check Docker socket permissions:**
   ```bash
   ls -l /var/run/docker.sock
   ```
   Should show: `srw-rw---- 1 root docker`

4. **Add your user to docker group:**
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

### Issue: "permission denied while trying to connect to the Docker daemon"

**Solution:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Either log out and back in, or run:
newgrp docker

# Verify
docker ps
```

### Issue: "docker-compose: command not found"

**Symptoms:**
```
bash: docker-compose: command not found
```

**Solution:**

Modern Docker installations use `docker compose` (with a space) instead of `docker-compose`:

```bash
# Try the new syntax
docker compose version

# If that doesn't work, install the plugin
sudo apt-get install docker-compose-plugin
```

If you need the standalone `docker-compose` command:

```bash
# Download latest version
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker-compose --version
```

### Issue: Docker commands hang or timeout

**Solutions:**

1. **Check Docker daemon status:**
   ```bash
   sudo systemctl status docker
   ```

2. **Restart Docker:**
   ```bash
   sudo systemctl restart docker
   ```

3. **Check Docker logs:**
   ```bash
   sudo journalctl -u docker.service -n 50
   ```

4. **Check available disk space:**
   ```bash
   df -h
   ```
   Docker needs adequate disk space for images and containers.

### Issue: SMO setup fails to build images

**Solutions:**

1. **Clear Docker build cache:**
   ```bash
   docker builder prune -a
   ```

2. **Remove old images:**
   ```bash
   docker image prune -a
   ```

3. **Check internet connection** (needed to download base images)

4. **Try building manually:**
   ```bash
   cd /path/to/SMO
   docker compose build --no-cache
   ```

## Uninstalling Docker

If you need to completely remove Docker:

### Ubuntu/Debian

```bash
# Stop Docker
sudo systemctl stop docker

# Remove Docker packages
sudo apt-get purge docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Remove Docker data
sudo rm -rf /var/lib/docker
sudo rm -rf /var/lib/containerd

# Remove Docker group
sudo groupdel docker
```

### Fedora/RHEL/CentOS

```bash
sudo systemctl stop docker
sudo dnf remove docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo rm -rf /var/lib/docker
sudo rm -rf /var/lib/containerd
```

## Additional Resources

- [Official Docker Installation Guide](https://docs.docker.com/engine/install/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Post-Installation Steps](https://docs.docker.com/engine/install/linux-postinstall/)
- [Docker Troubleshooting Guide](https://docs.docker.com/config/daemon/)

## Next Steps

Once Docker is installed and running:

1. Return to the SMO directory
2. Run the setup script:
   ```bash
   ./setup.sh
   ```
3. Follow the interactive prompts to configure SMO

For more information about SMO configuration, see:
- [CONTAINERIZATION.md](../CONTAINERIZATION.md) - Detailed containerization guide
- [README.md](../README.md) - General SMO documentation

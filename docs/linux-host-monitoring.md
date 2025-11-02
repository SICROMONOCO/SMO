# Running SMO agent against the Linux host/VM

This document explains how to run the SMO agent container so it observes the
Linux host or VM (reads the host kernel `/proc`), instead of reporting the
container's cgroup-limited view.

## Recommended approach (Option A)

Share the host PID namespace and use host networking. This lets `psutil` inside
the container read host `/proc` and system metrics without changing the agent.

Steps:

1. SSH into the Linux VM where you want to deploy SMO.
2. Ensure Docker and Docker Compose / Docker Compose plugin are installed.
3. From the repository root on the VM, run:

```bash
# start with an override that puts the agent into host mode
docker compose -f docker-compose.yml -f docker-compose.host.override.yml up -d --build
```

4. Verify the host reports match those inside the container:

```bash
# on the VM host
cat /proc/meminfo

# inside the running agent container (replace container selector if needed)
docker exec -it $(docker ps -qf "name=smo-agent") cat /proc/meminfo
```

If they match, the agent is reading host resources.

## Alternative: bind-mount host /proc (Option B)

You can bind-mount `/proc` into the container and set `HOST_PROC` to point at it.
Note: `psutil` does not support reading an alternate proc root. Use this only if
you change the agent to parse `${HOST_PROC}` paths directly.

## Docker Desktop (Windows) notes

If you develop on Windows with Docker Desktop, make sure Docker Desktop is set
to use Linux containers (WSL2 backend) when building images for Linux VMs. If
Docker Desktop is in Windows container mode, switch it back using the Docker
Desktop menu (tray icon) → "Switch to Linux containers".

## Security notes

- Running containers with `privileged: true` or host namespaces grants broad
  access. For production consider limiting capabilities to the minimum required.
- Avoid setting explicit Docker resource limits on the agent container if you
  expect it to report full host resources (limits may cause psutil to report
  container-limited values).

## Troubleshooting

- If you still see VM/WSL metrics while testing on Windows, remember WSL2 is a
  Linux VM: containers inside WSL2 will naturally show WSL2 VM metrics. Test the
  host-mode setup on a dedicated Linux VM for accurate host observation.

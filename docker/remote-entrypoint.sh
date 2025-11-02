#!/usr/bin/env bash
set -euo pipefail

# This entrypoint starts a tmux session running the TUI as 'remoteuser'
# and then launches sshd in the foreground so users can SSH and attach to
# the session to view the live TUI.

# Create tmux session if it doesn't exist
TMUX_SESSION_NAME="smo_tui"

# Ensure home dir and permissions
chown -R remoteuser:remoteuser /home/remoteuser || true

# Start tmux session as remoteuser if missing
if ! su - remoteuser -c "tmux has-session -t ${TMUX_SESSION_NAME}" 2>/dev/null; then
  echo "Starting tmux session '${TMUX_SESSION_NAME}' running the TUI..."
  # Start the TUI in a detached tmux session so remote users can attach
  su - remoteuser -c "cd /app && tmux new-session -d -s ${TMUX_SESSION_NAME} 'python3 -m tui.tui_dashboard'"
else
  echo "tmux session '${TMUX_SESSION_NAME}' already exists"
fi

# Start sshd in foreground
/usr/sbin/sshd -D

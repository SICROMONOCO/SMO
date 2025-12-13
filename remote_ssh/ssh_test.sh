#!/usr/bin/env bash
set -euo pipefail

# Basic SSH connectivity test script.
# Usage: ssh_test.sh <host> [user] [port] [private_key]
# If args are missing, it will use env vars SSH_HOST, SSH_USER, SSH_PORT and key in this folder.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_KEY="$SCRIPT_DIR/id_rsa"

HOST="${1:-${SSH_HOST:-}}"
USER="${2:-${SSH_USER:-root}}"
PORT="${3:-${SSH_PORT:-22}}"
KEY="${4:-${SSH_KEY:-$DEFAULT_KEY}}"

if [ -z "$HOST" ]; then
    echo "Usage: $0 <host> [user] [port] [private_key]" >&2
    exit 2
fi

echo "Running SSH tests against $USER@$HOST:$PORT using key $KEY"

SSH_COMMON=(-o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new -i "$KEY" -p "$PORT")

check_ssh_command(){
    echo -n "1) Test simple remote command... "
    if ssh "${SSH_COMMON[@]}" "$USER@$HOST" 'echo SSH_OK' >/dev/null 2>&1; then
        echo "PASS"
    else
        echo "FAIL"
        return 1
    fi
}

check_authorized_key_present(){
    if [ ! -f "$DEFAULT_KEY.pub" ]; then
        echo "2) Public key $DEFAULT_KEY.pub missing; skip authorized_keys presence check" && return 0
    fi
    echo -n "2) Check authorized_keys contains our public key... "
    local pub
    pub=$(cat "$DEFAULT_KEY.pub")
    if ssh "${SSH_COMMON[@]}" "$USER@$HOST" "grep -F -- \"$pub\" ~/.ssh/authorized_keys >/dev/null 2>&1"; then
        echo "PASS"
    else
        echo "WARN: PUBLIC KEY NOT FOUND"
    fi
}

check_scp_roundtrip(){
    echo -n "3) Test SCP upload and download... "
    local tmp_local=$(mktemp)
    local tmp_remote="/tmp/smo_ssh_test_$$"
    echo "hello" > "$tmp_local"
    set +e
    scp -P "$PORT" -i "$KEY" "$tmp_local" "$USER@$HOST:$tmp_remote" >/dev/null 2>&1
    rc=$?
    if [ $rc -ne 0 ]; then
        echo "FAIL (upload)"
        rm -f "$tmp_local"
        set -e
        return 1
    fi
    ssh -i "$KEY" -p "$PORT" "$USER@$HOST" "cat $tmp_remote && rm -f $tmp_remote" >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "FAIL (remote read)"
        rm -f "$tmp_local"
        set -e
        return 1
    fi
    rm -f "$tmp_local"
    set -e
    echo "PASS"
}

check_reverse_tunnel(){
    echo -n "4) Optional: check remote can reach a small local HTTP server via reverse SSH (skipped)" && echo
    # This would require starting a server locally and a reverse tunnel; it's environment dependent.
}

main(){
    local fail=0
    check_ssh_command || fail=1
    check_authorized_key_present || true
    check_scp_roundtrip || fail=1
    check_reverse_tunnel || true

    if [ $fail -eq 0 ]; then
        echo "\nAll critical checks passed."
        return 0
    else
        echo "\nOne or more checks failed. See messages above for details."
        return 2
    fi
}

main

#!/usr/bin/env bash
# ==============================================================================
# AsteroidOS DevKit: SSH Helper for Emulator
# ==============================================================================
set -euo pipefail

PORT="2222"
USER="ceres"
HOST="localhost"

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_usage() {
    cat << EOF
Usage: $0 [options] [-- <remote-command>]

Options:
  -u, --user <username>   User to log in as (ceres or root, default: ceres)
  -p, --port <port>       SSH port forwarded from emulator (default: 2222)
  -h, --help              Show this help message

Examples:
  $0                      # Interactive shell as ceres
  $0 -u root              # Interactive shell as root
  $0 -- mcetool -D on     # Enable demo mode (keep display on)
EOF
}

REMOTE_CMD=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        -u|--user)
            USER="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        --)
            shift
            REMOTE_CMD=("$@")
            break
            ;;
        *)
            REMOTE_CMD+=("$1")
            shift
            ;;
    esac
done

SSH_OPTS=(
    -o "StrictHostKeyChecking=no"
    -o "UserKnownHostsFile=/dev/null"
    -o "LogLevel=ERROR"
    -p "${PORT}"
)

if [ ${#REMOTE_CMD[@]} -gt 0 ]; then
    ssh -t "${SSH_OPTS[@]}" "${USER}@${HOST}" "${REMOTE_CMD[@]}"
else
    echo -e "${BLUE}[INFO]${NC} Connecting to AsteroidOS Emulator (${USER}@${HOST}:${PORT})..."
    ssh "${SSH_OPTS[@]}" "${USER}@${HOST}"
fi


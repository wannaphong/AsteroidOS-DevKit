#!/usr/bin/env bash
# ==============================================================================
# AsteroidOS DevKit: Deploy Application to Emulator or Physical Watch
# ==============================================================================
set -euo pipefail

TARGET_TYPE="emulator"
IPK_FILE=""
HOST="localhost"
PORT="2222"
SSH_USER="ceres"

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

print_usage() {
    cat << EOF
Usage: $0 [ipk-file-or-build-dir] [options]

Options:
  -t, --target <emulator|watch>   Target device (default: emulator)
  -H, --host <host>               Host IP/hostname (default: localhost for emulator, 192.168.2.15 for watch)
  -p, --port <port>               SSH port (default: 2222 for emulator, 22 for watch)
  -u, --user <user>               SSH user (default: ceres for emulator, root for watch)
  -h, --help                      Show this help message

Examples:
  $0 sample-app/build-emulator                 # Auto-detect IPK in build dir and deploy to emulator
  $0 sample-app/build-emulator/app.ipk         # Deploy specific IPK to emulator
  $0 sample-app/build-arm --target watch       # Deploy ARM build to physical watch (192.168.2.15)
  $0 app.ipk --target watch --host 192.168.1.50 # Deploy to custom watch IP
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)
            TARGET_TYPE="$2"
            shift 2
            ;;
        -H|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -u|--user)
            SSH_USER="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        -*)
            log_err "Unknown option: $1"
            print_usage
            exit 1
            ;;
        *)
            if [ -z "${IPK_FILE}" ]; then
                IPK_FILE="$1"
            else
                log_err "Unexpected argument: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Adjust defaults for watch target if not explicitly customized
if [ "${TARGET_TYPE}" = "watch" ]; then
    if [ "${HOST}" = "localhost" ]; then HOST="192.168.2.15"; fi
    if [ "${PORT}" = "2222" ]; then PORT="22"; fi
    if [ "${SSH_USER}" = "ceres" ]; then SSH_USER="root"; fi
fi

if [ -z "${IPK_FILE}" ]; then
    # Try finding in sample-app
    if [ -d "sample-app/build-${TARGET_TYPE}" ]; then
        IPK_FILE="$(ls -1 sample-app/build-${TARGET_TYPE}/*.ipk 2>/dev/null | head -n 1 || true)"
    fi
fi

if [ -z "${IPK_FILE}" ]; then
    log_err "No IPK file specified and none found in default build directories."
    print_usage
    exit 1
fi

if [ -d "${IPK_FILE}" ]; then
    SEARCH_DIR="${IPK_FILE}"
    IPK_FILE="$(ls -1 "${SEARCH_DIR}"/*.ipk 2>/dev/null | head -n 1 || true)"
    if [ -z "${IPK_FILE}" ]; then
        log_err "No .ipk file found inside directory '${SEARCH_DIR}'."
        exit 1
    fi
fi

if [ ! -f "${IPK_FILE}" ]; then
    log_err "File '${IPK_FILE}' does not exist."
    exit 1
fi

IPK_BASENAME="$(basename "${IPK_FILE}")"

SSH_OPTS=(
    -o "StrictHostKeyChecking=no"
    -o "UserKnownHostsFile=/dev/null"
    -o "LogLevel=ERROR"
    -p "${PORT}"
)

SCP_OPTS=(
    -o "StrictHostKeyChecking=no"
    -o "UserKnownHostsFile=/dev/null"
    -o "LogLevel=ERROR"
    -P "${PORT}"
)

echo -e "${BOLD}Deploying AsteroidOS Package${NC}"
echo "============================"
echo "IPK Package : ${IPK_FILE}"
echo "Target Host : ${SSH_USER}@${HOST}:${PORT}"
echo ""

log_info "Uploading package to target device..."
scp "${SCP_OPTS[@]}" "${IPK_FILE}" "${SSH_USER}@${HOST}:/tmp/${IPK_BASENAME}"

log_info "Installing package with opkg..."
# If user is not root, use sudo or install as root
if [ "${SSH_USER}" = "root" ]; then
    ssh "${SSH_OPTS[@]}" "${SSH_USER}@${HOST}" "opkg install --force-reinstall /tmp/${IPK_BASENAME} && rm -f /tmp/${IPK_BASENAME}"
else
    # Try running opkg (may require sudo if permissions needed)
    ssh "${SSH_OPTS[@]}" "${SSH_USER}@${HOST}" "opkg install --force-reinstall /tmp/${IPK_BASENAME} || sudo opkg install --force-reinstall /tmp/${IPK_BASENAME} && rm -f /tmp/${IPK_BASENAME}"
fi

echo ""
log_ok "Package ${IPK_BASENAME} installed successfully!"
echo "Check your app on the app launcher on the AsteroidOS screen."


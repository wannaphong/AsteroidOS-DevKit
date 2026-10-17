#!/usr/bin/env bash
# ==============================================================================
# AsteroidOS DevKit: Launch Emulator in QEMU
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
EMULATOR_DIR="${BASE_DIR}/emulator"

KERNEL="${EMULATOR_DIR}/bzImage-emulator.bin"
ROOTFS="${EMULATOR_DIR}/asteroid-image-emulator.rootfs.ext4"

# Defaults
DISPLAY_BACKEND="sdl"
GL_MODE="on"
SHOW_CURSOR=false
MEMORY="512"
RESOLUTION="800x800"
SSH_PORT="2222"
USE_KVM=true
SNAPSHOT=false

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
Usage: $0 [options]

Options:
  --display <sdl|gtk>     Display frontend: sdl (default) or gtk
  --show-cursor           Always show host mouse cursor (helpful for clicking)
  --no-gl                 Disable hardware OpenGL (GL off)
  --resolution <WxH>      Screen resolution (default: 800x800)
  --mem <MB>              RAM size in MB (default: 512)
  --port <port>           SSH forwarding port (default: 2222)
  --snapshot              Run in snapshot mode (discards rootfs modifications on exit)
  --no-kvm                Disable KVM hardware acceleration (fallback to TCG)
  -h, --help              Show this help message

SSH Access:
  Once booted, connect via:
    ssh -p 2222 ceres@localhost
    or run: ./scripts/ssh-emulator.sh
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --display)
            DISPLAY_BACKEND="$2"
            shift 2
            ;;
        --show-cursor)
            SHOW_CURSOR=true
            shift
            ;;
        --no-gl)
            GL_MODE="off"
            shift
            ;;
        --resolution)
            RESOLUTION="$2"
            shift 2
            ;;
        --mem)
            MEMORY="$2"
            shift 2
            ;;
        --port)
            SSH_PORT="$2"
            shift 2
            ;;
        --snapshot)
            SNAPSHOT=true
            shift
            ;;
        --no-kvm)
            USE_KVM=false
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            log_err "Unknown argument: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Check files
if [ ! -f "${KERNEL}" ] || [ ! -f "${ROOTFS}" ]; then
    log_warn "Emulator kernel or rootfs missing in ${EMULATOR_DIR}."
    log_info "Running setup-emulator.sh to download required images..."
    "${SCRIPT_DIR}/setup-emulator.sh"
fi

# Session check (Wayland vs X11)
SESSION_TYPE="${XDG_SESSION_TYPE:-unknown}"
if [ "${SESSION_TYPE}" = "x11" ]; then
    log_warn "Current session is X11. AsteroidOS emulator works best under Wayland."
    log_warn "If you experience graphical glitches or crashes, try GTK mode: $0 --display gtk"
fi

# Detect QEMU binary
QEMU_BIN=""
if command -v qemu-system-x86_64 >/dev/null 2>&1; then
    QEMU_BIN="qemu-system-x86_64"
elif command -v qemu-system-i386 >/dev/null 2>&1; then
    QEMU_BIN="qemu-system-i386"
else
    log_err "qemu-system-x86_64 is not installed. Please run ./scripts/install-prereqs.sh"
    exit 1
fi

# Detect VGA device
VGA_DEVICE="virtio-vga-gl"
if ! "${QEMU_BIN}" -device help 2>&1 | grep -q "virtio-vga-gl"; then
    if "${QEMU_BIN}" -device help 2>&1 | grep -q "virtio-vga"; then
        VGA_DEVICE="virtio-vga,virgl=on"
    fi
fi

# Build display option
DISPLAY_OPT="${DISPLAY_BACKEND}"
if [ "${GL_MODE}" = "on" ]; then
    DISPLAY_OPT="${DISPLAY_OPT},gl=on"
fi
if [ "${SHOW_CURSOR}" = "true" ]; then
    DISPLAY_OPT="${DISPLAY_OPT},show-cursor=on"
fi

# Build KVM / acceleration options
ACCEL_OPTS=()
if [ "${USE_KVM}" = "true" ]; then
    if [ -w /dev/kvm ]; then
        ACCEL_OPTS+=("-enable-kvm")
    else
        log_warn "/dev/kvm is not writable by current user; running without KVM acceleration."
    fi
fi

# Drive options
DRIVE_OPTS=("-drive" "format=raw,file=${ROOTFS}")
if [ "${SNAPSHOT}" = "true" ]; then
    DRIVE_OPTS+=("-snapshot")
fi

echo -e "${BOLD}Starting AsteroidOS Emulator${NC}"
echo "============================="
echo "QEMU Binary : ${QEMU_BIN}"
echo "Kernel      : ${KERNEL}"
echo "RootFS      : ${ROOTFS}"
echo "Display     : ${DISPLAY_OPT}"
echo "VGA Device  : ${VGA_DEVICE}"
echo "Resolution  : ${RESOLUTION}"
echo "Memory      : ${MEMORY}M"
echo "SSH Port    : localhost:${SSH_PORT} -> guest:22"
echo ""
echo -e "${GREEN}Connect via SSH:${NC} ssh -p ${SSH_PORT} ceres@localhost"
echo "============================="

exec "${QEMU_BIN}" \
    "${ACCEL_OPTS[@]}" \
    -kernel "${KERNEL}" \
    -device "${VGA_DEVICE}" \
    -net nic \
    -net "user,hostfwd=tcp::${SSH_PORT}-:22" \
    "${DRIVE_OPTS[@]}" \
    -m "${MEMORY}" \
    -display "${DISPLAY_OPT}" \
    -cpu qemu64,+ssse3,+sse4.1,+sse4.2 \
    -usb -device usb-tablet \
    --append "verbose root=/dev/sda rw mem=${MEMORY}M video=${RESOLUTION}"


#!/usr/bin/env bash
# ==============================================================================
# AsteroidOS DevKit: Setup Emulator (Kernel & RootFS)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
EMULATOR_DIR="${BASE_DIR}/emulator"

# Release server configuration
BASE_URL="https://release.asteroidos.org/nightlies/emulator"
KERNEL_FILE="bzImage-emulator.bin"
ROOTFS_FILE="asteroid-image-emulator.rootfs.ext4"

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

FORCE=false
for arg in "$@"; do
    case "$arg" in
        --force|-f)
            FORCE=true
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --force, -f    Force re-download even if files already exist"
            echo "  --help, -h     Show this help message"
            exit 0
            ;;
    esac
done

echo -e "${BOLD}AsteroidOS DevKit - Emulator Setup${NC}"
echo "==================================="
mkdir -p "${EMULATOR_DIR}"

# Download function supporting aria2c, curl, and wget
download_file() {
    local filename="$1"
    local url="${BASE_URL}/${filename}"
    local dest="${EMULATOR_DIR}/${filename}"

    if [ -f "${dest}" ] && [ "${FORCE}" != "true" ]; then
        log_info "File '${filename}' already exists. Skipping download (use --force to re-download)."
        return 0
    fi

    log_info "Downloading ${filename} from ${url}..."
    if command -v aria2c >/dev/null 2>&1; then
        aria2c -x 8 -s 8 -k 1M -c --allow-overwrite=true -d "${EMULATOR_DIR}" -o "${filename}" "${url}"
    elif command -v wget >/dev/null 2>&1; then
        wget -c --show-progress -O "${dest}" "${url}"
    elif command -v curl >/dev/null 2>&1; then
        curl -C - -L --progress-bar -o "${dest}" "${url}"
    else
        log_err "No download tool found! Please install curl, wget, or aria2."
        exit 1
    fi
}

download_file "${KERNEL_FILE}"
download_file "${ROOTFS_FILE}"

# Download MD5 checksums and verify
log_info "Verifying checksums against official AsteroidOS release..."
MD5SUMS_URL="${BASE_URL}/MD5SUMS"
MD5SUMS_TMP="$(mktemp)"
if curl -sL "${MD5SUMS_URL}" -o "${MD5SUMS_TMP}"; then
    pushd "${EMULATOR_DIR}" >/dev/null
    # Filter only files we care about
    grep -E "(${KERNEL_FILE}|${ROOTFS_FILE})" "${MD5SUMS_TMP}" | md5sum -c --status && {
        log_ok "Checksums verified successfully!"
    } || {
        log_warn "Checksum verification reported a mismatch or check failed. Please check files."
    }
    popd >/dev/null
    rm -f "${MD5SUMS_TMP}"
else
    log_warn "Could not fetch MD5SUMS for verification. Skipping checksum validation."
fi

# Expand rootfs to 2GB to prevent ENOSPC disk exhaustion when deploying applications
ROOTFS_PATH="${EMULATOR_DIR}/${ROOTFS_FILE}"
if [ -f "${ROOTFS_PATH}" ] && command -v truncate >/dev/null 2>&1 && command -v resize2fs >/dev/null 2>&1; then
    CURRENT_SIZE="$(stat -c%s "${ROOTFS_PATH}" 2>/dev/null || echo 0)"
    if [ "${CURRENT_SIZE}" -gt 0 ] && [ "${CURRENT_SIZE}" -lt 2147483648 ]; then
        log_info "Auto-expanding rootfs to 2GB for comfortable app development..."
        e2fsck -fy "${ROOTFS_PATH}" >/dev/null 2>&1 || true
        truncate -s 2G "${ROOTFS_PATH}"
        resize2fs "${ROOTFS_PATH}" >/dev/null 2>&1 || true
        log_ok "Rootfs expanded to 2GB successfully!"
    fi
fi

# Check QEMU
echo ""
if command -v qemu-system-x86_64 >/dev/null 2>&1; then
    log_ok "QEMU (qemu-system-x86_64) is installed: $(qemu-system-x86_64 --version | head -n 1)"
else
    log_warn "QEMU is not installed! Run './scripts/install-prereqs.sh' or install 'qemu-system-x86'."
fi

echo ""
log_ok "Emulator setup complete! You can start the emulator with:"
echo "  ./scripts/run-emulator.sh"


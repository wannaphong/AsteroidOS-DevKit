#!/usr/bin/env bash
# ==============================================================================
# AsteroidOS DevKit: Build Application Helper
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

TARGET="emulator"
APP_DIR=""
BUILD_DIR=""
DO_PACKAGE=true
CLEAN=false

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
Usage: $0 [app-directory] [options]

Arguments:
  app-directory             Path to application source directory (default: sample-app)

Options:
  -t, --target <target>     Target platform: 'emulator' (default) or 'arm'
  -b, --build-dir <dir>     Build output directory (default: <app-dir>/build-<target>)
  --no-package              Do not build .ipk package (compile binaries only)
  --clean                   Clean build directory before building
  -h, --help                Show this help message

Examples:
  $0 sample-app                         # Build sample-app for emulator & make .ipk
  $0 sample-app --target arm            # Build sample-app for ARM smartwatch
  $0 path/to/my-app --target emulator   # Build custom app
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -b|--build-dir)
            BUILD_DIR="$2"
            shift 2
            ;;
        --no-package)
            DO_PACKAGE=false
            shift
            ;;
        --clean)
            CLEAN=true
            shift
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
            if [ -z "${APP_DIR}" ]; then
                APP_DIR="$1"
            else
                log_err "Unexpected argument: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Default app directory
if [ -z "${APP_DIR}" ]; then
    APP_DIR="${BASE_DIR}/sample-app"
fi

if [ ! -d "${APP_DIR}" ]; then
    log_err "Application directory '${APP_DIR}' not found."
    exit 1
fi
APP_DIR="$(cd "${APP_DIR}" && pwd)"

if [ ! -f "${APP_DIR}/CMakeLists.txt" ]; then
    log_err "No CMakeLists.txt found in '${APP_DIR}'."
    exit 1
fi

if [ -z "${BUILD_DIR}" ]; then
    BUILD_DIR="${APP_DIR}/build-${TARGET}"
fi

# Load SDK Environment
ENV_SCRIPT="${BASE_DIR}/env-${TARGET}.sh"
if [ ! -f "${ENV_SCRIPT}" ]; then
    # Check if SDK directory exists
    SDK_DIR="${BASE_DIR}/sdk"
    if [ ! -d "${SDK_DIR}" ] || [ -z "$(ls -A "${SDK_DIR}" 2>/dev/null)" ]; then
        log_err "SDK for '${TARGET}' is not installed."
        echo "Please install it first by running:"
        echo "  ./scripts/setup-sdk.sh --target ${TARGET}"
        exit 1
    fi
    # If SDK exists but env wrapper doesn't, try finding environment-setup file
    if [ "${TARGET}" = "arm" ]; then
        ENV_FILE="$(ls -1 ${SDK_DIR}/environment-setup-*armv7* 2>/dev/null | head -n 1 || true)"
        SYSROOT_BIN="$(ls -d ${SDK_DIR}/sysroots/armv7*-oe-linux-gnueabi/usr/bin 2>/dev/null | head -n 1 || true)"
    else
        ENV_FILE="$(ls -1 ${SDK_DIR}/environment-setup-*core2-32* 2>/dev/null | head -n 1 || true)"
        SYSROOT_BIN="$(ls -d ${SDK_DIR}/sysroots/core2-32-*-linux/usr/bin 2>/dev/null | head -n 1 || true)"
    fi
    if [ -z "${ENV_FILE}" ]; then
        log_err "No matching environment setup script found for '${TARGET}' in ${SDK_DIR}."
        exit 1
    fi
    if [ -n "${SYSROOT_BIN}" ]; then
        export CMAKE_PROGRAM_PATH="${SYSROOT_BIN}"
    fi
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
else
    # shellcheck disable=SC1090
    source "${ENV_SCRIPT}"
fi

echo -e "${BOLD}Building AsteroidOS Application${NC}"
echo "==============================="
echo "App Source : ${APP_DIR}"
echo "Target     : ${TARGET}"
echo "Build Dir  : ${BUILD_DIR}"
echo "Arch       : ${OECORE_TARGET_ARCH:-unknown}"
echo ""

if [ "${CLEAN}" = "true" ] && [ -d "${BUILD_DIR}" ]; then
    log_info "Cleaning build directory..."
    rm -rf "${BUILD_DIR}"
fi

log_info "Configuring CMake..."
cmake -B "${BUILD_DIR}" -S "${APP_DIR}" -DCMAKE_INSTALL_PREFIX:PATH=/usr

log_info "Compiling project..."
cmake --build "${BUILD_DIR}" -j"$(nproc)"

if [ "${DO_PACKAGE}" = "true" ]; then
    log_info "Packaging .ipk package..."
    cmake --build "${BUILD_DIR}" --target package
fi

echo ""
log_ok "Build finished successfully!"
echo "Generated outputs in ${BUILD_DIR}:"
ls -la "${BUILD_DIR}"/*.so 2>/dev/null || true
ls -la "${BUILD_DIR}"/*.ipk 2>/dev/null || true


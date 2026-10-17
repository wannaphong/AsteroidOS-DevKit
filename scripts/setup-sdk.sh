#!/usr/bin/env bash
# ==============================================================================
# AsteroidOS DevKit: Setup Software Development Kit (Qt6 SDK)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOWNLOADS_DIR="${BASE_DIR}/downloads"
SDK_INSTALL_DIR="${BASE_DIR}/sdk"

SDK_BASE_URL="https://release.asteroidos.org/nightlies/sdk"
ARM_INSTALLER="oecore-meta-toolchain-qt6-x86_64-armv7vehf-neon-sturgeon-toolchain-nodistro.0.sh"
EMU_INSTALLER="oecore-meta-toolchain-qt6-x86_64-core2-32-emulator-toolchain-nodistro.0.sh"

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

TARGET="emulator"
FORCE=false

print_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -t, --target <target>   SDK target to install: 'emulator', 'arm', or 'all' (default: emulator)"
    echo "  -d, --dir <path>        Installation prefix directory (default: ${SDK_INSTALL_DIR})"
    echo "  -f, --force             Force re-download and re-install even if already installed"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --target emulator     # Install Qt6 SDK for QEMU emulator"
    echo "  $0 --target arm          # Install Qt6 SDK for ARM watch devices"
    echo "  $0 --target all          # Install both SDKs"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -d|--dir)
            SDK_INSTALL_DIR="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
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

mkdir -p "${DOWNLOADS_DIR}" "${SDK_INSTALL_DIR}"

download_sdk() {
    local installer="$1"
    local url="${SDK_BASE_URL}/${installer}"
    local dest="${DOWNLOADS_DIR}/${installer}"

    if [ -f "${dest}" ] && [ "${FORCE}" != "true" ]; then
        log_info "Installer '${installer}' already downloaded in ${DOWNLOADS_DIR}."
        return 0
    fi

    log_info "Downloading ${installer} (~2GB)..."
    if command -v aria2c >/dev/null 2>&1; then
        aria2c -x 8 -s 8 -k 1M -c --allow-overwrite=true -d "${DOWNLOADS_DIR}" -o "${installer}" "${url}"
    elif command -v wget >/dev/null 2>&1; then
        wget -c --show-progress -O "${dest}" "${url}"
    elif command -v curl >/dev/null 2>&1; then
        curl -C - -L --progress-bar -o "${dest}" "${url}"
    else
        log_err "No download tool found! Please install aria2, wget, or curl."
        exit 1
    fi
}

verify_sdk() {
    local installer="$1"
    log_info "Verifying MD5 checksum for ${installer}..."
    local md5_tmp="$(mktemp)"
    if curl -sL "${SDK_BASE_URL}/MD5SUMS" -o "${md5_tmp}"; then
        pushd "${DOWNLOADS_DIR}" >/dev/null
        if grep "${installer}" "${md5_tmp}" | md5sum -c --status; then
            log_ok "Checksum verified for ${installer}!"
        else
            log_warn "Checksum verification failed for ${installer}."
        fi
        popd >/dev/null
        rm -f "${md5_tmp}"
    else
        log_warn "Could not fetch MD5SUMS; skipping verification."
    fi
}

install_sdk() {
    local installer="$1"
    local target_type="$2" # "emulator" or "arm"
    local installer_path="${DOWNLOADS_DIR}/${installer}"

    chmod +x "${installer_path}"
    log_info "Installing ${target_type} SDK into ${SDK_INSTALL_DIR}..."
    # The OE SDK installer takes -y (answer yes to all questions) and -d <dir>
    "${installer_path}" -y -d "${SDK_INSTALL_DIR}"
    log_ok "${target_type} SDK base toolchain installed successfully!"

    populate_asteroid_sysroot "${target_type}"
}

populate_asteroid_sysroot() {
    local target_type="$1"
    local arch_name=""
    local sysroot_pattern=""

    if [ "${target_type}" = "arm" ]; then
        arch_name="armv7vehf-neon"
        sysroot_pattern="armv7*"
    else
        arch_name="core2-32"
        sysroot_pattern="core2-32*"
    fi

    local target_sysroot
    target_sysroot="$(ls -d ${SDK_INSTALL_DIR}/sysroots/${sysroot_pattern}-linux 2>/dev/null | head -n 1 || true)"
    local native_sysroot
    native_sysroot="$(ls -d ${SDK_INSTALL_DIR}/sysroots/x86_64-*-linux 2>/dev/null | head -n 1 || true)"

    if [ -z "${target_sysroot}" ] || [ ! -d "${target_sysroot}" ]; then
        log_warn "Target sysroot not found for ${target_type}. Skipping package population."
        return 0
    fi

    log_info "Populating AsteroidOS application development headers and CMake modules for ${target_type}..."
    local ipk_base_url="https://release.asteroidos.org/nightlies/ipk/${arch_name}"
    local ipk_cache_dir="${DOWNLOADS_DIR}/ipk-${arch_name}"
    mkdir -p "${ipk_cache_dir}"

    local index_html
    index_html="$(curl -sL "${ipk_base_url}/")"

    local pkgs=("extra-cmake-modules-dev" "libasteroidapp6-dev" "libasteroidapp6-2")
    for pkg in "${pkgs[@]}"; do
        local pkg_file
        pkg_file="$(echo "${index_html}" | grep -o "href=\"${pkg}_[^\"]*\.ipk\"" | head -n 1 | cut -d'"' -f2 || true)"
        if [ -z "${pkg_file}" ]; then
            pkg_file="$(echo "${index_html}" | grep -o "href=\"${pkg}%[^\"]*\.ipk\"" | head -n 1 | cut -d'"' -f2 || true)"
        fi

        if [ -n "${pkg_file}" ]; then
            local pkg_url="${ipk_base_url}/${pkg_file}"
            local local_ipk="${ipk_cache_dir}/$(basename "${pkg_file}")"

            if [ ! -f "${local_ipk}" ]; then
                log_info "Downloading ${pkg}..."
                curl -sL -o "${local_ipk}" "${pkg_url}"
            fi

            # Extract data tar archive from IPK
            if command -v ar >/dev/null 2>&1; then
                local data_member
                data_member="$(ar -t "${local_ipk}" | grep '^data\.tar' | head -n 1)"
                if [ -n "${data_member}" ]; then
                    case "${data_member}" in
                        data.tar.zst)
                            ar -p "${local_ipk}" "${data_member}" | zstd -d -q | tar -x -C "${target_sysroot}"
                            ;;
                        data.tar.xz)
                            ar -p "${local_ipk}" "${data_member}" | tar -xJ -C "${target_sysroot}"
                            ;;
                        data.tar.gz)
                            ar -p "${local_ipk}" "${data_member}" | tar -xz -C "${target_sysroot}"
                            ;;
                        *)
                            ar -p "${local_ipk}" "${data_member}" | tar -x -C "${target_sysroot}"
                            ;;
                    esac
                fi
            else
                log_warn "'ar' utility not found. Please install binutils."
            fi
        else
            log_warn "Could not resolve IPK package for ${pkg} in ${ipk_base_url}"
        fi
    done

    # Ensure asteroid-generate-desktop is in native sysroot bin
    if [ -f "${target_sysroot}/usr/bin/asteroid-generate-desktop" ] && [ -d "${native_sysroot}/usr/bin" ]; then
        cp -f "${target_sysroot}/usr/bin/asteroid-generate-desktop" "${native_sysroot}/usr/bin/"
        chmod +x "${native_sysroot}/usr/bin/asteroid-generate-desktop"
    fi

    log_ok "AsteroidOS development headers & modules populated into sysroot!"
}

generate_env_wrappers() {
    # Generate convenient environment activation scripts in project root
    if compgen -G "${SDK_INSTALL_DIR}/environment-setup-*core2-32*" > /dev/null; then
        local emu_env
        emu_env="$(ls -1 ${SDK_INSTALL_DIR}/environment-setup-*core2-32* | head -n 1)"
        cat << 'EOF' > "${BASE_DIR}/env-emulator.sh"
#!/usr/bin/env bash
# Source this file before building apps for AsteroidOS Emulator:
#   source env-emulator.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_DIR="${SCRIPT_DIR}/sdk"
ENV_FILE="$(ls -1 ${SDK_DIR}/environment-setup-*core2-32* 2>/dev/null | head -n 1)"

if [ -z "${ENV_FILE}" ] || [ ! -f "${ENV_FILE}" ]; then
    echo "[ERROR] Emulator SDK environment file not found in ${SDK_DIR}."
    echo "Please run: ./scripts/setup-sdk.sh --target emulator"
    return 1 2>/dev/null || exit 1
fi

SYSROOT_BIN="$(ls -d ${SDK_DIR}/sysroots/core2-32-*-linux/usr/bin 2>/dev/null | head -n 1)"
if [ -n "${SYSROOT_BIN}" ]; then
    export CMAKE_PROGRAM_PATH="${SYSROOT_BIN}"
fi

source "${ENV_FILE}"
echo "[OK] AsteroidOS Emulator SDK environment loaded!"
echo "     Target Architecture : ${OECORE_TARGET_ARCH:-x86}"
echo "     Sysroot             : ${SDKTARGETSYSROOT:-unknown}"
echo "     CMake Path          : ${CMAKE_PROGRAM_PATH:-default}"
EOF
        chmod +x "${BASE_DIR}/env-emulator.sh"
        log_ok "Generated: env-emulator.sh"
    fi

    if compgen -G "${SDK_INSTALL_DIR}/environment-setup-*armv7*" > /dev/null; then
        local arm_env
        arm_env="$(ls -1 ${SDK_INSTALL_DIR}/environment-setup-*armv7* | head -n 1)"
        cat << 'EOF' > "${BASE_DIR}/env-arm.sh"
#!/usr/bin/env bash
# Source this file before building apps for AsteroidOS ARM Watches:
#   source env-arm.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_DIR="${SCRIPT_DIR}/sdk"
ENV_FILE="$(ls -1 ${SDK_DIR}/environment-setup-*armv7* 2>/dev/null | head -n 1)"

if [ -z "${ENV_FILE}" ] || [ ! -f "${ENV_FILE}" ]; then
    echo "[ERROR] ARM SDK environment file not found in ${SDK_DIR}."
    echo "Please run: ./scripts/setup-sdk.sh --target arm"
    return 1 2>/dev/null || exit 1
fi

SYSROOT_BIN="$(ls -d ${SDK_DIR}/sysroots/armv7*-oe-linux-gnueabi/usr/bin 2>/dev/null | head -n 1)"
if [ -n "${SYSROOT_BIN}" ]; then
    export CMAKE_PROGRAM_PATH="${SYSROOT_BIN}"
fi

source "${ENV_FILE}"
echo "[OK] AsteroidOS ARM SDK environment loaded!"
echo "     Target Architecture : ${OECORE_TARGET_ARCH:-arm}"
echo "     Sysroot             : ${SDKTARGETSYSROOT:-unknown}"
echo "     CMake Path          : ${CMAKE_PROGRAM_PATH:-default}"
EOF
        chmod +x "${BASE_DIR}/env-arm.sh"
        log_ok "Generated: env-arm.sh"
    fi
}

echo -e "${BOLD}AsteroidOS DevKit - SDK Setup${NC}"
echo "=============================="
echo "Target  : ${TARGET}"
echo "SDK Dir : ${SDK_INSTALL_DIR}"
echo ""

case "${TARGET}" in
    emulator|emu|x86)
        download_sdk "${EMU_INSTALLER}"
        verify_sdk "${EMU_INSTALLER}"
        install_sdk "${EMU_INSTALLER}" "emulator"
        ;;
    arm|watch)
        download_sdk "${ARM_INSTALLER}"
        verify_sdk "${ARM_INSTALLER}"
        install_sdk "${ARM_INSTALLER}" "arm"
        ;;
    all|both)
        download_sdk "${EMU_INSTALLER}"
        verify_sdk "${EMU_INSTALLER}"
        install_sdk "${EMU_INSTALLER}" "emulator"

        download_sdk "${ARM_INSTALLER}"
        verify_sdk "${ARM_INSTALLER}"
        install_sdk "${ARM_INSTALLER}" "arm"
        ;;
    *)
        log_err "Invalid target '${TARGET}'. Use 'emulator', 'arm', or 'all'."
        exit 1
        ;;
esac

generate_env_wrappers

echo ""
log_ok "SDK setup completed successfully!"


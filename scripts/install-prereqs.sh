#!/usr/bin/env bash
# ==============================================================================
# AsteroidOS DevKit: Install Host Prerequisites
# ==============================================================================
set -euo pipefail

# ANSI color output
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

echo -e "${BOLD}AsteroidOS DevKit - Host Prerequisites Installer${NC}"
echo "================================================="

# Check sudo access
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        log_err "This script requires root privileges to install packages. Please run as root or install sudo."
        exit 1
    fi
fi

# Detect package manager
if command -v apt-get >/dev/null 2>&1; then
    log_info "Detected Debian/Ubuntu-based distribution (apt-get)"
    $SUDO apt-get update -y
    $SUDO apt-get install -y \
        build-essential \
        binutils \
        cmake \
        git \
        curl \
        wget \
        aria2 \
        python3 \
        tar \
        xz-utils \
        bzip2 \
        zstd \
        file \
        openssh-client \
        qemu-system-x86 \
        libgl1-mesa-dri \
        libvirt-daemon-system

elif command -v dnf >/dev/null 2>&1; then
    log_info "Detected Fedora/RHEL-based distribution (dnf)"
    $SUDO dnf install -y \
        @development-tools \
        binutils \
        cmake \
        git \
        curl \
        wget \
        aria2 \
        python3 \
        tar \
        xz \
        bzip2 \
        zstd \
        file \
        openssh-clients \
        qemu-system-x86 \
        mesa-dri-drivers

elif command -v pacman >/dev/null 2>&1; then
    log_info "Detected Arch Linux-based distribution (pacman)"
    $SUDO pacman -Sy --needed --noconfirm \
        base-devel \
        binutils \
        cmake \
        git \
        curl \
        wget \
        aria2 \
        python \
        tar \
        xz \
        bzip2 \
        zstd \
        file \
        openssh \
        qemu-desktop \
        mesa

elif command -v zypper >/dev/null 2>&1; then
    log_info "Detected openSUSE distribution (zypper)"
    $SUDO zypper install -y \
        -t pattern devel_basis \
        binutils \
        cmake \
        git \
        curl \
        wget \
        aria2 \
        python3 \
        tar \
        xz \
        bzip2 \
        zstd \
        file \
        openssh \
        qemu-x86 \
        Mesa

else
    log_warn "Unrecognized package manager. Please ensure the following tools are manually installed:"
    echo "  - build-essential / base-devel"
    echo "  - cmake, git, curl, wget, aria2, python3, tar, xz, bzip2"
    echo "  - qemu-system-x86_64 (with virtio-vga-gl & SDL/GTK support)"
    echo "  - openssh-client"
fi

# Check KVM permission for current user
echo ""
log_info "Checking KVM acceleration support (/dev/kvm)..."
if [ -e /dev/kvm ]; then
    if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
        log_ok "KVM device exists and is accessible by current user ($(whoami))."
    else
        log_warn "/dev/kvm exists, but current user ($(whoami)) does not have write permissions."
        if getent group kvm >/dev/null 2>&1; then
            log_info "Adding $(whoami) to group 'kvm'..."
            $SUDO usermod -aG kvm "$(whoami)" || true
            log_warn "Please log out and log back in (or run 'newgrp kvm') for group changes to take effect."
        fi
    fi
else
    log_warn "/dev/kvm not found. Hardware virtualization might be disabled in BIOS or running inside nested VM."
    log_warn "QEMU emulator will fall back to software emulation (TCG), which runs slower."
fi

echo ""
log_ok "Host prerequisites check and installation complete!"


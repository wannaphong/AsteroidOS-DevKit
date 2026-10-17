# AsteroidOS DevKit

A complete, developer-friendly development kit for **[AsteroidOS](https://asteroidos.org)** — the open-source Linux operating system for smartwatches.

This repository provides automated scripts, an emulator environment, Qt6 SDK setup, build helpers, and a sample project to build, test, package, and deploy AsteroidOS applications.

---

## Table of Contents

- [Features](#features)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [SDK Setup](#sdk-setup)
- [AsteroidOS Emulator](#asteroidos-emulator)
- [Building Applications](#building-applications)
- [Deploying Applications](#deploying-applications)
- [Developing with QtCreator / VS Code](#developing-with-qtcreator--vs-code)
- [Troubleshooting & Tips](#troubleshooting--tips)
- [References](#references)

---

## Features

- **Automated Dependency Setup**: Supports Ubuntu, Debian, Fedora, Arch Linux, and openSUSE.
- **Prebuilt Qt6 SDKs**: Automated download, MD5 verification, and non-root installation for both x86 Emulator (`core2-32`) and real ARM watches (`armv7vehf-neon-sturgeon`).
- **QEMU Emulator Ready**: Automated fetching of the official AsteroidOS kernel and rootfs with GPU hardware acceleration (`virtio-vga-gl`), input tablet/mouse support, and SSH forwarding.
- **One-Command Build & Package**: Compile CMake/Qt6 apps and generate installable `.ipk` packages.
- **Fast Deployment**: SCP/SSH deployment straight to the emulator (`localhost:2222`) or a physical watch (`192.168.2.15`).
- **Sample App Included**: `asteroid-helloworld` pre-configured as a template.

---

## Repository Structure

```text
├── Makefile                   # Convenient shortcuts for common tasks
├── README.md                  # This documentation
├── scripts/
│   ├── install-prereqs.sh     # Installs required host system packages
│   ├── setup-sdk.sh           # Downloads & installs AsteroidOS Qt6 SDK
│   ├── setup-emulator.sh      # Downloads & verifies emulator kernel & rootfs
│   ├── run-emulator.sh        # Launches AsteroidOS in QEMU
│   ├── ssh-emulator.sh        # SSH helper for connecting to the emulator
│   ├── build-app.sh           # Compiles apps & builds .ipk packages
│   └── deploy-app.sh          # Deploys .ipk packages to emulator or watch
├── emulator/                  # Storage for bzImage-emulator.bin and rootfs
├── sample-app/                # Official AsteroidOS sample application (asteroid-helloworld)
└── sdk/                       # Installed SDK toolchain and sysroots (gitignored)
```

---

## Prerequisites

### Host System Requirements

- **Operating System**: Linux (Ubuntu 22.04+, Debian 12+, Fedora 38+, Arch Linux, or openSUSE).
- **Session**: **Wayland** is strongly recommended for the emulator. (Run `echo $XDG_SESSION_TYPE` to check).
- **Virtualization**: KVM support (`/dev/kvm`) for hardware acceleration.
- **Disk Space**: ~10–15 GB free disk space (SDKs ~2.5 GB each, rootfs ~1 GB, sysroots ~5 GB uncompressed).

### Install Host Dependencies

Run the automated prerequisite installer:

```bash
./scripts/install-prereqs.sh
# or
make prereqs
```

This installs `build-essential`, `cmake`, `git`, `python3`, `qemu-system-x86`, `aria2`, `curl`, and checks your `/dev/kvm` permissions.

---

## Quick Start

Follow these 4 simple steps to go from zero to a running AsteroidOS app in the emulator:

### 1. Download Emulator Images

```bash
make setup-emulator
# or: ./scripts/setup-emulator.sh
```

### 2. Install the Qt6 SDK

Install the SDK for the emulator (default):

```bash
make setup-sdk
# or: ./scripts/setup-sdk.sh --target emulator
```

*(Optional: To install the ARM SDK for real watches, run `make setup-sdk-arm`).*

### 3. Build the Sample Application

```bash
make build-sample-emulator
# or: ./scripts/build-app.sh sample-app --target emulator
```

This compiles `sample-app` and generates an `.ipk` package in `sample-app/build-emulator/`.

### 4. Run Emulator & Deploy App

In **Terminal 1**, start the emulator:

```bash
make emulator
# or: ./scripts/run-emulator.sh
```

In **Terminal 2**, deploy the compiled app:

```bash
make deploy-sample
# or: ./scripts/deploy-app.sh sample-app/build-emulator
```

The sample app will appear on the AsteroidOS watch app launcher!

---

## SDK Setup

AsteroidOS uses OpenEmbedded/Yocto cross-toolchains based on Qt6. The DevKit supports two targets:

| Target | Description | SDK Installer Name |
| :--- | :--- | :--- |
| `emulator` | 32-bit x86 target (`core2-32`) for QEMU | `oecore-...-core2-32-emulator-...sh` |
| `arm` | 32-bit ARMv7 target (`armv7vehf-neon`) for physical watches | `oecore-...-armv7vehf-neon-sturgeon-...sh` |

### Installing the SDK

```bash
# Install Emulator SDK (default: installed in ./sdk):
./scripts/setup-sdk.sh --target emulator

# Install ARM SDK:
./scripts/setup-sdk.sh --target arm

# Install both SDKs:
./scripts/setup-sdk.sh --target all

# Custom installation path:
./scripts/setup-sdk.sh --target emulator --dir /opt/asteroidos-sdk
```

### Using the SDK Environment in Shell

After installation, convenient environment scripts are generated:

- For emulator: `source env-emulator.sh`
- For ARM watch: `source env-arm.sh`

Once sourced, your terminal has all cross-compilers (`$CC`, `$CXX`), CMake toolchain variables, and Qt6 paths configured.

---

## AsteroidOS Emulator

The emulator runs AsteroidOS inside QEMU with hardware OpenGL pass-through via Virgil3D / `virtio-vga-gl`.

### Launching the Emulator

```bash
# Standard launch (SDL display, KVM enabled, SSH forwarded to port 2222)
./scripts/run-emulator.sh

# If SDL has issues, use GTK display with visible mouse cursor:
./scripts/run-emulator.sh --display gtk --show-cursor

# Custom resolution (e.g. 480x480 or 800x800):
./scripts/run-emulator.sh --resolution 480x480

# Discard changes on exit (snapshot mode):
./scripts/run-emulator.sh --snapshot
```

### Connecting to Emulator via SSH

The emulator forwards SSH port `22` to host port `2222`:

```bash
# Connect using the helper script:
./scripts/ssh-emulator.sh

# Or connect directly:
ssh -p 2222 ceres@localhost
```

Default credentials:
- Username: `ceres` or `root`
- Password: (no password / blank)

---

## Building Applications

You can build any AsteroidOS CMake application using `./scripts/build-app.sh`:

```bash
# Build for emulator (generates .so and .ipk):
./scripts/build-app.sh sample-app --target emulator

# Build for physical ARM smartwatch:
./scripts/build-app.sh sample-app --target arm

# Clean build:
./scripts/build-app.sh sample-app --clean
```

### Manual Build Steps

If you prefer using CMake directly:

```bash
# 1. Source environment
source env-emulator.sh   # (or source env-arm.sh)

# 2. Configure and build
cmake -B build -DCMAKE_INSTALL_PREFIX:PATH=/usr
cmake --build build

# 3. Create .ipk package
cmake --build build --target package
```

---

## Deploying Applications

Use `./scripts/deploy-app.sh` to upload and install packages via `opkg`:

### Deploy to Emulator

```bash
# Auto-detect IPK in build directory:
./scripts/deploy-app.sh sample-app/build-emulator

# Or specify an IPK file directly:
./scripts/deploy-app.sh sample-app/build-emulator/asteroid-helloworld-2.1.0.ipk
```

### Deploy to Physical Watch

Connect your watch via USB (default IP: `192.168.2.15`):

```bash
# Deploy to USB-connected watch:
./scripts/deploy-app.sh sample-app/build-arm --target watch

# Deploy to watch on custom Wi-Fi IP:
./scripts/deploy-app.sh app.ipk --target watch --host 192.168.1.105
```

---

## Developing with QtCreator / VS Code

### Visual Studio Code

The `sample-app` includes a `.vscode/` folder. When opening the project:
1. Ensure the **CMake Tools** and **C/C++** extensions are installed.
2. In your terminal, run `source env-emulator.sh` (or `source env-arm.sh`).
3. Launch VS Code from that terminal: `code .`
4. CMake Tools will automatically detect the cross-compiler toolchain and sysroot headers.

### Qt Creator

1. Open Qt Creator.
2. Go to **Settings > Build & Run > Kits**.
3. Add a new Compiler pointing to `$BASE_DIR/sdk/sysroots/x86_64-*-linux/usr/bin/...-g++`.
4. Add Qt Version pointing to `qmake` in the SDK sysroot.
5. Add CMake Tool pointing to `cmake` in the SDK sysroot.
6. Create a Kit using these tools and set Sysroot to `$BASE_DIR/sdk/sysroots/core2-32-*-linux`.

---

## Troubleshooting & Tips

### 1. Screen Turns Off in Emulator (Display Lockup)

AsteroidOS blanks the display after an idle timeout. To keep the display permanently awake during development, enable **Demo Mode**:

```bash
./scripts/ssh-emulator.sh -u root -- mcetool -D on
```

To turn demo mode off:
```bash
./scripts/ssh-emulator.sh -u root -- mcetool -D off
```

### 2. Clicks Misaligned or Not Registering

- Launch the emulator with `--show-cursor` or `--display gtk`:
  ```bash
  ./scripts/run-emulator.sh --display gtk --show-cursor
  ```
- Resizing the QEMU window taller often helps calibrate vertical touch positions.
- Verify `ceres` user is in `input` group:
  ```bash
  ./scripts/ssh-emulator.sh -u root -- "usermod -a -G input ceres && systemctl restart user@1000"
  ```

### 3. X11 vs Wayland Graphic Artifacts

The AsteroidOS emulator requires OpenGL pass-through via Virgl. Under X11, some window managers cause black screens or crashes.
- Check session: `echo $XDG_SESSION_TYPE`
- If on X11, switch to a Wayland session at login.
- If using NVIDIA proprietary drivers, try running with `--display gtk`.

### 4. Running App Directly via CLI (Invoker)

To run or debug your app via SSH without touching the UI:

```bash
# Connect to watch/emulator
./scripts/ssh-emulator.sh

# Run with invoker:
QT_QPA_PLATFORM=wayland invoker --single-instance --type=qtcomponents-qt6 /usr/lib/asteroid-helloworld.so
```

### 5. Adding Translations

AsteroidOS applications use Qt Linguist with ID-based translations (`qsTrId`):

```bash
# Update translation files (.ts) in sample-app/i18n:
cd sample-app
lupdate-qt6 -no-obsolete src/* i18n/*.h -ts i18n/*.ts
```

---

## References

- [AsteroidOS Official Website](https://asteroidos.org)
- [AsteroidOS Documentation Wiki](https://wiki.asteroidos.org)
- [Installing the SDK Guide](https://wiki.asteroidos.org/index.php/Installing_the_SDK)
- [Emulator Wiki Page](https://wiki.asteroidos.org/index.php/Emulator)
- [Creating an Asteroid App](https://wiki.asteroidos.org/index.php/Creating_an_Asteroid_app)
- [AsteroidOS GitHub Organization](https://github.com/AsteroidOS)
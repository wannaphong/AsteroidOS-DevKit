# Standalone Python Runtime Packaging (AppImage-Style) for AsteroidOS

## 1. Introduction & Motivation

AsteroidOS is an open-source Linux distribution engineered specifically for smartwatches and wearable devices. To optimize for constrained flash storage and battery life, stock AsteroidOS system images are minimal and **do not pre-install Python 3 or PySide6**.

Traditionally, running a Python application on embedded Linux required:
1. Setting up external package feeds (`opkg update`).
2. Installing large system packages (`python3-core`, `python3-pyside6`, `python3-modules`) directly to rootfs.
3. Managing system library conflicts and broken package dependencies across OS releases.

The **AsteroidOS Python SDK** solves this challenge by introducing **Standalone Runtime Packaging (AppImage-Style)**. Similar to how AppImage, Flatpak, or macOS application bundles work, each Python watch application can be built into a completely self-contained `.ipk` package embedding its own dedicated Python interpreter, standard library, and Qt6/PySide6 bindings.

---

## 2. Core Architecture

When an application is packaged with `standalone=True` (the default for `Target.EMULATOR` and `Target.ARM`/`Target.WATCH`), the SDK extracts target-architecture binaries from the cross-compilation sysroot (`sdk/sysroots/`) and organizes them into an isolated directory structure inside `/usr/share/<app-name>/python/`.

### Bundle Directory Layout

```
/usr/
├── bin/
│   └── <app-name>                                   # Optimized shell launcher script
├── share/
│   ├── applications/
│   │   └── <app-name>.desktop                       # Asteroid-launcher desktop entry
│   └── <app-name>/
│       ├── main.py                                  # Application entry point
│       ├── main.qml                                 # Asteroid UI interface
│       ├── asteroid.json                            # App metadata
│       └── python/                                  # Embedded standalone runtime
│           ├── bin/
│           │   └── python3                          # Target ELF interpreter
│           ├── lib/
│           │   ├── libpython3.13.so.1.0             # Python shared library
│           │   ├── libpyside6.abi3.so.6.11          # PySide6 C++ binding runtime
│           │   ├── libpyside6qml.abi3.so.6.11       # PySide6 QML C++ bridge
│           │   ├── libshiboken6.abi3.so.6.11.0      # Shiboken dynamic binding engine
│           │   └── python3.13/
│           │       ├── *.py                         # Core standard library modules
│           │       ├── pathlib/                     # Full pathlib directory package
│           │       ├── ctypes/                      # C types interoperability
│           │       ├── urllib/, xml/, json/, re/    # Standard utilities & data formats
│           │       ├── lib-dynload/                 # Target C extensions (.so)
│           │       └── site-packages/
│           │           ├── shiboken6/               # Shiboken Python package
│           │           └── PySide6/                 # PySide6 modules (QtCore, QtGui,
│           │                                        # QtQml, QtQuick, QtOpenGL, etc.)
```

---

## 3. Bundled Runtime Components

The standalone bundler packages only the essential runtime components necessary to execute Qt/QML watch applications without bloating the package size:

| Category | Components Included | Purpose |
| :--- | :--- | :--- |
| **Interpreter & Libs** | `python3.13`, `libpython3.13.so.1.0` | Target architecture ELF executable and shared library |
| **PySide6 C++ Bridges** | `libpyside6.abi3.so`, `libpyside6qml.abi3.so`, `libshiboken6.abi3.so` | Shared dynamic libraries linking Qt6 with Python |
| **PySide6 Modules** | `QtCore`, `QtGui`, `QtQml`, `QtQuick`, `QtQuickControls2`, `QtNetwork`, `QtOpenGL`, `QtDBus`, `QtSensors` | Qt GUI, Wayland rendering, QML engine, and hardware sensor access |
| **Standard Library** | `pathlib`, `ctypes`, `urllib`, `xml`, `logging`, `zipfile`, `asyncio`, `email`, `html`, `http`, `concurrent`, `json`, `collections`, `encodings` | Essential Python stdlib packages required by PySide6 and app logic |
| **C Extensions (`lib-dynload`)** | `_ctypes.so`, `_json.so`, `math.so`, `_datetime.so`, `_struct.so`, `_posixsubprocess.so`, `unicodedata.so`, `zlib.so`, `binascii.so`, `select.so`, `fcntl.so` | Native acceleration modules for filesystem, string processing, and math |

---

## 4. Key Engineering Innovations

### 1. Zero Host OS Dependencies
In standard Debian/OPKG packaging, applications declare dependencies via the `Depends:` control field. A standalone bundle requires no external host packages:

```ini
Package: asteroid-pycounter
Version: 1.0.0
Architecture: core2-32
Maintainer: AsteroidOS Developer <developer@asteroidos.org>
Description: Interactive counter watch app written in Python with PySide6
Section: user/apps
Priority: optional
Installed-Size: 28500
```
Because `Depends:` does not require `python3-core` or `python3-pyside6`, `opkg install` succeeds immediately on stock AsteroidOS releases.

### 2. ELF Symlink Preservation
Dynamic linkers look up libraries by their `SONAME` (e.g., `libshiboken6.abi3.so.6.11` linking to `libshiboken6.abi3.so.6.11.0`). If symlinks are flattened into duplicated regular files, package size and flash storage double.

The SDK's pure-Python `IpkPackager` creates true POSIX `SYMTYPE` entries inside `data.tar.gz`. The symlinks resolve locally inside `/usr/share/<app-name>/python/lib/`, saving ~15MB of precious smartwatch storage.

### 3. Isolated Launcher Wrapper
The launcher script installed at `/usr/bin/<app-name>` isolates the bundled environment from any system Python or global libraries:

```bash
#!/bin/sh
APP_DIR="/usr/share/<app-name>"
if [ -d "$APP_DIR/python" ] && [ -x "$APP_DIR/python/bin/python3" ]; then
    export PYTHONHOME="$APP_DIR/python"
    export PYTHONPATH="$APP_DIR:$APP_DIR/python/lib/python3.13:$APP_DIR/python/lib/python3.13/site-packages:$PYTHONPATH"
    export LD_LIBRARY_PATH="$APP_DIR/python/lib:$LD_LIBRARY_PATH"
    exec "$APP_DIR/python/bin/python3" "$APP_DIR/main.py" "$@"
elif command -v python3 >/dev/null 2>&1; then
    export PYTHONPATH="$APP_DIR:$PYTHONPATH"
    exec python3 "$APP_DIR/main.py" "$@"
else
    echo "Error: Python runtime not found." >&2
    exit 1
fi
```

### 4. Space-Constrained Target Deployment
Embedded watch storage is small (~800MB rootfs on emulator). The deployment tooling incorporates:
- **Legacy SCP Protocol (`-O`)**: Prevents SFTP buffer truncation errors on OpenSSH 9+ hosts.
- **Journal Log Vacuuming**: Automatically runs `journalctl --vacuum-time=1s` before file transfer to prevent out-of-disk (`ENOSPC`) errors.
- **Package List Cleanup**: Cleans stale `/var/lib/opkg/lists/*` cache files before uploading large packages.

### 5. PyPI Packages with Native Compiler Support (NumPy, etc.)
Many modern Python wearable applications require scientific or mathematical libraries like **NumPy** or compiled speedups like **MarkupSafe**. Because PyPI usually only provides 64-bit x86_64 or desktop wheels, targeting embedded 32-bit `core2-32` or ARM smartwatches requires cross-compiling from source.

The AsteroidOS Python SDK automates the entire cross-compilation pipeline:
- **Automatic SDK Cross-Compiler Detection**: Leverages the DevKit cross toolchain (`i686-oe-linux-gcc` / `armv7...`) and OpenEmbedded target sysroot.
- **Sysconfig Bridge**: Configures target `_sysconfigdata` and Python 3.13 headers so native C/C++ builds (using `setuptools`, `meson-python`, or `ninja`) target the smartwatch architecture rather than the host.
- **Wheelhouse Caching**: Pre-compiles target wheels into `~/.cache/asteroidos/wheels/<arch>/` so that subsequent builds don't need to recompile NumPy from source.
- **Seamless Declaration**: Dependencies can be declared in `asteroid.json` (`"pip_dependencies"`), in `requirements.txt`, or programmatically via `app.add_pip_package("numpy")`.

---

## 5. Usage Guide

### A. Packaging with the `asteroidos` CLI

```bash
# Package for QEMU Emulator (default, core2-32 architecture):
asteroidos package sample-python-app --target emulator

# Package for Physical Smartwatch (ARMv7 architecture):
asteroidos package sample-python-app --target watch

# Deploy package to target device:
asteroidos deploy sample-python-app/dist --target emulator
```

### B. Packaging via Python SDK API

```python
from asteroidos import App, Target

# Load an existing project directory containing asteroid.json
app = App.load("sample-python-app")

# Package standalone self-contained .ipk bundle
ipk_path = app.package(target=Target.EMULATOR, standalone=True)
print(f"Generated standalone IPK: {ipk_path}")

# Deploy directly to emulator over SSH/SCP
app.deploy(target=Target.EMULATOR, ipk_path=ipk_path)
```

### C. Using the Makefile

The root Makefile provides shortcuts for building and deploying:

```bash
# Build standalone sample-python-app
make build-sample-python

# Deploy to running emulator (localhost:2222)
make deploy-sample-python
```

---

## 6. Sample Application (`sample-python-app`)

A reference implementation is located in `sample-python-app/`:

### 1. `asteroid.json` (Metadata)
```json
{
  "name": "asteroid-pycounter",
  "title": "Python Counter",
  "version": "1.0.0",
  "description": "Interactive counter watch app written in Python with PySide6",
  "author": "AsteroidOS Developer <developer@asteroidos.org>",
  "icon": "ios-pulse-outline",
  "center_color": "#2c3e50",
  "outer_color": "#1a252f",
  "type": "python"
}
```

### 2. `main.py` (PySide6 Backend Bridge)
```python
import os
import sys

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView


class CounterBackend(QObject):
    countChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._count = 0

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return self._count

    @Slot()
    def increment(self):
        self._count += 1
        self.countChanged.emit(self._count)

    @Slot()
    def decrement(self):
        if self._count > 0:
            self._count -= 1
            self.countChanged.emit(self._count)

    @Slot()
    def reset(self):
        self._count = 0
        self.countChanged.emit(self._count)


def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("asteroid-pycounter")

    view = QQuickView()
    backend = CounterBackend()

    # Expose Python backend object to QML context
    context = view.rootContext()
    context.setContextProperty("counter", backend)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    view.setSource(QUrl.fromLocalFile(os.path.join(current_dir, "main.qml")))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.showFullScreen()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

### 3. `main.qml` (AsteroidOS User Interface)
```qml
import QtQuick
import org.asteroid.controls

Application {
    id: app
    centerColor: "#2c3e50"
    outerColor: "#1a252f"

    Item {
        anchors.fill: parent

        Label {
            id: titleLabel
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: parent.height * 0.28
            text: "Counter"
            font.pixelSize: 18
            color: "#ecf0f1"
        }

        Label {
            id: countLabel
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: titleLabel.bottom
            anchors.topMargin: 8
            text: counter.count.toString()
            font.pixelSize: 42
            font.bold: true
            color: "#ffffff"
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: parent.height * 0.25
            spacing: 24

            IconButton {
                iconName: "ios-minus-empty"
                onClicked: counter.decrement()
            }
            IconButton {
                iconName: "ios-refresh-empty"
                onClicked: counter.reset()
            }
            IconButton {
                iconName: "ios-plus-empty"
                onClicked: counter.increment()
            }
        }
    }
}
```

---

## 7. AsteroidOS QML UI Components (`qml-asteroid`)

AsteroidOS applications pair a Python/PySide6 backend with declarative QML frontends powered by **[`qml-asteroid`](https://github.com/AsteroidOS/qml-asteroid)**.

### Available QML Modules:
- **`org.asteroid.controls`**: Native wearable UI widgets designed for both round and square smartwatches:
  - **Layout & Structure**: `Application` (root item with flat mesh gradient & swipe indicators), `LayerStack` (push/pop multi-page navigation with edge swipe-back), `PageHeader`, `StatusPage`.
  - **Buttons & Toggles**: `IconButton` (vector Ionicons button), `Switch`, `LabeledSwitch`, `LabeledActionButton`.
  - **Lists & Selection**: `ListItem`, `ListRow`, `IntSelector` (pill scrubber), `OptionCycler`, `Spinner`, `CircularSpinner`.
  - **Gauges & Feedback**: `RemorseTimer` (cancellable action countdown), `ValueMeter` (wave meter with particles), `SegmentedArc` (circular progress), `Marquee` (scrolling text).
  - **Responsive Sizing**: `Dims` singleton (`Dims.w()`, `Dims.h()`, `Dims.l()`) dynamically scales coordinates across varied watch resolutions and shapes.
- **`org.asteroid.utils`**: Direct hardware capabilities:
  - `DeviceSpecs`: Screen shape (`hasRoundScreen`), Moto 360 chin cutout (`flatTireHeight`), speaker/WLAN hardware availability, and OLED burn-in requirements (`needsBurnInProtection`).
  - `WallClock`: High-efficiency system clock aligned to second/minute/day boundaries.
  - `BluetoothStatus`: Bluetooth power and companion connection state.
- **`org.asteroid.settings`**: System settings including `DisplaySettings`, `DateTimeSettings`, and `LanguageModel`.

📖 **Full Reference & API Guide**: For comprehensive property tables, component details, and complete runnable examples, see **[QML Controls & UI Toolkit Guide (python-sdk/docs/qml_asteroid.md)](python-sdk/docs/qml_asteroid.md)**.

---

## 8. Troubleshooting & FAQs

### Q: Why does `scp` fail with `write remote: Failure` when uploading?
- **Cause 1**: OpenSSH 9.0+ uses SFTP by default, which can fail on embedded SSH servers.
  - **Fix**: Use `scp -O` (legacy SCP protocol). The SDK scripts include this automatically.
- **Cause 2**: Rootfs is out of space (`ENOSPC`).
  - **Fix**: Run `sudo journalctl --vacuum-time=1s` and `sudo rm -rf /var/lib/opkg/lists/*` on the device.

### Q: How do I test running the application from an SSH session?
To run a GUI application via SSH on AsteroidOS, you must specify the Wayland display and runtime directory:
```bash
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-0
/usr/bin/asteroid-pycounter
```

### Q: How do I take a screenshot of the running app on the emulator?
Use the built-in `screenshottool` utility:
```bash
export XDG_RUNTIME_DIR=/run/user/1000
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
screenshottool /tmp/screen.png
```
Or use the Python SDK command:
```bash
asteroidos screenshot
```


# AsteroidOS Python SDK

The official Python SDK and command-line interface for developing, building, packaging, and deploying applications for **[AsteroidOS](https://asteroidos.org)** — the open-source Linux operating system for smartwatches.

---

> 📖 **Documentation**:
> - **[QML Controls & UI Toolkit Guide (qml-asteroid)](docs/qml_asteroid.md)**: Complete guide to AsteroidOS QML controls (`Application`, `LayerStack`, `IconButton`, `IntSelector`, `ValueMeter`, etc.), `Dims` responsive layouts, system utilities (`DeviceSpecs`, `WallClock`, `BluetoothStatus`), and PySide6 integration.
> - **[Architecture & Deep Dive (python_sdk.md)](../python_sdk.md)**: Full details on AppImage-style standalone runtime bundling, ELF symlink handling, and target deployment.

---

## Features

- **Develop Apps in Python**:
  - Build native AsteroidOS C++/Qt6 QML applications directly using a Python API.
  - Build pure Python applications (using PySide6 and standard AsteroidOS QML controls).
- **Pure-Python IPK Packaging**:
  - Built-in Debian/OPKG `.ipk` generator and parser (zero binary dependencies required to package apps).
- **Automated Cross-Compilation**:
  - Seamlessly invokes the AsteroidOS OpenEmbedded SDK toolchain for both the Emulator (`core2-32`) and physical watches (`armv7vehf-neon`).
- **Emulator & Device Automation**:
  - Start, stop, and inspect the QEMU emulator.
  - Deploy `.ipk` packages over SSH/SCP with automatic `opkg` installation.
  - Capture watch display screenshots directly via Python.
- **Unified CLI Tool (`asteroidos`)**:
  - `asteroidos new`, `build`, `package`, `deploy`, `emulator`, `screenshot`, and `doctor`.

---

## Installation

```bash
# Editable install from repository:
pip install -e ./python-sdk

# Or directly:
pip install ./python-sdk
```

---

## Quick Start (CLI)

### 1. Scaffold a New Application

```bash
# Create a native C++/QML application
asteroidos new my-watch-app --title "My App" --template qml_cpp

# Or create a Python-based application
asteroidos new my-python-app --title "Python Watch App" --template python
```

### 2. Build the Application

```bash
cd my-watch-app

# Build for QEMU emulator (default)
asteroidos build --target emulator

# Build for real smartwatch
asteroidos build --target arm
```

### 3. Deploy to Emulator or Watch

```bash
# Deploy to emulator (localhost:2222)
asteroidos deploy --target emulator

# Deploy to physical watch (over USB / Bluetooth at 192.168.2.15)
asteroidos deploy --target watch
```

---

## Python API Usage

### Example 1: Create a Native AsteroidOS App in Python

```python
from asteroidos import App, AppType, Target
import asteroidos.icons as icons

app = App(
    name="asteroid-dice",
    title="Dice Roller",
    version="1.0.0",
    description="Roll dice on your AsteroidOS watch",
    author="Dev <dev@example.org>",
    icon=icons.IOS_GAME_CONTROLLER_B_OUTLINE,
    center_color="#e67e22",
    outer_color="#d35400",
    app_type=AppType.NATIVE_QML,
)

# Custom QML user interface
app.set_main_qml("""
import QtQuick
import org.asteroid.controls

Application {
    id: app
    centerColor: "#e67e22"
    outerColor: "#d35400"

    Label {
        anchors.centerIn: parent
        text: "🎲 Roll: 6"
        font.pixelSize: 32
    }
}
""")

# Generate project and build .ipk package
app.generate_project("/tmp/asteroid-dice")
ipk_path = app.build(target=Target.EMULATOR)
print(f"Created: {ipk_path}")

# Deploy to emulator
app.deploy(target=Target.EMULATOR)
```

---

### Example 2: Create a Python Watch App (PySide6)

```python
from asteroidos import App, AppType, Target
import asteroidos.icons as icons

app = App(
    name="asteroid-pycounter",
    title="Step Counter",
    version="1.0.0",
    icon=icons.IOS_PULSE_OUTLINE,
    app_type=AppType.PYTHON_QML,
)

# Custom Python backend logic
app.set_main_py("""
import sys, os
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QUrl

def main():
    qapp = QGuiApplication(sys.argv)
    view = QQuickView()
    qml_file = os.path.join(os.path.dirname(__file__), "main.qml")
    view.setSource(QUrl.fromLocalFile(qml_file))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.showFullScreen()
    return qapp.exec()

if __name__ == "__main__":
    sys.exit(main())
""")

# Package standalone self-contained bundle for emulator (AppImage-style)
# Bundles Python 3.13, PySide6, and standard library from SDK sysroot:
ipk_file = app.package(target=Target.EMULATOR, standalone=True)
print(f"Packaged standalone: {ipk_file}")

# Or package for physical watch:
# ipk_file = app.package(target=Target.WATCH, standalone=True)
```

#### Standalone Packaging (AppImage-style for Python)

Because AsteroidOS minimal OS images do not include `python3` by default, the AsteroidOS Python SDK supports **standalone runtime bundling** (AppImage-style):

- **Self-Contained Runtime**: Automatically bundles the target architecture's Python interpreter (`python3`), shared libraries (`libpython3.so`, `libpyside6.so`, `libshiboken6.so`), standard library modules, and PySide6 Qt bindings from the SDK sysroot into `/usr/share/<app-name>/python/`.
- **Zero OS Dependencies**: The resulting `.ipk` package requires zero host Python packages (`Depends:` is empty for Python), running cleanly on stock AsteroidOS releases.
- **Smart Symlink Preservation**: The built-in packager preserves ELF shared library symlinks, avoiding duplicate disk usage on space-constrained watch storage.
- **Wrapper Launcher**: Automatically installs an optimized `/usr/bin/<app-name>` launcher script configured with isolated `PYTHONHOME`, `PYTHONPATH`, and `LD_LIBRARY_PATH`.

```bash
# Package standalone bundle for emulator (default):
asteroidos package sample-python-app --target emulator

# Package standalone bundle for smartwatch:
asteroidos package sample-python-app --target watch

# Package without bundling runtime (requires host python3-core):
asteroidos package sample-python-app --no-standalone
```

---

### Example 3: Control Emulator & Devices

```python
from asteroidos import Emulator, Device, Target

# Manage emulator
if not Emulator.is_running():
    Emulator.start(daemon=True)
    Emulator.wait_ready(timeout=60)

# Connect to target device
device = Device.for_target(Target.EMULATOR)
if device.is_reachable():
    # Install an application package
    device.install_ipk("my-app.ipk")

    # Capture display screenshot
    device.screenshot("screenshot.png")
---

## AsteroidOS QML Controls (`qml-asteroid`)

AsteroidOS watch applications built with Python use Qt Quick / QML for their visual interface, powered by the [`qml-asteroid`](https://github.com/AsteroidOS/qml-asteroid) component library:

- **`org.asteroid.controls`**: Watch-optimized UI components including `Application`, `Dims` (responsive scaling), `LayerStack` (page navigation), `IconButton`, `IntSelector`, `OptionCycler`, `LabeledSwitch`, `ListItem`, `ValueMeter`, `RemorseTimer`, and `StatusPage`.
- **`org.asteroid.utils`**: Direct hardware and platform access including `DeviceSpecs` (screen shape, OLED burn-in, speaker/WLAN detection), `WallClock` (battery-friendly aligned timer), and `BluetoothStatus` (pairing and connectivity).
- **`org.asteroid.settings`**: System settings including `DisplaySettings`, `DateTimeSettings`, and `LanguageModel`.

👉 For the complete component reference, property tables, and PySide6 two-way binding examples, see **[QML Controls & UI Toolkit Guide](docs/qml_asteroid.md)**.

---

## Running the Example Builds

The repository includes runnable example build scripts in `examples/` and a dedicated `sample-python-app/`:

### 1. Build the Sample Python App (`sample-python-app`)
```bash
# Direct Python script:
python3 sample-python-app/build.py

# Or via make:
make build-sample-python

# Or via asteroidos CLI:
asteroidos package sample-python-app --target all
```
Output: `sample-python-app/dist/asteroid-pycounter-1.0.0.ipk`

### 2. Run Automated Build Examples
```bash
# Example 1: Builds a Native C++/QML app with cross-toolchain into an .ipk
python3 python-sdk/examples/01_create_native_app.py

# Example 2: Packages a PySide6 Python watch app into an .ipk
python3 python-sdk/examples/02_create_python_app.py

# Or run both with Make:
make build-python-examples
```

---

## Command Reference

| Command | Description |
| :--- | :--- |
| `asteroidos new <name>` | Scaffold a new app (`--template qml_cpp` or `python`) |
| `asteroidos build` | Compile application and create `.ipk` package |
| `asteroidos package` | Directly package files into `.ipk` archive |
| `asteroidos deploy` | Deploy `.ipk` to emulator (`:2222`) or watch (`192.168.2.15`) |
| `asteroidos emulator start` | Launch AsteroidOS QEMU emulator |
| `asteroidos emulator stop` | Stop running emulator processes |
| `asteroidos emulator status` | Check emulator execution & SSH status |
| `asteroidos screenshot` | Capture screenshot of running emulator/watch |
| `asteroidos doctor` | Diagnose host system, KVM, QEMU, and SDK setup |
| `asteroidos templates` | List available app templates |


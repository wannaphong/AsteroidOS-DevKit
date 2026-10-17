# AsteroidOS Python Sample Application (asteroid-pycounter)

An official sample application for **AsteroidOS** written in **Python** using **PySide6** and **Asteroid controls** (`org.asteroid.controls`).

---

## Structure

```text
sample-python-app/
├── asteroid.json                   # App manifest and metadata
├── main.py                         # PySide6 application entry point & backend logic
├── main.qml                        # AsteroidOS QML user interface
├── asteroid-pycounter.desktop      # Desktop launcher entry
├── runscript.sh                    # Launcher script
├── build.py                        # Standalone build script
└── README.md                       # This documentation
```

---

## Building the Application

### Option 1: Using the Standalone Build Script

```bash
python3 sample-python-app/build.py
```

### Option 2: Using Makefile

```bash
make build-sample-python
```

### Option 3: Using the `asteroidos` CLI

```bash
asteroidos package sample-python-app --target all
```

The resulting package will be created in `sample-python-app/dist/asteroid-pycounter-1.0.0.ipk`.

---

## Deploying to Emulator or Watch

```bash
# Using make:
make deploy-sample-python

# Using asteroidos CLI:
asteroidos deploy sample-python-app/dist/asteroid-pycounter-1.0.0.ipk --target emulator
```


#!/usr/bin/env python3
"""
Example 2: Create and Package a Python-based AsteroidOS Application.

This example creates a Python watch application that runs using PySide6
and Asteroid controls, and packages it into an installable .ipk package.
"""

from pathlib import Path
from asteroidos import App, AppType, Target
import asteroidos.icons as icons

def main():
    print("=== Creating Python-based AsteroidOS App ===")

    # 1. Define application
    app = App(
        name="asteroid-pytimer",
        title="Python Timer",
        version="1.0.0",
        description="Stopwatch and timer application written in Python",
        author="AsteroidOS Developer <dev@example.org>",
        icon=icons.IOS_STOPWATCH_OUTLINE,
        center_color="#2c3e50",
        outer_color="#1a252f",
        app_type=AppType.PYTHON_QML,
        dependencies=["python3-core", "python3-pyside6"],
    )

    # Add PyPI package dependencies (cross-compiled for target architecture)
    # app.add_pip_package("numpy")

    # 2. Add custom Python backend logic
    app.set_main_py("""#!/usr/bin/env python3
import sys
import os
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QUrl, QObject, Signal, Slot, Property, QTimer

class TimerBackend(QObject):
    secondsChanged = Signal(int)

    def __init__(self):
        super().__init__()
        self._seconds = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    @Property(int, notify=secondsChanged)
    def seconds(self):
        return self._seconds

    def _tick(self):
        self._seconds += 1
        self.secondsChanged.emit(self._seconds)

    @Slot()
    def start(self):
        self._timer.start()

    @Slot()
    def stop(self):
        self._timer.stop()

    @Slot()
    def reset(self):
        self._timer.stop()
        self._seconds = 0
        self.secondsChanged.emit(0)

def main():
    qapp = QGuiApplication(sys.argv)
    view = QQuickView()
    backend = TimerBackend()

    view.rootContext().setContextProperty("timerBackend", backend)
    qml_file = os.path.join(os.path.dirname(__file__), "main.qml")
    view.setSource(QUrl.fromLocalFile(qml_file))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.showFullScreen()
    return qapp.exec()

if __name__ == "__main__":
    sys.exit(main())
""")

    # 3. Add custom QML interface
    app.set_main_qml("""import QtQuick
import org.asteroid.controls

Application {
    id: app
    centerColor: "#2c3e50"
    outerColor: "#1a252f"

    Column {
        anchors.centerIn: parent
        spacing: 16

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Seconds: " + timerBackend.seconds
            font.pixelSize: 32
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 12

            Button {
                text: "Start"
                onClicked: timerBackend.start()
            }

            Button {
                text: "Stop"
                onClicked: timerBackend.stop()
            }
        }
    }
}
""")

    # 4. Generate project and package into .ipk
    project_dir = Path("/tmp/asteroid-pytimer")
    app.generate_project(project_dir, overwrite=True)
    print(f"Project generated in {project_dir}")

    # 5. Build .ipk package directly in Python (pure-Python, no CMake needed!)
    ipk_path = app.package(target=Target.ALL)
    print(f"Package created: {ipk_path}")

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
AsteroidOS Python Sample Application.
Interactive Counter implemented using PySide6 and Asteroid controls.
"""

import os
import sys

try:
    from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuick import QQuickView
except ImportError:
    print("[ERROR] PySide6 is required to run AsteroidOS Python applications.")
    sys.exit(1)


class CounterBackend(QObject):
    """Python backend bridge exposing properties and slots to QML."""

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
    app.setOrganizationName("AsteroidOS")

    view = QQuickView()
    backend = CounterBackend()

    # Expose Python backend to QML engine context
    context = view.rootContext()
    context.setContextProperty("counter", backend)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    qml_path = os.path.join(current_dir, "main.qml")

    view.setSource(QUrl.fromLocalFile(qml_path))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.showFullScreen()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
{{ app_name }} - AsteroidOS Python Application
"""

import os
import sys

try:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuick import QQuickView
    from PySide6.QtCore import QUrl, QObject, Signal, Slot, Property
except ImportError:
    print("[ERROR] PySide6 is required to run this AsteroidOS Python application.")
    sys.exit(1)


class AppBackend(QObject):
    """Python backend bridge exposing properties and slots to QML."""

    titleChanged = Signal(str)
    countChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._title = "{{ title }}"
        self._count = 0

    @Property(str, notify=titleChanged)
    def title(self):
        return self._title

    @Property(int, notify=countChanged)
    def count(self):
        return self._count

    @Slot()
    def increment(self):
        self._count += 1
        self.countChanged.emit(self._count)

    @Slot()
    def reset(self):
        self._count = 0
        self.countChanged.emit(self._count)


def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("{{ app_name }}")
    app.setOrganizationName("AsteroidOS")

    view = QQuickView()
    backend = AppBackend()

    # Expose Python backend to QML engine context
    context = view.rootContext()
    context.setContextProperty("backend", backend)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    qml_path = os.path.join(current_dir, "main.qml")

    view.setSource(QUrl.fromLocalFile(qml_path))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.showFullScreen()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())


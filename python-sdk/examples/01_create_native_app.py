#!/usr/bin/env python3
"""
Example 1: Create a Native AsteroidOS App from Python.

This example creates a native C++/Qt6 QML AsteroidOS application,
sets custom QML markup, generates the project, and builds an .ipk package.
"""

from pathlib import Path
from asteroidos import App, AppType, Target
import asteroidos.icons as icons

def main():
    print("=== Creating Native AsteroidOS App ===")

    # 1. Define application metadata
    app = App(
        name="asteroid-dice",
        title="Dice Roller",
        version="1.0.0",
        description="A roll-the-dice application for AsteroidOS",
        author="AsteroidOS Fan <fan@asteroidos.org>",
        icon=icons.IOS_GAME_CONTROLLER_B_OUTLINE,
        center_color="#e67e22",
        outer_color="#d35400",
        app_type=AppType.NATIVE_QML,
    )

    # 2. Customize QML interface
    custom_qml = """import QtQuick
import org.asteroid.controls

Application {
    id: app
    centerColor: "#e67e22"
    outerColor: "#d35400"

    property int diceValue: 1

    Column {
        anchors.centerIn: parent
        spacing: 20

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "🎲 " + app.diceValue
            font.pixelSize: 42
        }

        Button {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Roll"
            onClicked: {
                app.diceValue = Math.floor(Math.random() * 6) + 1
            }
        }
    }
}
"""
    app.set_main_qml(custom_qml)

    # 3. Generate project files
    project_dir = Path("/tmp/asteroid-dice")
    print(f"Generating project in {project_dir}...")
    app.generate_project(project_dir, overwrite=True)
    print("Project generated successfully!")

    # 4. Build for emulator (if DevKit environment is available)
    try:
        print("Compiling and packaging .ipk for Emulator...")
        ipk_path = app.build(target=Target.EMULATOR)
        print(f"Success! Package built at: {ipk_path}")
    except Exception as e:
        print(f"Note: Compilation requires AsteroidOS SDK installed: {e}")

if __name__ == "__main__":
    main()


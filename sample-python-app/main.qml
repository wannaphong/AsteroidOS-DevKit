import QtQuick
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
            text: "Counter"
            font.pixelSize: 24
            font.bold: true
        }

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: counter.count
            font.pixelSize: 48
            font.bold: true
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 20

            IconButton {
                iconName: "ios-remove"
                onClicked: counter.decrement()
            }

            IconButton {
                iconName: "ios-refresh"
                onClicked: counter.reset()
            }

            IconButton {
                iconName: "ios-add"
                onClicked: counter.increment()
            }
        }
    }
}


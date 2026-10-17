import QtQuick
import org.asteroid.controls

Application {
    id: app

    centerColor: "{{ center_color }}"
    outerColor: "{{ outer_color }}"

    Column {
        anchors.centerIn: parent
        spacing: 16

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: backend.title
            font.pixelSize: 24
            font.bold: true
        }

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Count: " + backend.count
            font.pixelSize: 20
        }

        IconButton {
            anchors.horizontalCenter: parent.horizontalCenter
            iconName: "ios-add"
            onClicked: backend.increment()
        }
    }
}


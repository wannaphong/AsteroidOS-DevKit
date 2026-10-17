import QtQuick
import org.asteroid.controls

Application {
    id: app

    centerColor: "{{ center_color }}"
    outerColor: "{{ outer_color }}"

    Label {
        id: hello
        anchors.centerIn: parent
        horizontalAlignment: Text.AlignHCenter
        text: "{{ title }}"
        font.pixelSize: 28
    }
}


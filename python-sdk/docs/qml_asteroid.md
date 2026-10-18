# AsteroidOS QML Controls (`qml-asteroid`) for Python SDK

This guide documents the **[qml-asteroid](https://github.com/AsteroidOS/qml-asteroid)** UI component library and how to build responsive, beautiful smartwatch interfaces in Python using the **AsteroidOS Python SDK** and **PySide6**.

---

## 1. Overview & Architecture

AsteroidOS applications use Qt Quick / QML for user interfaces. The `qml-asteroid` library provides the standard look, feel, gestures, and wearable components designed specifically for smartwatch displays (both circular and rectangular).

When writing AsteroidOS applications in Python:
- **Frontend (QML)**: Declares the UI hierarchy using AsteroidOS QML modules (`org.asteroid.controls`, `org.asteroid.utils`, `org.asteroid.settings`).
- **Backend (Python / PySide6)**: Implements business logic, sensor processing, networking, and hardware control via `QObject`, `@Property`, `Signal`, and `@Slot`.
- **Runtime**: Runs directly under AsteroidOS Wayland compositor (`lipstick`) using PySide6's `QQuickView` and `QGuiApplication`.

```
┌────────────────────────────────────────────────────────┐
│           AsteroidOS Smartwatch Screen (Wayland)        │
└────────────────────────────────────────────────────────┘
                           ▲
                           │ renders
┌────────────────────────────────────────────────────────┐
│                org.asteroid.controls                   │
│   Application, LayerStack, IconButton, IntSelector...  │
│  ────────────────────────────────────────────────────  │
│                 org.asteroid.utils                     │
│      DeviceSpecs, WallClock, BluetoothStatus...        │
└────────────────────────────────────────────────────────┘
                           ▲
                           │ QML Context Properties / Signals
┌────────────────────────────────────────────────────────┐
│           Python Application Logic (PySide6)           │
│     class WatchBackend(QObject): @Property, @Slot      │
│  ────────────────────────────────────────────────────  │
│         Standalone Bundled Python 3.13 Runtime          │
└────────────────────────────────────────────────────────┘
```

---

## 2. Setting Up PySide6 with AsteroidOS QML

A minimal AsteroidOS Python application initializes `QGuiApplication`, instantiates a `QQuickView`, registers Python backend objects into the QML context, and launches full screen:

### Python Entry Point (`main.py`)

```python
import os
import sys
from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView


class WatchBackend(QObject):
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
    def reset(self):
        self._count = 0
        self.countChanged.emit(self._count)


def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("asteroid-demo")

    view = QQuickView()
    backend = WatchBackend()

    # Expose Python backend to QML
    view.rootContext().setContextProperty("backend", backend)

    qml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.qml")
    view.setSource(QUrl.fromLocalFile(qml_file))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.showFullScreen()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

### QML User Interface (`main.qml`)

```qml
import QtQuick
import org.asteroid.controls

Application {
    id: app
    centerColor: "#2c3e50"
    outerColor: "#1a252f"

    Column {
        anchors.centerIn: parent
        spacing: Dims.h(4)

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Count: " + backend.count
            font.pixelSize: Dims.l(10)
        }

        IconButton {
            anchors.horizontalCenter: parent.horizontalCenter
            iconName: "ios-add"
            onClicked: backend.increment()
        }
    }
}
```

---

## 3. Responsive Wearable Design: The `Dims` Singleton

AsteroidOS runs on varied screen form factors:
- **Round Displays**: 360×360, 400×400, 454×454 (e.g. LG G Watch R, TicWatch Pro)
- **Flat-Tire Displays**: Round displays with bottom cutouts (e.g. Moto 360)
- **Square Displays**: 280×280, 320×320 (e.g. LG G Watch, Sony Smartwatch 3)

Never hardcode pixel coordinates. Import `org.asteroid.controls` and use the `Dims` singleton:

```qml
import QtQuick
import org.asteroid.controls

Rectangle {
    width: Dims.w(80)    // 80% of available screen width
    height: Dims.h(40)   // 40% of available screen height (compensating for flat tire)

    Label {
        font.pixelSize: Dims.l(8)  // 8% of the smallest screen dimension
    }
}
```

| Method / Property | Description |
| :--- | :--- |
| `Dims.w(percent)` | Returns `(percent / 100) * screenWidth`. |
| `Dims.h(percent)` | Returns `(percent / 100) * (screenHeight + flatTireHeight)`. |
| `Dims.l(percent)` | Returns `percent` of the **smaller** of width or adjusted height. Ideal for font sizes, square icons, and circular gauges. |
| `Dims.iconButtonMargin` | Recommended margin around icon buttons (`Dims.l(3)`). |
| `Dims.defaultFontSize` | Standard application font size (`Dims.l(7)`). |

---

## 4. `org.asteroid.controls` Component Reference

### 4.1 Application & Layout

#### `Application`
The top-level root element for every AsteroidOS application. Renders an interactive mesh gradient background (`FlatMesh`) and edge indicators hinting at swipeable content.

```qml
Application {
    id: app
    centerColor: "#3498db"
    outerColor: "#1b3852"

    // Control edge indicator arrow visibility:
    topIndicVisible: true
    bottomIndicVisible: false
    leftIndicVisible: true
    rightIndicVisible: false
}
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `centerColor` | `color` | System theme | Center radial color of the background mesh. |
| `outerColor` | `color` | System theme | Outer rim color of the background mesh. |
| `topIndicVisible` | `bool` | `true` | Top edge indicator arrow visibility. |
| `bottomIndicVisible` | `bool` | `false` | Bottom edge indicator arrow visibility. |
| `leftIndicVisible` | `bool` | `true` | Left edge indicator arrow visibility. |
| `rightIndicVisible` | `bool` | `false` | Right edge indicator arrow visibility. |

#### `PageHeader`
Header banner for subpages and views.

```qml
PageHeader {
    id: header
    text: "Settings"
}
```

| Property | Type | Description |
| :--- | :--- | :--- |
| `text` | `string` | Header title string displayed in bold uppercase. |

#### `LayerStack`
Stack-based view navigation manager supporting push/pop page transitions and edge swipe-to-dismiss gestures.

```qml
LayerStack {
    id: stack
    firstPage: homePageComponent

    Component {
        id: homePageComponent
        Item {
            IconButton {
                iconName: "ios-arrow-forward"
                onClicked: stack.push(detailPageComponent)
            }
        }
    }

    Component {
        id: detailPageComponent
        Item {
            PageHeader { text: "Details" }
            IconButton {
                iconName: "ios-arrow-back"
                onClicked: stack.pop(stack.currentLayer)
            }
        }
    }
}
```

| Method / Property | Type | Description |
| :--- | :--- | :--- |
| `firstPage` | `Component` | Initial root page component. |
| `layers` | `list` | Active stack layers list. |
| `currentLayer` | `Item` | Currently active top-most page. |
| `push(component, params)` | Method | Instantiates and pushes a page with slide-in animation. |
| `pop(layer)` | Method | Removes and destroys the specified layer. |
| `popAnim()` | Method | Slides out the top layer with exit animation. |

---

### 4.2 Buttons & Interactive Controls

#### `IconButton`
A circular touch button displaying an Ionicons glyph with pressed visual feedback.

```qml
IconButton {
    iconName: "ios-play"
    iconColor: "#ffffff"
    pressedIconColor: "#3498db"
    onClicked: backend.startPlayback()
}
```

| Property / Signal | Type | Description |
| :--- | :--- | :--- |
| `iconName` | `string` | AsteroidOS icon identifier (e.g. `"ios-alarm-outline"`). |
| `iconColor` | `color` | Resting icon glyph color (default `#FFFFFFFF`). |
| `pressedIconColor` | `color` | Color while the button is pressed down. |
| `clicked()` | `signal` | Emitted when tapped. |

#### `Switch` & `LabeledSwitch`
Toggle switch and combined label + switch for boolean preferences.

```qml
LabeledSwitch {
    width: parent.width
    text: "Heart Rate Monitor"
    checked: backend.heartRateEnabled
    onCheckedChanged: backend.setHeartRate(checked)
}
```

| Property | Type | Description |
| :--- | :--- | :--- |
| `text` | `string` | Label text displayed on the left. |
| `checked` | `bool` | Boolean toggle state. |

#### `LabeledActionButton`
A clickable list row showing a label and an action icon.

```qml
LabeledActionButton {
    text: "Shutdown Device"
    icon: "ios-power-outline"
    onClicked: backend.confirmShutdown()
}
```

---

### 4.3 Lists & Selectors

#### `ListItem`
Standard list delegate displaying an icon and title text.

```qml
ListView {
    anchors.fill: parent
    model: backend.deviceListModel
    delegate: ListItem {
        width: parent.width
        title: model.deviceName
        iconName: model.connected ? "ios-bluetooth" : "ios-close"
        onClicked: backend.connectDevice(model.deviceId)
    }
}
```

#### `ListRow`
The foundational layout container for list rows, providing standardized padding (`actionSlotPadding`), font sizes, and action widget slot (`actionComponent`).

#### `IntSelector`
Pill-shaped numerical scrubber track with minus and plus buttons for setting numbers (volume, brightness, targets).

```qml
IntSelector {
    width: Dims.w(90)
    anchors.centerIn: parent
    min: 0
    max: 100
    stepSize: 5
    unitMarker: "%"
    value: backend.brightnessValue
    onValueChanged: backend.setBrightness(value)
}
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `min` | `int` | `0` | Minimum allowable value. |
| `max` | `int` | `100` | Maximum allowable value. |
| `stepSize` | `int` | `10` | Increment / decrement step. |
| `unitMarker` | `string` | `"%"` | Suffix string displayed after number. |
| `value` | `int` | `0` | Current selected value. |
| `valueLabelVisible`| `bool` | `true` | Show or hide central numeric label. |

#### `OptionCycler`
Tap-to-cycle row component that advances through a list of choices on each tap.

```qml
OptionCycler {
    width: parent.width
    text: "Display Theme"
    valueArray: ["Dark", "OLED Blue", "Emerald", "Sunset"]
    currentValue: backend.selectedTheme
    onValueChanged: (val) => backend.changeTheme(val)
}
```

#### `Spinner` & `CircularSpinner`
Wheel selection views. `CircularSpinner` wraps values vertically on a curved path, ideal for time pickers (hours, minutes).

```qml
CircularSpinner {
    id: hourSpinner
    width: Dims.w(45)
    height: parent.height
    model: 24
    onCurrentIndexChanged: backend.setHour(currentIndex)
}
```

---

### 4.4 Status & Feedback Components

#### `RemorseTimer`
Fullscreen countdown gauge for cancellable destructive actions (e.g. deleting files, resetting data). Allows the user to tap to cancel before `triggered()` fires.

```qml
RemorseTimer {
    id: remorse
    action: "Deleting workout log"
    cancelText: "Tap to Cancel"
    duration: 4000  // 4 seconds
    onTriggered: backend.deleteWorkout()
    onCancelled: console.log("Workout deletion cancelled")
}

// Trigger in response to user action:
remorse.visible = true
```

#### `ValueMeter`
Animated liquid wave gauge with floating particles, ideal for battery, fitness step goals, or liquid trackers.

```qml
ValueMeter {
    anchors.fill: parent
    valueLowerBound: 0
    valueUpperBound: 10000
    value: backend.stepCount
    particleDesign: "diamonds"  // "diamonds", "bubbles", "logos", "flashes"
    fillColor: Qt.rgba(0.2, 0.7, 0.9, 0.35)
}
```

#### `SegmentedArc`
Circular progress arc composed of rounded radial segments.

```qml
SegmentedArc {
    anchors.fill: parent
    inputValue: backend.batteryPercent  // 0 - 100
    segmentAmount: 10
    fgColor: "#2ecc71"
    bgColor: "#2c3e50"
}
```

#### `StatusPage`
Fullscreen state page displaying an icon and status message (e.g., "Connected", "No Notifications", "Update Complete").

```qml
StatusPage {
    text: "Device Paired"
    icon: "ios-checkmark-circle-outline"
    clickable: true
    onClicked: stack.pop(stack.currentLayer)
}
```

#### `Marquee`
Scrolling marquee text component for labels that exceed display dimensions.

```qml
Marquee {
    width: Dims.w(80)
    height: Dims.h(10)
    text: backend.currentTrackArtist + " - " + backend.currentTrackTitle
    speed: 1.2
}
```

---

### 4.5 Text Input & Gestures

#### `TextField` & `TextArea`
Wearable-optimized single-line and multi-line text input fields.

```qml
TextField {
    width: Dims.w(85)
    text: backend.userName
    onTextChanged: backend.updateUserName(text)
}
```

#### `BorderGestureArea`
Touch area detecting edge-in swipe gestures (`left`, `right`, `up`, `down`).

```qml
BorderGestureArea {
    anchors.fill: parent
    acceptsRight: true
    onGestureFinished: (gesture) => {
        if (gesture === "right") {
            backend.handleSwipeBack()
        }
    }
}
```

---

## 5. `org.asteroid.utils` Utility Module

The `org.asteroid.utils` QML module provides direct access to device hardware capabilities, system time, and Bluetooth connectivity.

### 5.1 `DeviceSpecs` (Singleton)

Import `org.asteroid.utils` to query hardware attributes:

```qml
import QtQuick
import org.asteroid.utils

Item {
    Component.onCompleted: {
        console.log("Model:", DeviceSpecs.machineName)
        console.log("Round Screen:", DeviceSpecs.hasRoundScreen)
        console.log("Flat Tire Height:", DeviceSpecs.flatTireHeight)
        console.log("Has Speaker:", DeviceSpecs.hasSpeaker)
        console.log("Has WLAN:", DeviceSpecs.hasWlan)
        console.log("OLED Burn-in Protection:", DeviceSpecs.needsBurnInProtection)
    }
}
```

| Property | Type | Description |
| :--- | :--- | :--- |
| `hasRoundScreen` | `bool` | `true` if watch has a circular screen. |
| `flatTireHeight` | `int` | Pixel height of bottom dead zone on flat-tire screens (e.g. Moto 360). |
| `borderGestureWidth` | `double` | Normalized edge gesture activation threshold width. |
| `needsBurnInProtection` | `bool` | `true` for OLED displays requiring periodic UI shifting. |
| `hasWlan` | `bool` | `true` if hardware Wi-Fi chip is present. |
| `hasSpeaker` | `bool` | `true` if internal speaker hardware is present. |
| `machineName` | `string` | Board codename (e.g. `"dory"`, `"bass"`, `"lenok"`). |
| `hostname` | `string` | System hostname. |
| `buildID` | `string` | AsteroidOS software build identifier. |

### 5.2 `WallClock`

Battery-optimized clock object synchronized with the system timer, emitting `timeChanged` exactly on second, minute, or day boundaries.

```qml
import QtQuick
import org.asteroid.utils

Item {
    WallClock {
        id: clock
        enabled: true
        updateFrequency: WallClock.Minute  // WallClock.Second, WallClock.Minute, WallClock.Day
        onTimeChanged: timeLabel.text = Qt.formatTime(clock.time, "hh:mm")
    }

    Label {
        id: timeLabel
        anchors.centerIn: parent
        font.pixelSize: Dims.l(16)
        text: Qt.formatTime(clock.time, "hh:mm")
    }
}
```

### 5.3 `BluetoothStatus`

Monitors Bluetooth adapter and companion phone connection status over DBus:

```qml
import QtQuick
import org.asteroid.utils

Item {
    BluetoothStatus {
        id: bt
        onConnectedChanged: console.log("BT Connected:", connected)
    }

    IconButton {
        iconName: "ios-bluetooth"
        iconColor: bt.connected ? "#3498db" : "#7f8c8d"
    }
}
```

| Property | Type | Description |
| :--- | :--- | :--- |
| `powered` | `bool` | Whether Bluetooth radio is turned on. |
| `connected` | `bool` | Whether watch is actively connected to a phone. |

### 5.4 `FileInfo` (Singleton)

Check file existence on the local filesystem directly from QML:

```qml
import org.asteroid.utils

if (FileInfo.exists("/usr/share/sounds/alarm.wav")) {
    // File is present
}
```

---

## 6. `org.asteroid.settings` Module

Provides access to system configuration settings:

| Component | Description |
| :--- | :--- |
| `DisplaySettings` | Screen brightness, display timeout, and ambient mode settings. |
| `DateTimeSettings` | 12/24-hour clock formatting and timezone settings. |
| `AboutSettings` | Device storage statistics, kernel version, and AsteroidOS release info. |
| `LanguageModel` | List model of supported AsteroidOS system languages. |

---

## 7. AsteroidOS Icons (`asteroidos.icons`)

AsteroidOS uses Ionicons-based glyphs. In QML, pass icon names directly to `IconButton`, `ListItem`, `LabeledActionButton`, or `StatusPage`:

```qml
IconButton {
    iconName: "ios-pulse-outline"
}
```

In Python code (e.g. app metadata and menus), import the SDK's icon constants:

```python
import asteroidos.icons as icons

app_icon = icons.IOS_PULSE_OUTLINE
alarm_icon = icons.IOS_ALARM_OUTLINE
stopwatch_icon = icons.IOS_STOPWATCH_OUTLINE
settings_icon = icons.IOS_SETTINGS_OUTLINE
battery_icon = icons.IOS_BATTERY_CHARGING
bluetooth_icon = icons.IOS_BLUETOOTH
```

Commonly used icons:
- `"ios-pulse-outline"`: Heart rate / fitness
- `"ios-play"`, `"ios-pause"`, `"ios-skipforward"`: Media controls
- `"ios-add"`, `"ios-minus-empty"`, `"ios-refresh-empty"`: Counters & adjustment
- `"ios-alarm-outline"`, `"ios-timer-outline"`, `"ios-stopwatch-outline"`: Clocks & timers
- `"ios-sunny-outline"`, `"ios-moon-outline"`, `"ios-partlysunny-outline"`: Weather & theme
- `"ios-settings-outline"`, `"ios-information-outline"`: Config & about
- `"ios-power-outline"`, `"ios-sync"`: Power & reload

---

## 8. Complete Real-World Example: Fitness Tracker

Here is a full Python + QML application demonstrating `Application`, `Dims`, `LayerStack`, `IntSelector`, `ValueMeter`, `LabeledSwitch`, and two-way PySide6 data binding:

### `main.py`
```python
import os
import sys

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView


class FitnessBackend(QObject):
    stepsChanged = Signal(int)
    targetChanged = Signal(int)
    trackingChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._steps = 4250
        self._target = 10000
        self._tracking = True

    @Property(int, notify=stepsChanged)
    def steps(self) -> int:
        return self._steps

    @Property(int, notify=targetChanged)
    def target(self) -> int:
        return self._target

    @Property(bool, notify=trackingChanged)
    def tracking(self) -> bool:
        return self._tracking

    @Slot(int)
    def setTarget(self, new_target: int):
        if self._target != new_target:
            self._target = new_target
            self.targetChanged.emit(self._target)

    @Slot(bool)
    def setTracking(self, enabled: bool):
        if self._tracking != enabled:
            self._tracking = enabled
            self.trackingChanged.emit(self._tracking)

    @Slot()
    def addSampleSteps(self):
        self._steps = min(self._steps + 250, self._target)
        self.stepsChanged.emit(self._steps)


def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("asteroid-fitness")

    view = QQuickView()
    backend = FitnessBackend()
    view.rootContext().setContextProperty("fitness", backend)

    qml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.qml")
    view.setSource(QUrl.fromLocalFile(qml_file))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.showFullScreen()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

### `main.qml`
```qml
import QtQuick
import org.asteroid.controls
import org.asteroid.utils

Application {
    id: app
    centerColor: "#16a085"
    outerColor: "#0e6251"

    LayerStack {
        id: stack
        firstPage: trackerPage

        Component {
            id: trackerPage
            Item {
                ValueMeter {
                    anchors.fill: parent
                    valueLowerBound: 0
                    valueUpperBound: fitness.target
                    value: fitness.steps
                    fillColor: Qt.rgba(0.1, 0.8, 0.6, 0.3)
                    particleDesign: "bubbles"
                }

                Column {
                    anchors.centerIn: parent
                    spacing: Dims.h(2)

                    Label {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "STEPS"
                        font.pixelSize: Dims.l(6)
                        color: "#a3e4d7"
                    }

                    Label {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: fitness.steps.toString()
                        font.pixelSize: Dims.l(14)
                        font.bold: true
                    }

                    Label {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Goal: " + fitness.target
                        font.pixelSize: Dims.l(5)
                        color: "#d1f2eb"
                    }
                }

                Row {
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: Dims.h(10)
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Dims.w(8)

                    IconButton {
                        iconName: "ios-add"
                        onClicked: fitness.addSampleSteps()
                    }

                    IconButton {
                        iconName: "ios-settings-outline"
                        onClicked: stack.push(settingsPage)
                    }
                }
            }
        }

        Component {
            id: settingsPage
            Item {
                PageHeader {
                    id: header
                    text: "Goal Settings"
                }

                Column {
                    anchors.top: header.bottom
                    anchors.topMargin: Dims.h(4)
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Dims.w(90)
                    spacing: Dims.h(4)

                    LabeledSwitch {
                        width: parent.width
                        text: "Live Tracking"
                        checked: fitness.tracking
                        onCheckedChanged: fitness.setTracking(checked)
                    }

                    Label {
                        text: "Daily Step Target"
                        font.pixelSize: Dims.l(6)
                    }

                    IntSelector {
                        width: parent.width
                        min: 2000
                        max: 20000
                        stepSize: 1000
                        unitMarker: " steps"
                        value: fitness.target
                        onValueChanged: fitness.setTarget(value)
                    }
                }
            }
        }
    }
}
```

---

## 9. Best Practices for AsteroidOS Python Apps

1. **Keep Python CPU Work Light**: Smartwatch CPUs are low-power ARM Cortex-A7 cores. Perform heavy computation or network fetching asynchronously (`QThread` or `QThreadPool`) to prevent stuttering in the Wayland compositor.
2. **Respect Ambient & Burn-In Modes**: On OLED displays, `DeviceSpecs.needsBurnInProtection` is `true`. Avoid static high-contrast white pixels that stay permanently in one position.
3. **Always Use `Dims`**: Hardcoded pixel sizes (like `width: 250`) will break when moving between a 320×320 square display and a 454×454 round watch.
4. **Edge Gestures for Back**: Use `LayerStack` for multi-screen navigation so users can swipe in from the left/right screen edge to go back, matching the native AsteroidOS gesture language.
5. **Clean PySide6 Object Lifetimes**: Ensure Python objects exposed to `setContextProperty()` persist throughout the application lifecycle (e.g. keep references on the main application object).


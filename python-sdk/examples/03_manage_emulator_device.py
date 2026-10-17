#!/usr/bin/env python3
"""
Example 3: Controlling Emulator and Deploying Applications.

Demonstrates programmatic control of the AsteroidOS emulator,
checking connection, taking screenshots, and inspecting system information.
"""

from asteroidos import Emulator, Device, Target

def main():
    print("=== AsteroidOS Emulator and Device Management ===")

    # 1. Check emulator status
    status = Emulator.status()
    print(f"Emulator running: {status['running']}")

    if not status["running"]:
        print("Starting emulator in background...")
        Emulator.start(daemon=True)
        print("Waiting for emulator to finish booting...")
        ready = Emulator.wait_ready(timeout=60)
        print(f"Emulator ready: {ready}")

    # 2. Connect to device
    device = Device.for_target(Target.EMULATOR)
    if device.is_reachable():
        print("Device is reachable via SSH!")

        # 3. Read OS info
        os_info = device.get_os_release()
        print(f"AsteroidOS Version: {os_info.get('PRETTY_NAME', 'unknown')}")

        # 4. Take a screenshot
        screenshot_file = device.screenshot("emulator_screenshot.png")
        print(f"Captured screenshot: {screenshot_file}")
    else:
        print("Device not currently reachable over SSH.")

if __name__ == "__main__":
    main()


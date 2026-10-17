"""
AsteroidOS Emulator Controller.

Allows starting, stopping, inspecting, and waiting for the AsteroidOS QEMU emulator
from Python.
"""

from __future__ import annotations

import os
from pathlib import Path
import signal
import socket
import subprocess
import time
from typing import Dict, Optional

from .builder import Builder
from .device import Device


class EmulatorError(Exception):
    """Raised when an emulator operation fails."""
    pass


class Emulator:
    """Manages the AsteroidOS QEMU Emulator."""

    DEFAULT_PORT = 2222

    @classmethod
    def find_script(cls) -> Path:
        devkit_root = Builder.find_devkit_root()
        if not devkit_root:
            raise EmulatorError("Could not locate DevKit root containing scripts/run-emulator.sh")
        script = devkit_root / "scripts" / "run-emulator.sh"
        if not script.exists():
            raise EmulatorError(f"Emulator script not found at {script}")
        return script

    @classmethod
    def get_qemu_pids(cls) -> list[int]:
        """Finds any running AsteroidOS QEMU processes."""
        try:
            output = subprocess.check_output(["pgrep", "-f", "bzImage-emulator.bin"], text=True)
            return [int(pid) for pid in output.strip().splitlines() if pid]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    @classmethod
    def is_running(cls) -> bool:
        """Returns True if QEMU emulator process is running."""
        return len(cls.get_qemu_pids()) > 0

    @classmethod
    def is_port_open(cls, port: int = DEFAULT_PORT, host: str = "127.0.0.1") -> bool:
        """Checks if port (SSH) is accepting connections."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            return s.connect_ex((host, port)) == 0

    @classmethod
    def start(
        cls,
        daemon: bool = True,
        acceleration: bool = True,
        display: Optional[str] = None,
    ) -> Optional[subprocess.Popen]:
        """
        Starts the AsteroidOS emulator.

        Args:
            daemon: If True, runs in the background.
            acceleration: If False, passes --no-accel to run without KVM.
            display: "gtk", "sdl", or None.

        Returns:
            subprocess.Popen object if started in daemon mode.
        """
        if cls.is_running():
            print("[INFO] AsteroidOS emulator is already running.")
            return None

        script = cls.find_script()
        devkit_root = script.parent.parent

        cmd = [str(script)]
        if not acceleration:
            cmd.append("--no-accel")
        if display:
            cmd.extend(["--display", display])

        if daemon:
            log_file = devkit_root / "emulator" / "emulator.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            f = open(log_file, "a")
            proc = subprocess.Popen(
                cmd,
                cwd=str(devkit_root),
                stdout=f,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            return proc
        else:
            subprocess.run(cmd, cwd=str(devkit_root))
            return None

    @classmethod
    def stop(cls, force: bool = False) -> bool:
        """Stops any running AsteroidOS emulator processes."""
        pids = cls.get_qemu_pids()
        if not pids:
            return False

        sig = signal.SIGKILL if force else signal.SIGTERM
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        return True

    @classmethod
    def wait_ready(cls, timeout: int = 60, poll_interval: float = 1.0) -> bool:
        """Waits until the emulator has booted and SSH connection is established."""
        start_time = time.time()
        dev = Device.for_target("emulator")

        while time.time() - start_time < timeout:
            if cls.is_port_open(dev.port, dev.host):
                if dev.is_reachable():
                    return True
            time.sleep(poll_interval)
        return False

    @classmethod
    def status(cls) -> Dict[str, object]:
        """Returns the current state of the emulator."""
        pids = cls.get_qemu_pids()
        running = len(pids) > 0
        ssh_ready = cls.is_port_open(cls.DEFAULT_PORT) if running else False
        return {
            "running": running,
            "pids": pids,
            "ssh_ready": ssh_ready,
            "port": cls.DEFAULT_PORT,
        }


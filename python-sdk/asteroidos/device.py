"""
AsteroidOS Device & SSH Abstraction.

Provides connection, package installation, execution, screenshotting,
and diagnostics for AsteroidOS emulator and physical watches.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Union

if TYPE_CHECKING:
    from .app import Target


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class DeviceError(Exception):
    """Raised on device connection or command failure."""
    pass


class Device:
    """Represents a connection to an AsteroidOS device (emulator or physical watch)."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 2222,
        user: str = "ceres",
        timeout: int = 10,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.timeout = timeout

    @classmethod
    def for_target(
        cls,
        target: Union[Target, str],
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
    ) -> Device:
        """Creates a Device instance configured with default settings for the target."""
        target_name = target.value if hasattr(target, "value") else str(target)

        if target_name == "watch":
            final_host = host or "192.168.2.15"
            final_port = port or 22
            final_user = user or "root"
        else:
            final_host = host or "localhost"
            final_port = port or 2222
            final_user = user or "ceres"

        return cls(host=final_host, port=final_port, user=final_user)

    def _ssh_cmd_base(self) -> List[str]:
        return [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-o", f"ConnectTimeout={self.timeout}",
            "-p", str(self.port),
            f"{self.user}@{self.host}",
        ]

    def _scp_cmd_base(self) -> List[str]:
        return [
            "scp",
            "-O",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-o", f"ConnectTimeout={self.timeout}",
            "-P", str(self.port),
        ]

    def is_reachable(self) -> bool:
        """Checks if SSH connection to the device is responding."""
        try:
            res = self.run("echo ok", timeout=3)
            return res.ok and "ok" in res.stdout
        except Exception:
            return False

    def run(self, command: str, sudo: bool = False, timeout: Optional[int] = None) -> CommandResult:
        """Runs a shell command on the remote AsteroidOS device."""
        if sudo and self.user != "root":
            command = f"sudo {command}"

        cmd = self._ssh_cmd_base() + [command]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )
            return CommandResult(
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(exit_code=124, stdout="", stderr=f"Timeout expired: {exc}")
        except Exception as exc:
            return CommandResult(exit_code=1, stdout="", stderr=str(exc))

    def upload(self, local_path: Union[str, Path], remote_path: str) -> bool:
        """Copies a local file to remote device over SCP."""
        local = Path(local_path)
        if not local.exists():
            raise FileNotFoundError(f"Local file does not exist: {local}")

        cmd = self._scp_cmd_base() + [str(local), f"{self.user}@{self.host}:{remote_path}"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout * 3)
        return res.returncode == 0

    def download(self, remote_path: str, local_path: Union[str, Path]) -> bool:
        """Copies a file from remote device to local over SCP."""
        local = Path(local_path)
        local.parent.mkdir(parents=True, exist_ok=True)

        cmd = self._scp_cmd_base() + [f"{self.user}@{self.host}:{remote_path}", str(local)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout * 3)
        return res.returncode == 0

    def install_ipk(self, ipk_path: Union[str, Path], force: bool = True) -> bool:
        """Uploads and installs an .ipk package using opkg."""
        ipk = Path(ipk_path)
        if not ipk.exists():
            raise FileNotFoundError(f"IPK package not found: {ipk}")

        # Pre-clean any stale files and vacuum logs to avoid ENOSPC
        self.run(f"rm -f \"{ipk.name}\" \"/dev/shm/{ipk.name}\" \"/tmp/{ipk.name}\"")
        self.run("journalctl --vacuum-time=1s", sudo=True)
        self.run("rm -rf /var/lib/opkg/lists/*", sudo=True)

        # Try uploading to /dev/shm first (RAM tmpfs avoids consuming rootfs space), then home, then /tmp
        remote_dest = f"/dev/shm/{ipk.name}"
        if not self.upload(ipk, remote_dest):
            remote_dest = ipk.name
            if not self.upload(ipk, remote_dest):
                remote_dest = f"/tmp/{ipk.name}"
                if not self.upload(ipk, remote_dest):
                    raise DeviceError(f"Failed to upload package {ipk.name} to {self.host}:{remote_dest}")

        force_flags = "--force-reinstall --force-overwrite --force-depends" if force else ""
        install_target = remote_dest if remote_dest.startswith("/") else f"./{remote_dest}"
        cmd = f"opkg install {force_flags} {install_target} && rm -f {install_target} /dev/shm/{ipk.name} /tmp/{ipk.name} {ipk.name}"
        res = self.run(cmd, sudo=True)
        if not res.ok:
            raise DeviceError(f"Package installation failed: {res.stderr}\n{res.stdout}")

        return True

    def uninstall(self, package_name: str) -> bool:
        """Uninstalls a package via opkg."""
        res = self.run(f"opkg remove {package_name}", sudo=True)
        return res.ok

    def launch_app(self, app_name: str) -> bool:
        """Launches an application binary or script on the device."""
        # Run in background via nohup
        res = self.run(f"nohup {app_name} >/dev/null 2>&1 &")
        return res.ok

    def screenshot(self, save_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Takes a screenshot of the AsteroidOS screen using `screenshottool` and saves locally.

        Returns:
            Local path to screenshot PNG file.
        """
        remote_png = f"/tmp/screenshot_{int(time.time())}.png"
        res = self.run(f"screenshottool {remote_png}")
        if not res.ok:
            raise DeviceError(f"Failed to capture screenshot: {res.stderr}")

        if save_path is None:
            save_path = Path.cwd() / "screenshot.png"
        else:
            save_path = Path(save_path)

        success = self.download(remote_png, save_path)
        self.run(f"rm -f {remote_png}")

        if not success or not save_path.exists():
            raise DeviceError(f"Failed to retrieve screenshot from device.")

        return save_path

    def get_os_release(self) -> Dict[str, str]:
        """Reads /etc/os-release or /usr/lib/os-release on the device."""
        res = self.run("cat /etc/os-release 2>/dev/null || cat /usr/lib/os-release 2>/dev/null")
        info = {}
        if res.ok:
            for line in res.stdout.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    info[k.strip()] = v.strip().strip('"')
        return info


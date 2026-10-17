"""
AsteroidOS Python SDK.

A developer kit for creating, building, packaging, and deploying
applications for the AsteroidOS smartwatch platform from Python.
"""

from .app import App, AppMetadata, AppType, Target
from .builder import Builder, BuildError
from .device import CommandResult, Device, DeviceError
from .emulator import Emulator, EmulatorError
from .icons import ALL_ICONS
from .packager import ArArchive, IpkPackager
from .templates import TemplateManager

__version__ = "0.1.0"

__all__ = [
    "App",
    "AppMetadata",
    "AppType",
    "Target",
    "Builder",
    "BuildError",
    "Device",
    "DeviceError",
    "CommandResult",
    "Emulator",
    "EmulatorError",
    "IpkPackager",
    "ArArchive",
    "TemplateManager",
    "ALL_ICONS",
    "__version__",
]


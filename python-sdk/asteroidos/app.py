"""
AsteroidOS Application Abstraction.

Allows defining, configuring, building, packaging, and deploying
AsteroidOS applications directly from Python code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional, Union

from .icons import IOS_PULSE_OUTLINE
from .templates import TemplateManager, render_template_string


class Target(str, Enum):
    """Target build platform for AsteroidOS."""
    EMULATOR = "emulator"
    ARM = "arm"
    WATCH = "watch"
    ALL = "all"

    @property
    def arch(self) -> str:
        if self == Target.EMULATOR:
            return "core2-32"
        elif self in (Target.ARM, Target.WATCH):
            return "armv7vehf-neon"
        return "all"


class AppType(str, Enum):
    """Application technology stack."""
    NATIVE_QML = "qml_cpp"
    PYTHON_QML = "python"


@dataclass
class AppMetadata:
    """Metadata describing an AsteroidOS application."""
    name: str
    title: str = ""
    version: str = "1.0.0"
    description: str = "An application for AsteroidOS"
    author: str = "AsteroidOS Developer <developer@example.org>"
    icon: str = IOS_PULSE_OUTLINE
    center_color: str = "#b04d1c"
    outer_color: str = "#421c0a"
    app_type: AppType = AppType.NATIVE_QML
    dependencies: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Sanitize app name (must be valid package identifier: lowercase letters, digits, dashes)
        sanitized = self.name.lower().replace("_", "-")
        self.name = re.sub(r"[^a-z0-9+-]", "-", sanitized).strip("-")
        if not self.title:
            # Generate title from name (e.g. asteroid-stopwatch -> Stopwatch)
            cleaned = self.name.replace("asteroid-", "").replace("-", " ")
            self.title = cleaned.title()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "icon": self.icon,
            "center_color": self.center_color,
            "outer_color": self.outer_color,
            "app_type": self.app_type.value if isinstance(self.app_type, AppType) else self.app_type,
            "dependencies": list(self.dependencies),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppMetadata:
        app_type_val = data.get("app_type", "qml_cpp")
        try:
            app_type = AppType(app_type_val)
        except ValueError:
            app_type = AppType.NATIVE_QML

        return cls(
            name=data["name"],
            title=data.get("title", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", "AsteroidOS Developer"),
            icon=data.get("icon", IOS_PULSE_OUTLINE),
            center_color=data.get("center_color", "#b04d1c"),
            outer_color=data.get("outer_color", "#421c0a"),
            app_type=app_type,
            dependencies=data.get("dependencies", []),
        )


class App:
    """
    Main AsteroidOS Application builder and manager.

    Example:
        >>> from asteroidos import App, Target
        >>> app = App("asteroid-counter", title="Step Counter")
        >>> app.set_main_qml(...)
        >>> package = app.build(Target.EMULATOR)
    """

    def __init__(
        self,
        name: str,
        title: str = "",
        version: str = "1.0.0",
        description: str = "An application for AsteroidOS",
        author: str = "AsteroidOS Developer <developer@example.org>",
        icon: str = IOS_PULSE_OUTLINE,
        center_color: str = "#b04d1c",
        outer_color: str = "#421c0a",
        app_type: Union[AppType, str] = AppType.NATIVE_QML,
        dependencies: Optional[List[str]] = None,
        project_dir: Optional[Union[str, Path]] = None,
    ):
        if isinstance(app_type, str):
            try:
                app_type = AppType(app_type)
            except ValueError:
                app_type = AppType.NATIVE_QML

        self.metadata = AppMetadata(
            name=name,
            title=title,
            version=version,
            description=description,
            author=author,
            icon=icon,
            center_color=center_color,
            outer_color=outer_color,
            app_type=app_type,
            dependencies=dependencies or [],
        )

        self.project_dir = Path(project_dir) if project_dir else None
        self._custom_files: Dict[str, Union[str, bytes]] = {}
        self._custom_assets: List[Tuple[Path, str]] = []

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def title(self) -> str:
        return self.metadata.title

    @property
    def version(self) -> str:
        return self.metadata.version

    @property
    def app_type(self) -> AppType:
        return self.metadata.app_type

    def set_main_qml(self, content: str) -> App:
        """Sets the main QML user interface content."""
        if self.metadata.app_type == AppType.NATIVE_QML:
            self._custom_files["src/main.qml"] = content
        else:
            self._custom_files["main.qml"] = content
        return self

    def set_main_py(self, content: str) -> App:
        """Sets the main Python entry point (for Python apps)."""
        self._custom_files["main.py"] = content
        return self

    def add_file(self, relative_path: str, content: Union[str, bytes]) -> App:
        """Adds a custom file into the application project."""
        self._custom_files[relative_path.lstrip("/")] = content
        return self

    def add_asset(self, source_path: Union[str, Path], destination_relative_path: str) -> App:
        """Adds an external asset file (image, sound, data) to the app."""
        src = Path(source_path)
        if not src.exists():
            raise FileNotFoundError(f"Asset file '{src}' does not exist.")
        self._custom_assets.append((src, destination_relative_path.lstrip("/")))
        return self

    def get_template_context(self) -> Dict[str, Any]:
        """Returns the dictionary context passed to template renderers."""
        ctx = self.metadata.to_dict()
        ctx["app_name"] = self.metadata.name
        return ctx

    def generate_project(self, destination_dir: Union[str, Path], overwrite: bool = False) -> Path:
        """
        Generates the full project filesystem directory with all source files.

        Args:
            destination_dir: Directory where the project should be placed.
            overwrite: If True, existing files will be overwritten.

        Returns:
            Path to the project directory.
        """
        dest = Path(destination_dir)
        if dest.exists() and not overwrite and any(dest.iterdir()):
            raise FileExistsError(f"Directory '{dest}' already exists and is not empty. Use overwrite=True.")

        dest.mkdir(parents=True, exist_ok=True)
        self.project_dir = dest

        # 1. Render base template
        template_name = self.metadata.app_type.value
        context = self.get_template_context()
        TemplateManager.render_template(template_name, context, dest)

        # 2. Write custom files
        for rel_path, content in self._custom_files.items():
            target_path = dest / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, str):
                target_path.write_text(content, encoding="utf-8")
            else:
                target_path.write_bytes(content)

        # 3. Copy custom assets
        for src_path, rel_path in self._custom_assets:
            target_path = dest / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, target_path)

        # 4. Save metadata manifest
        manifest_file = dest / "asteroid.json"
        manifest_file.write_text(json.dumps(self.metadata.to_dict(), indent=2), encoding="utf-8")

        return dest

    def build(
        self,
        target: Union[Target, str] = Target.EMULATOR,
        build_dir: Optional[Union[str, Path]] = None,
        clean: bool = False,
        package: bool = True,
        standalone: bool = True,
    ) -> Path:
        """
        Builds the application and optionally generates an .ipk package.

        Returns:
            Path to the generated .ipk file (or build output dir).
        """
        from .builder import Builder

        if isinstance(target, str):
            target = Target(target)

        # If project hasn't been written to disk yet, write to a temporary or default project dir
        if not self.project_dir:
            temp_dir = Path("/tmp") / f"asteroid-build-{self.name}"
            self.generate_project(temp_dir, overwrite=True)

        return Builder.build(
            app=self,
            target=target,
            build_dir=Path(build_dir) if build_dir else None,
            clean=clean,
            package=package,
            standalone=standalone,
        )

    def package(
        self,
        target: Union[Target, str] = Target.EMULATOR,
        output_file: Optional[Union[str, Path]] = None,
        standalone: bool = True,
    ) -> Path:
        """
        Directly packages the application into an .ipk file without requiring full CMake compilation
        (ideal for Python/QML applications, or assets).

        Args:
            target: Target architecture (Target.EMULATOR, Target.ARM, or Target.ALL).
            output_file: Optional destination .ipk file.
            standalone: If True, bundles a self-contained Python runtime (AppImage-style).

        Returns:
            Path to generated .ipk package.
        """
        from .builder import Builder

        if isinstance(target, str):
            target = Target(target)

        if not self.project_dir:
            temp_dir = Path("/tmp") / f"asteroid-pkg-{self.name}"
            self.generate_project(temp_dir, overwrite=True)

        return Builder.package_ipk(
            app=self,
            target=target,
            output_file=Path(output_file) if output_file else None,
            standalone=standalone,
        )

    def deploy(
        self,
        target: Union[Target, str] = Target.EMULATOR,
        ipk_path: Optional[Union[str, Path]] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> bool:
        """
        Deploys the compiled application to emulator or physical watch.

        Returns:
            True if deployment succeeded.
        """
        from .device import Device

        if isinstance(target, str):
            target = Target(target)

        if ipk_path is None:
            ipk_path = self.build(target=target, package=True)

        device = Device.for_target(target, host=host, port=port)
        return device.install_ipk(ipk_path)

    @classmethod
    def load(cls, project_dir: Union[str, Path]) -> App:
        """Loads an existing AsteroidOS application project from disk."""
        project_dir = Path(project_dir)
        if not project_dir.is_dir():
            raise NotADirectoryError(f"'{project_dir}' is not a directory.")

        manifest_path = project_dir / "asteroid.json"
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            meta = AppMetadata.from_dict(data)
            app = cls(
                name=meta.name,
                title=meta.title,
                version=meta.version,
                description=meta.description,
                author=meta.author,
                icon=meta.icon,
                center_color=meta.center_color,
                outer_color=meta.outer_color,
                app_type=meta.app_type,
                dependencies=meta.dependencies,
                project_dir=project_dir,
            )
            return app

        # Infer from directory contents
        name = project_dir.name
        is_python = (project_dir / "main.py").exists()
        app_type = AppType.PYTHON_QML if is_python else AppType.NATIVE_QML

        # Check desktop template if present
        desktop_file = None
        for f in project_dir.glob("*.desktop*"):
            desktop_file = f
            break

        icon = IOS_PULSE_OUTLINE
        center_color = "#b04d1c"
        outer_color = "#421c0a"
        if desktop_file and desktop_file.exists():
            for line in desktop_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("Icon="):
                    icon = line.split("=", 1)[1].strip()
                elif line.startswith("X-Asteroid-Center-Color="):
                    center_color = line.split("=", 1)[1].strip()
                elif line.startswith("X-Asteroid-Outer-Color="):
                    outer_color = line.split("=", 1)[1].strip()

        return cls(
            name=name,
            icon=icon,
            center_color=center_color,
            outer_color=outer_color,
            app_type=app_type,
            project_dir=project_dir,
        )

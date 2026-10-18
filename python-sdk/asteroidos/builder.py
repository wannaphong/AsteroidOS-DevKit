"""
AsteroidOS Application Builder.

Handles compiling native C++/Qt6 projects and packaging Python/QML applications
into standard AsteroidOS .ipk packages.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from .packager import IpkPackager

if TYPE_CHECKING:
    from .app import App, Target


class BuildError(Exception):
    """Raised when an application build or packaging step fails."""
    pass


class Builder:
    """Coordinates application compilation and package generation."""

    @classmethod
    def find_devkit_root(cls, start_path: Optional[Path] = None) -> Optional[Path]:
        """Finds the AsteroidOS DevKit root directory."""
        # 1. Environment variable override
        env_root = os.environ.get("ASTEROID_DEVKIT_ROOT") or os.environ.get("ASTEROIDOS_DIR")
        if env_root and Path(env_root).exists():
            return Path(env_root).resolve()

        # 2. Location relative to this package file (python-sdk/asteroidos/builder.py -> devkit root)
        package_root = Path(__file__).resolve().parent.parent.parent
        if (package_root / "scripts" / "build-app.sh").exists() or (package_root / "env-emulator.sh").exists():
            return package_root

        # 3. Traversal from CWD
        candidates = [Path.cwd()]
        if start_path:
            candidates.append(Path(start_path).resolve())

        for base in candidates:
            for p in [base] + list(base.parents):
                if (p / "scripts" / "build-app.sh").exists() or (p / "env-emulator.sh").exists():
                    return p

        return None

    @classmethod
    def build_native(
        cls,
        app: App,
        target: Target,
        build_dir: Optional[Path] = None,
        clean: bool = False,
        package: bool = True,
    ) -> Path:
        """
        Compiles a native C++/Qt6 AsteroidOS application using the DevKit SDK environment.

        Returns:
            Path to the generated .ipk file (or build directory if package=False).
        """
        if not app.project_dir or not app.project_dir.exists():
            raise BuildError(f"Application project directory does not exist: {app.project_dir}")

        if not (app.project_dir / "CMakeLists.txt").exists():
            raise BuildError(f"CMakeLists.txt not found in {app.project_dir}")

        devkit_root = cls.find_devkit_root(app.project_dir)
        if not devkit_root:
            raise BuildError(
                "Could not locate AsteroidOS DevKit root directory (containing scripts/build-app.sh or env-emulator.sh)."
            )

        build_app_script = devkit_root / "scripts" / "build-app.sh"
        if not build_app_script.exists():
            raise BuildError(f"Build script not found: {build_app_script}")

        target_name = target.value if hasattr(target, "value") else str(target)
        if target_name not in ("emulator", "arm"):
            target_name = "emulator"

        out_build_dir = build_dir or (app.project_dir / f"build-{target_name}")

        cmd = [
            str(build_app_script),
            str(app.project_dir),
            "--target",
            target_name,
            "--build-dir",
            str(out_build_dir),
        ]
        if clean:
            cmd.append("--clean")
        if not package:
            cmd.append("--no-package")

        result = subprocess.run(cmd, cwd=str(devkit_root), capture_output=True, text=True)
        if result.returncode != 0:
            raise BuildError(
                f"Failed to build native app '{app.name}' for {target_name}:\n{result.stderr}\n{result.stdout}"
            )

        if package:
            # Find the created .ipk file in build_dir
            ipk_candidates = list(out_build_dir.glob("*.ipk"))
            if not ipk_candidates:
                raise BuildError(f"Build succeeded but no .ipk package found in {out_build_dir}")
            return ipk_candidates[0]

        return out_build_dir

    @classmethod
    def find_target_sysroot(cls, target: Target, devkit_root: Optional[Path] = None) -> Optional[Path]:
        """Finds sysroot directory for target architecture in sdk/sysroots/."""
        root = devkit_root or cls.find_devkit_root()
        if not root:
            return None
        sdk_sysroots = root / "sdk" / "sysroots"
        if not sdk_sysroots.exists():
            return None

        target_name = target.value if hasattr(target, "value") else str(target)
        if target_name in ("all", "allarch"):
            return None
        elif target_name in ("arm", "watch"):
            candidates = list(sdk_sysroots.glob("armv7*"))
        else:
            candidates = list(sdk_sysroots.glob("core2-32*"))

        return candidates[0] if candidates else None

    @classmethod
    def find_sdk_env_file(cls, target: Target, devkit_root: Optional[Path] = None) -> Optional[Path]:
        """Finds the AsteroidOS SDK environment setup script for target architecture."""
        root = devkit_root or cls.find_devkit_root()
        if not root:
            return None
        sdk_dir = root / "sdk"
        if not sdk_dir.exists():
            return None

        target_name = target.value if hasattr(target, "value") else str(target)
        if target_name in ("arm", "watch"):
            candidates = list(sdk_dir.glob("environment-setup-*arm*"))
        else:
            candidates = list(sdk_dir.glob("environment-setup-*core2-32*"))

        if not candidates:
            # Fallback to any environment setup script in sdk/
            candidates = list(sdk_dir.glob("environment-setup-*"))

        return candidates[0] if candidates else None

    @classmethod
    def setup_target_python_cross_env(
        cls,
        target: Target,
        devkit_root: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Configures and prepares cross-compilation environment variables for compiling
        Python C/C++ extensions (such as NumPy) targeting the device architecture.
        """
        root = devkit_root or cls.find_devkit_root()
        if not root:
            raise BuildError("Could not locate AsteroidOS DevKit root directory.")

        target_sysroot = cls.find_target_sysroot(target, root)
        if not target_sysroot:
            raise BuildError(f"Target sysroot not found for target '{target}' in {root / 'sdk' / 'sysroots'}")

        native_sysroot = root / "sdk" / "sysroots" / "x86_64-oesdk-linux"
        if not native_sysroot.exists():
            raise BuildError(f"Native SDK sysroot not found at {native_sysroot}")

        sdk_env_file = cls.find_sdk_env_file(target, root)
        if not sdk_env_file or not sdk_env_file.exists():
            raise BuildError(f"SDK environment-setup script not found in {root / 'sdk'}")

        # Detect Python version in target sysroot
        py_inc_dirs = list((target_sysroot / "usr" / "include").glob("python3.*"))
        if not py_inc_dirs:
            raise BuildError(f"No Python 3 headers found in {target_sysroot / 'usr' / 'include'}")
        py_version_dir = py_inc_dirs[0].name  # e.g. python3.13

        # Ensure pip is available in the SDK native Python environment
        native_python = native_sysroot / "usr" / "bin" / "python3"
        pip_check = subprocess.run(
            [str(native_python), "-m", "pip", "--version"],
            capture_output=True,
            text=True,
        )
        if pip_check.returncode != 0:
            ensure_res = subprocess.run(
                [str(native_python), "-m", "ensurepip"],
                capture_output=True,
                text=True,
            )
            if ensure_res.returncode != 0:
                raise BuildError(f"Failed to initialize pip in SDK Python:\n{ensure_res.stderr}")

        # Locate target _sysconfigdata in target sysroot
        target_py_lib = target_sysroot / "usr" / "lib" / py_version_dir
        sysconfig_files = list(target_py_lib.glob("_sysconfigdata*.py"))
        if not sysconfig_files:
            raise BuildError(f"No _sysconfigdata file found in {target_py_lib}")
        target_sysconfig = sysconfig_files[0]
        sysconfig_name = target_sysconfig.stem

        # Ensure target _sysconfigdata is copied/symlinked into native Python lib so build isolation can import it
        native_py_lib = native_sysroot / "usr" / "lib" / py_version_dir
        native_sysconfig_link = native_py_lib / target_sysconfig.name
        if not native_sysconfig_link.exists():
            try:
                native_sysconfig_link.symlink_to(target_sysconfig)
            except OSError:
                shutil.copy2(target_sysconfig, native_sysconfig_link)

        return {
            "devkit_root": root,
            "sdk_env_file": sdk_env_file,
            "target_sysroot": target_sysroot,
            "native_sysroot": native_sysroot,
            "native_python": native_python,
            "python_version": py_version_dir,
            "sysconfig_name": sysconfig_name,
            "target_include_dir": target_sysroot / "usr" / "include" / py_version_dir,
        }

    @classmethod
    def install_pip_packages(
        cls,
        packages: List[str],
        target: Target,
        dest_dir: Path,
        devkit_root: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        no_build_isolation: bool = False,
        clean_cache: bool = False,
    ) -> None:
        """
        Cross-compiles and installs PyPI packages into dest_dir for the target device architecture.
        Packages requiring C/C++ compilation (like numpy) are built using the SDK target toolchain.
        Pre-built wheels are cached in ~/.cache/asteroidos/wheels/<arch> to accelerate subsequent builds.
        """
        if not packages:
            return

        dest_dir = Path(dest_dir).resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)

        env_info = cls.setup_target_python_cross_env(target, devkit_root)
        root = env_info["devkit_root"]
        sdk_env_file = env_info["sdk_env_file"]
        target_inc = env_info["target_include_dir"]
        sysconfig_name = env_info["sysconfig_name"]
        target_arch = target.arch

        # Wheelhouse and pip download caches
        wheelhouse_dir = cache_dir or (Path.home() / ".cache" / "asteroidos" / "wheels" / target_arch)
        wheelhouse_dir.mkdir(parents=True, exist_ok=True)
        pip_cache = Path.home() / ".cache" / "asteroidos" / "pip"
        pip_cache.mkdir(parents=True, exist_ok=True)

        if clean_cache and wheelhouse_dir.exists():
            for f in wheelhouse_dir.glob("*.whl"):
                f.unlink()

        pkg_args = " ".join(f'"{p}"' for p in packages)
        isolation_flag = "--no-build-isolation" if no_build_isolation else ""

        # Build command:
        # Step 1: Compile target wheels into wheelhouse using the cross compiler
        # Step 2: Install from wheelhouse into dest_dir
        build_script = (
            f"set -e\n"
            f"unset LD_LIBRARY_PATH\n"
            f"source \"{sdk_env_file}\"\n"
            f"export _PYTHON_SYSCONFIGDATA_NAME=\"{sysconfig_name}\"\n"
            f"export CPPFLAGS=\"-I{target_inc} ${{CPPFLAGS:-}}\"\n"
            f"export CFLAGS=\"-O2 -g -pipe -I{target_inc} ${{CFLAGS:-}}\"\n"
            f"export CXXFLAGS=\"-O2 -g -pipe -I{target_inc} ${{CXXFLAGS:-}}\"\n"
            f"python3 -m pip wheel {pkg_args} "
            f"  --no-binary :all: "
            f"  --wheel-dir \"{wheelhouse_dir}\" "
            f"  --find-links \"{wheelhouse_dir}\" "
            f"  --cache-dir \"{pip_cache}\" "
            f"  {isolation_flag}\n"
            f"python3 -m pip install {pkg_args} "
            f"  --no-index "
            f"  --find-links \"{wheelhouse_dir}\" "
            f"  --target \"{dest_dir}\"\n"
        )

        res = subprocess.run(
            ["bash", "-c", build_script],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        if res.returncode != 0:
            raise BuildError(
                f"Failed to cross-compile/install PyPI packages ({', '.join(packages)}) for {target_arch}:\n"
                f"{res.stderr}\n{res.stdout}"
            )


    @classmethod
    def collect_bundled_python(
        cls,
        sysroot: Path,
        app_share_dir: str,
        include_pyside6: bool = True,
    ) -> List[tuple[Path, str, int]]:
        """
        Collects files for a standalone self-contained Python runtime from the target SDK sysroot.
        Similar to an AppImage bundle, this enables running Python apps on AsteroidOS devices
        that do not have python3 pre-installed.
        """
        bundled: List[tuple[Path, str, int]] = []
        py_target_dir = f"{app_share_dir}/python"

        # 1. Python binary
        bin_dir = sysroot / "usr" / "bin"
        py_bin = bin_dir / "python3.13"
        if not py_bin.exists():
            py_bin = bin_dir / "python3"
        if py_bin.exists():
            bundled.append((py_bin, f"{py_target_dir}/bin/python3", 0o755))

        # 2. Python shared library
        lib_dir = sysroot / "usr" / "lib"
        for libpy in lib_dir.glob("libpython3*.so*"):
            if not libpy.name.endswith(".a") and ".debug" not in libpy.name:
                bundled.append((libpy, f"{py_target_dir}/lib/{libpy.name}", 0o755))

        # 3. Standard Library
        stdlib_dir = lib_dir / "python3.13"
        if stdlib_dir.exists():
            # Standard library subpackages (excluding test, repl, caches, and build configs)
            excluded_dirs = {
                "site-packages", "lib-dynload", "unittest", "__pycache__",
                "_pyrepl", "config-3.13-i386-linux-gnu", ".debug",
            }
            for child in stdlib_dir.iterdir():
                if child.is_dir() and child.name not in excluded_dirs and not child.name.startswith("."):
                    for root, _, files in os.walk(child):
                        if "__pycache__" in root or ".debug" in root:
                            continue
                        rel = Path(root).relative_to(stdlib_dir)
                        for f in files:
                            if f.endswith((".py", ".so")):
                                src_f = Path(root) / f
                                dest_f = f"{py_target_dir}/lib/python3.13/{rel}/{f}"
                                bundled.append((src_f, dest_f, 0o644))

            # All standard library .py modules
            for cf in stdlib_dir.iterdir():
                if cf.is_file() and cf.suffix == ".py" and not cf.name.startswith("test_"):
                    bundled.append((cf, f"{py_target_dir}/lib/python3.13/{cf.name}", 0o644))

            # Dynamic extension modules (lib-dynload)
            dynload_dir = stdlib_dir / "lib-dynload"
            if dynload_dir.exists():
                for f in dynload_dir.iterdir():
                    if f.suffix == ".so" and not f.name.startswith("."):
                        bundled.append((f, f"{py_target_dir}/lib/python3.13/lib-dynload/{f.name}", 0o755))

        # 4. PySide6 + Shiboken6 (if requested)
        if include_pyside6:
            # Shared libs
            for pyside_lib in lib_dir.glob("libpyside6*.so*"):
                if not pyside_lib.name.endswith(".a") and ".debug" not in pyside_lib.name:
                    bundled.append((pyside_lib, f"{py_target_dir}/lib/{pyside_lib.name}", 0o755))
            for shiboken_lib in lib_dir.glob("libshiboken6*.so*"):
                if not shiboken_lib.name.endswith(".a") and ".debug" not in shiboken_lib.name:
                    bundled.append((shiboken_lib, f"{py_target_dir}/lib/{shiboken_lib.name}", 0o755))

            # Site-packages
            site_packages = stdlib_dir / "site-packages"
            pyside6_dir = site_packages / "PySide6"
            if pyside6_dir.exists():
                needed_pyside = [
                    "__init__.py", "_config.py", "_git_pyside_version.py",
                    "QtCore.abi3.so", "QtGui.abi3.so", "QtQml.abi3.so", "QtQuick.abi3.so",
                    "QtQuickControls2.abi3.so", "QtNetwork.abi3.so", "QtOpenGL.abi3.so",
                    "QtDBus.abi3.so", "QtSensors.abi3.so",
                ]
                for nf in needed_pyside:
                    src_nf = pyside6_dir / nf
                    if src_nf.exists():
                        perm = 0o755 if nf.endswith(".so") else 0o644
                        bundled.append((src_nf, f"{py_target_dir}/lib/python3.13/site-packages/PySide6/{nf}", perm))

                support_dir = pyside6_dir / "support"
                if support_dir.exists():
                    for root, _, files in os.walk(support_dir):
                        rel = Path(root).relative_to(site_packages)
                        for f in files:
                            src_f = Path(root) / f
                            perm = 0o755 if f.endswith(".so") else 0o644
                            bundled.append((src_f, f"{py_target_dir}/lib/python3.13/site-packages/{rel}/{f}", perm))

            shiboken_dir = site_packages / "shiboken6"
            if shiboken_dir.exists():
                for root, _, files in os.walk(shiboken_dir):
                    rel = Path(root).relative_to(site_packages)
                    for f in files:
                        src_f = Path(root) / f
                        perm = 0o755 if f.endswith(".so") else 0o644
                        bundled.append((src_f, f"{py_target_dir}/lib/python3.13/site-packages/{rel}/{f}", perm))

        return bundled

    @classmethod
    def package_python_app(
        cls,
        app: App,
        target: Target,
        output_file: Optional[Path] = None,
        standalone: bool = True,
        pip_install: bool = True,
        pip_packages: Optional[List[str]] = None,
    ) -> Path:
        """
        Packages a Python-based AsteroidOS application into an installable .ipk file.

        If standalone is True (the default), the package bundles a minimal target Python
        runtime directly into /usr/share/<app-name>/python/ (like an AppImage), allowing
        the application to run even on watch/emulator images where python3 is not pre-installed.

        PyPI packages (both pure-Python and native C/C++ extensions like numpy) are cross-compiled
        and bundled into the application's site-packages directory.
        """
        if not app.project_dir or not app.project_dir.exists():
            raise BuildError(f"Project directory does not exist: {app.project_dir}")

        # Check for sysroot to bundle python
        sysroot = cls.find_target_sysroot(target) if standalone else None
        target_arch = target.arch if (standalone and sysroot) else "all"

        if output_file is None:
            dist_dir = app.project_dir / "dist"
            dist_dir.mkdir(parents=True, exist_ok=True)
            output_file = dist_dir / f"{app.name}-{app.version}.ipk"

        # Dependencies: if standalone, zero host python dependencies needed!
        if standalone and sysroot:
            deps = [d for d in app.metadata.dependencies if not d.startswith("python3")]
        else:
            deps = ["python3-core", "python3-pyside6"]
            for dep in app.metadata.dependencies:
                if dep not in deps:
                    deps.append(dep)

        # Collect PyPI dependencies from metadata, arguments, and requirements.txt
        pip_deps = list(app.metadata.pip_dependencies)
        if pip_packages:
            for p in pip_packages:
                if p not in pip_deps:
                    pip_deps.append(p)
        if app.project_dir:
            req_file = app.project_dir / "requirements.txt"
            if req_file.exists():
                for line in req_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and line not in pip_deps:
                        pip_deps.append(line)

        # Cross-compile and install PyPI dependencies if requested
        staging_site_packages: Optional[Path] = None
        if pip_install and pip_deps:
            devkit_root = cls.find_devkit_root(app.project_dir)
            target_name = target.value if hasattr(target, "value") else str(target)
            actual_target = target if target_name != "all" else Target.EMULATOR

            if sysroot or (target_name != "all" and cls.find_target_sysroot(actual_target, devkit_root)):
                build_cache_dir = app.project_dir / "build" / f"site-packages-{actual_target.arch}" if app.project_dir else None
                staging_dir = build_cache_dir or (Path("/tmp") / f"asteroid-site-{app.name}-{actual_target.arch}")
                cls.install_pip_packages(
                    packages=pip_deps,
                    target=actual_target,
                    dest_dir=staging_dir,
                    devkit_root=devkit_root,
                )
                staging_site_packages = staging_dir
            else:
                # Target 'all' or no sysroot: install pure Python packages
                build_cache_dir = app.project_dir / "build" / "site-packages-all" if app.project_dir else None
                staging_dir = build_cache_dir or (Path("/tmp") / f"asteroid-site-{app.name}-all")
                staging_dir.mkdir(parents=True, exist_ok=True)
                cmd = [sys.executable, "-m", "pip", "install", "--target", str(staging_dir), "--no-deps"] + pip_deps
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    raise BuildError(f"Failed to install pure Python packages ({pip_deps}):\n{res.stderr}")
                staging_site_packages = staging_dir

        control_fields = {
            "Package": app.name,
            "Version": app.version,
            "Description": app.metadata.description,
            "Section": "user/apps",
            "Priority": "optional",
            "Maintainer": app.metadata.author,
            "Architecture": target_arch,
        }
        if deps:
            control_fields["Depends"] = ", ".join(deps)

        # Collect data files
        data_files = []
        app_share_dir = f"/usr/share/{app.name}"

        # 1. Launcher script in /usr/bin/<app_name>
        runscript_src = app.project_dir / "runscript.sh"
        if runscript_src.exists() and not standalone:
            launcher_content = runscript_src.read_text(encoding="utf-8")
        else:
            launcher_content = (
                f"#!/bin/sh\n"
                f"APP_DIR=\"{app_share_dir}\"\n"
                f"if [ -d \"$APP_DIR/python\" ] && [ -x \"$APP_DIR/python/bin/python3\" ]; then\n"
                f"    export PYTHONHOME=\"$APP_DIR/python\"\n"
                f"    export PYTHONPATH=\"$APP_DIR:$APP_DIR/site-packages:$APP_DIR/python/lib/python3.13:$APP_DIR/python/lib/python3.13/site-packages:$PYTHONPATH\"\n"
                f"    export LD_LIBRARY_PATH=\"$APP_DIR/python/lib:$LD_LIBRARY_PATH\"\n"
                f"    exec \"$APP_DIR/python/bin/python3\" \"$APP_DIR/main.py\" \"$@\"\n"
                f"elif command -v python3 >/dev/null 2>&1; then\n"
                f"    export PYTHONPATH=\"$APP_DIR:$APP_DIR/site-packages:$APP_DIR/python/lib/python3.13/site-packages:$PYTHONPATH\"\n"
                f"    exec python3 \"$APP_DIR/main.py\" \"$@\"\n"
                f"else\n"
                f"    echo \"Error: Python runtime not found.\" >&2\n"
                f"    exit 1\n"
                f"fi\n"
            )

        data_files.append((launcher_content.encode("utf-8"), f"/usr/bin/{app.name}", 0o755))

        # 2. Desktop entry in /usr/share/applications/<app_name>.desktop
        desktop_src = app.project_dir / f"{app.name}.desktop"
        if not desktop_src.exists():
            desktop_src = app.project_dir / "desktop"
        if not desktop_src.exists():
            desktop_content = (
                f"[Desktop Entry]\n"
                f"Type=Application\n"
                f"Name={app.title}\n"
                f"Comment={app.metadata.description}\n"
                f"Categories=Applications;\n"
                f"Exec={app.name}\n"
                f"Icon={app.metadata.icon}\n"
                f"X-Asteroid-Center-Color={app.metadata.center_color}\n"
                f"X-Asteroid-Outer-Color={app.metadata.outer_color}\n"
            )
        else:
            desktop_content = desktop_src.read_text(encoding="utf-8")

        data_files.append((
            desktop_content.encode("utf-8"),
            f"/usr/share/applications/{app.name}.desktop",
            0o644,
        ))

        # 3. Application files in /usr/share/<app_name>/
        ignored_patterns = {
            ".git", ".vscode", "dist", "build", "__pycache__", "asteroid.json",
            ".asteroidos", ".cache", ".pytest_cache", ".venv", "venv",
        }

        for root, dirs, files in os.walk(app.project_dir):
            dirs[:] = [d for d in dirs if d not in ignored_patterns and not d.startswith("build-")]
            rel_root = Path(root).relative_to(app.project_dir)

            for file_name in files:
                if file_name in ignored_patterns or file_name.endswith(".ipk"):
                    continue
                if rel_root == Path(".") and file_name in ("runscript.sh", "runscript.in", f"{app.name}.desktop", "desktop"):
                    continue

                file_path = Path(root) / file_name
                rel_dest = Path(app_share_dir) / rel_root / file_name

                is_exec = file_name.endswith((".py", ".sh")) or os.access(file_path, os.X_OK)
                perm = 0o755 if is_exec else 0o644

                data_files.append((file_path, str(rel_dest), perm))

        # 3.5 Bundled PyPI site-packages (including cross-compiled C/C++ extensions)
        if staging_site_packages and staging_site_packages.exists():
            dest_prefix = f"{app_share_dir}/python/lib/python3.13/site-packages" if (standalone and sysroot) else f"{app_share_dir}/site-packages"
            for root, dirs, files in os.walk(staging_site_packages):
                dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
                rel = Path(root).relative_to(staging_site_packages)
                for f in files:
                    if f.endswith((".pyc", ".pyo")):
                        continue
                    src_f = Path(root) / f
                    target_dest = f"{dest_prefix}/{rel}/{f}" if str(rel) != "." else f"{dest_prefix}/{f}"
                    perm = 0o755 if (f.endswith(".so") or os.access(src_f, os.X_OK)) else 0o644
                    data_files.append((src_f, target_dest, perm))

        # 4. Standalone bundled Python runtime (AppImage-style)
        if standalone and sysroot:
            include_pyside6 = "python3-pyside6" in app.metadata.dependencies or (
                (app.project_dir / "main.py").exists() and "PySide6" in (app.project_dir / "main.py").read_text(errors="ignore")
            )
            bundled_runtime = cls.collect_bundled_python(
                sysroot=sysroot,
                app_share_dir=app_share_dir,
                include_pyside6=include_pyside6,
            )
            data_files.extend(bundled_runtime)

        # Build IPK
        IpkPackager.create_ipk(
            output_file=output_file,
            control_fields=control_fields,
            data_files=data_files,
        )

        return output_file

    @classmethod
    def build(
        cls,
        app: App,
        target: Target,
        build_dir: Optional[Path] = None,
        clean: bool = False,
        package: bool = True,
        standalone: bool = True,
        pip_install: bool = True,
        pip_packages: Optional[List[str]] = None,
    ) -> Path:
        """Dispatches build according to app type."""
        from .app import AppType

        if app.app_type == AppType.PYTHON_QML:
            return cls.package_python_app(
                app,
                target,
                output_file=build_dir,
                standalone=standalone,
                pip_install=pip_install,
                pip_packages=pip_packages,
            )
        else:
            return cls.build_native(app, target, build_dir=build_dir, clean=clean, package=package)

    @classmethod
    def package_ipk(
        cls,
        app: App,
        target: Target,
        output_file: Optional[Path] = None,
        standalone: bool = True,
        pip_install: bool = True,
        pip_packages: Optional[List[str]] = None,
    ) -> Path:
        """Packages an application directly into an .ipk package."""
        from .app import AppType

        if app.app_type == AppType.PYTHON_QML:
            return cls.package_python_app(
                app,
                target,
                output_file=output_file,
                standalone=standalone,
                pip_install=pip_install,
                pip_packages=pip_packages,
            )
        else:
            return cls.build_native(app, target, package=True)

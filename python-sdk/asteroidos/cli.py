"""
AsteroidOS Command Line Interface (CLI).

Unified CLI tool for creating, compiling, packaging, deploying, and managing
AsteroidOS applications and the emulator.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
from typing import List, Optional

from .app import App, AppType, Target
from .builder import Builder
from .device import Device
from .emulator import Emulator
from .icons import ALL_ICONS, IOS_PULSE_OUTLINE
from .templates import TemplateManager


def print_header(text: str) -> None:
    print(f"\033[1;34m=== {text} ===\033[0m")


def print_ok(text: str) -> None:
    print(f"\033[1;32m[OK]\033[0m {text}")


def print_info(text: str) -> None:
    print(f"\033[1;34m[INFO]\033[0m {text}")


def print_warn(text: str) -> None:
    print(f"\033[1;33m[WARN]\033[0m {text}")


def print_error(text: str) -> None:
    print(f"\033[1;31m[ERROR]\033[0m {text}", file=sys.stderr)


def cmd_new(args: argparse.Namespace) -> int:
    """Scaffold a new AsteroidOS application."""
    dest_dir = Path(args.dest or args.name)
    print_info(f"Creating new AsteroidOS app '{args.name}' using template '{args.template}'...")

    try:
        app_type = AppType(args.template)
    except ValueError:
        print_error(f"Invalid template '{args.template}'. Choose from: {TemplateManager.list_templates()}")
        return 1

    app = App(
        name=args.name,
        title=args.title or "",
        version=args.version,
        description=args.description,
        author=args.author,
        icon=args.icon,
        center_color=args.center_color,
        outer_color=args.outer_color,
        app_type=app_type,
    )

    try:
        app.generate_project(dest_dir, overwrite=args.force)
        print_ok(f"Project created at {dest_dir.resolve()}")
        print("\nNext steps:")
        print(f"  cd {dest_dir}")
        print(f"  asteroidos build --target emulator")
        print(f"  asteroidos deploy --target emulator")
        return 0
    except Exception as exc:
        print_error(f"Failed to create app: {exc}")
        return 1


def cmd_build(args: argparse.Namespace) -> int:
    """Build an application project."""
    project_dir = Path(args.project_dir or ".").resolve()
    print_info(f"Loading application from {project_dir}...")

    try:
        app = App.load(project_dir)
    except Exception as exc:
        print_error(f"Could not load application from {project_dir}: {exc}")
        return 1

    target = Target(args.target)
    print_info(f"Building '{app.name}' ({app.metadata.app_type.value}) for target '{target.value}'...")

    standalone = not getattr(args, "no_standalone", False)
    pip_packages = getattr(args, "pip_packages", None)
    pip_install = not getattr(args, "no_pip", False)
    try:
        result_path = app.build(
            target=target,
            clean=args.clean,
            package=not args.no_package,
            standalone=standalone,
            pip_install=pip_install,
            pip_packages=pip_packages,
        )
        print_ok(f"Build succeeded! Output: {result_path}")
        return 0
    except Exception as exc:
        print_error(f"Build failed: {exc}")
        return 1


def cmd_package(args: argparse.Namespace) -> int:
    """Directly package an application into an .ipk package."""
    project_dir = Path(args.project_dir or ".").resolve()
    app = App.load(project_dir)
    target = Target(args.target)

    out_file = Path(args.out) if args.out else None
    standalone = not getattr(args, "no_standalone", False)
    pip_packages = getattr(args, "pip_packages", None)
    pip_install = not getattr(args, "no_pip", False)
    try:
        ipk_path = app.package(
            target=target,
            output_file=out_file,
            standalone=standalone,
            pip_install=pip_install,
            pip_packages=pip_packages,
        )
        print_ok(f"Package created: {ipk_path}")
        return 0
    except Exception as exc:
        print_error(f"Packaging failed: {exc}")
        return 1


def cmd_pip(args: argparse.Namespace) -> int:
    """Manage PyPI dependencies for AsteroidOS applications."""
    action = args.pip_action
    if action == "install":
        target = Target(args.target)
        packages = list(args.packages or [])
        project_dir = Path(args.project_dir or ".").resolve()
        dest_dir = Path(args.dest).resolve() if args.dest else project_dir / "build" / f"site-packages-{target.arch}"

        if not packages:
            req_file = project_dir / "requirements.txt"
            if req_file.exists():
                for line in req_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        packages.append(line)
        if not packages:
            print_error("No packages specified and no requirements.txt found.")
            return 1

        print_info(f"Cross-compiling and installing PyPI packages for target '{target.value}': {', '.join(packages)}")
        try:
            Builder.install_pip_packages(
                packages=packages,
                target=target,
                dest_dir=dest_dir,
                clean_cache=getattr(args, "clean_cache", False),
            )
            print_ok(f"Packages successfully installed into {dest_dir}")
            return 0
        except Exception as exc:
            print_error(f"Failed to install packages: {exc}")
            return 1
    elif action == "list":
        project_dir = Path(args.project_dir or ".").resolve()
        try:
            app = App.load(project_dir)
            print_header(f"PyPI Dependencies for '{app.name}'")
            if app.pip_dependencies:
                for p in app.pip_dependencies:
                    print(f"  - {p}")
            else:
                print("  (None configured)")
            return 0
        except Exception as exc:
            print_error(f"Could not load app from {project_dir}: {exc}")
            return 1
    return 0


def cmd_deploy(args: argparse.Namespace) -> int:
    """Deploy an application package to an emulator or physical watch."""
    target = Target(args.target)
    target_str = target.value

    path_arg = Path(args.package_or_dir) if args.package_or_dir else Path(".")
    ipk_path: Optional[Path] = None

    if path_arg.is_file() and path_arg.suffix == ".ipk":
        ipk_path = path_arg
    elif path_arg.is_dir():
        # Search build directory
        candidates = list(path_arg.glob("*.ipk")) + list(path_arg.glob(f"build-{target_str}/*.ipk")) + list(path_arg.glob("dist/*.ipk"))
        if candidates:
            ipk_path = candidates[0]

    if not ipk_path or not ipk_path.exists():
        print_error(f"No .ipk package found in {path_arg}")
        return 1

    device = Device.for_target(target, host=args.host, port=args.port, user=args.user)
    print_info(f"Deploying {ipk_path.name} to {device.user}@{device.host}:{device.port}...")

    try:
        device.install_ipk(ipk_path)
        print_ok(f"Successfully installed {ipk_path.name} on target!")
        return 0
    except Exception as exc:
        print_error(f"Deploy failed: {exc}")
        return 1


def cmd_emulator(args: argparse.Namespace) -> int:
    """Manage the AsteroidOS emulator."""
    action = args.action

    if action == "start":
        print_info("Starting AsteroidOS emulator...")
        Emulator.start(daemon=not args.foreground, acceleration=not args.no_accel)
        if not args.foreground:
            print_ok("Emulator launched in background. Use 'asteroidos emulator status' to check.")
        return 0

    elif action == "stop":
        print_info("Stopping AsteroidOS emulator...")
        if Emulator.stop(force=args.force):
            print_ok("Emulator stopped.")
        else:
            print_info("No emulator processes were running.")
        return 0

    elif action == "status":
        status = Emulator.status()
        print_header("Emulator Status")
        print(f"Running   : {status['running']}")
        print(f"PIDs      : {status['pids']}")
        print(f"SSH Ready : {status['ssh_ready']} (port {status['port']})")
        return 0

    elif action == "wait":
        print_info("Waiting for emulator to become ready...")
        if Emulator.wait_ready(timeout=args.timeout):
            print_ok("Emulator is ready and accepting SSH connections!")
            return 0
        else:
            print_error(f"Timed out after {args.timeout} seconds waiting for emulator.")
            return 1

    return 0


def cmd_screenshot(args: argparse.Namespace) -> int:
    """Capture a screenshot from the target device."""
    target = Target(args.target)
    device = Device.for_target(target, host=args.host, port=args.port, user=args.user)
    out_file = Path(args.output or "screenshot.png")

    print_info(f"Taking screenshot from {target.value}...")
    try:
        saved = device.screenshot(out_file)
        print_ok(f"Screenshot saved to {saved.resolve()}")
        return 0
    except Exception as exc:
        print_error(f"Failed to take screenshot: {exc}")
        return 1


def cmd_doctor(_args: argparse.Namespace) -> int:
    """Run diagnostics on host environment and AsteroidOS DevKit setup."""
    print_header("AsteroidOS DevKit System Check")

    # 1. DevKit Root
    root = Builder.find_devkit_root()
    if root:
        print_ok(f"DevKit root: {root}")
    else:
        print_warn("Could not find DevKit root directory.")

    # 2. Host Python
    print_ok(f"Host Python: {sys.version.split()[0]}")

    # 3. KVM acceleration
    if os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK):
        print_ok("KVM Hardware Virtualization: Available & Accessible (/dev/kvm)")
    elif os.path.exists("/dev/kvm"):
        print_warn("KVM exists but user lacks read/write permissions. Add user to kvm group.")
    else:
        print_warn("KVM acceleration not detected.")

    # 4. QEMU
    qemu_bin = shutil.which("qemu-system-x86_64") or shutil.which("qemu-system-i386")
    if qemu_bin:
        print_ok(f"QEMU binary: {qemu_bin}")
    else:
        print_error("QEMU not installed. Run 'make prereqs' or install qemu-system-x86.")

    # 5. Emulator Kernel & Rootfs
    if root:
        kernel = root / "emulator" / "bzImage-emulator.bin"
        rootfs = root / "emulator" / "asteroid-image-emulator.rootfs.ext4"
        if kernel.exists() and rootfs.exists():
            print_ok("Emulator files: Kernel and rootfs are present.")
        else:
            print_warn("Emulator kernel or rootfs missing. Run 'make setup-emulator'.")

    # 6. SDK Environment
    if root:
        env_emu = root / "env-emulator.sh"
        if env_emu.exists():
            print_ok("Emulator Qt6 SDK: Installed (env-emulator.sh present).")
        else:
            print_warn("Emulator SDK not installed. Run 'make setup-sdk'.")

        # 7. Python Cross-compilation & PyPI Support
        try:
            env_info = Builder.setup_target_python_cross_env(Target.EMULATOR, root)
            print_ok(f"Python Cross-Compiler: Ready ({env_info['python_version']}, {env_info['sysconfig_name']})")
        except Exception as exc:
            print_warn(f"Python cross-compilation not configured: {exc}")

    return 0


def cmd_templates(_args: argparse.Namespace) -> int:
    """List available application templates."""
    print_header("Available App Templates")
    for t in TemplateManager.list_templates():
        desc = "Native C++ Qt6/QML Application" if t == "qml_cpp" else "Python with PySide6 & QML UI"
        print(f"  - \033[1m{t:<10}\033[0m : {desc}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="asteroidos",
        description="AsteroidOS Application Development Kit & Python SDK",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # new
    p_new = subparsers.add_parser("new", help="Scaffold a new AsteroidOS application")
    p_new.add_argument("name", help="Application package name (e.g. asteroid-timer)")
    p_new.add_argument("--title", help="Human-friendly app title (e.g. 'Timer')")
    p_new.add_argument("--template", "-t", default="qml_cpp", choices=TemplateManager.list_templates(), help="Template type")
    p_new.add_argument("--version", "-v", default="1.0.0", help="App version")
    p_new.add_argument("--description", "-d", default="An application for AsteroidOS", help="App description")
    p_new.add_argument("--author", "-a", default="AsteroidOS Developer <developer@example.org>", help="Author")
    p_new.add_argument("--icon", default=IOS_PULSE_OUTLINE, help="Icon name")
    p_new.add_argument("--center-color", default="#b04d1c", help="Center background color hex")
    p_new.add_argument("--outer-color", default="#421c0a", help="Outer background color hex")
    p_new.add_argument("--dest", help="Destination directory (default: same as name)")
    p_new.add_argument("--force", "-f", action="store_true", help="Overwrite existing directory")
    p_new.set_defaults(func=cmd_new)

    # build
    p_build = subparsers.add_parser("build", help="Compile and build application")
    p_build.add_argument("project_dir", nargs="?", default=".", help="Application directory")
    p_build.add_argument("--target", "-t", default="emulator", choices=["emulator", "arm", "all"], help="Build target")
    p_build.add_argument("--clean", action="store_true", help="Clean build directory first")
    p_build.add_argument("--no-package", action="store_true", help="Compile only, skip .ipk creation")
    p_build.add_argument("--standalone", action="store_true", default=True, help="Bundle self-contained Python runtime (AppImage-style)")
    p_build.add_argument("--no-standalone", action="store_true", help="Do not bundle Python runtime")
    p_build.add_argument("--pip-package", action="append", dest="pip_packages", help="PyPI package to bundle (can be specified multiple times)")
    p_build.add_argument("--no-pip", action="store_true", help="Skip installing PyPI dependencies")
    p_build.set_defaults(func=cmd_build)

    # package
    p_pkg = subparsers.add_parser("package", help="Package application into .ipk archive")
    p_pkg.add_argument("project_dir", nargs="?", default=".", help="Application directory")
    p_pkg.add_argument("--target", "-t", default="emulator", choices=["emulator", "arm", "all"], help="Build target")
    p_pkg.add_argument("--out", "-o", help="Output .ipk file path")
    p_pkg.add_argument("--standalone", action="store_true", default=True, help="Bundle self-contained Python runtime (AppImage-style)")
    p_pkg.add_argument("--no-standalone", action="store_true", help="Do not bundle Python runtime")
    p_pkg.add_argument("--pip-package", action="append", dest="pip_packages", help="PyPI package to bundle (can be specified multiple times)")
    p_pkg.add_argument("--no-pip", action="store_true", help="Skip installing PyPI dependencies")
    p_pkg.set_defaults(func=cmd_package)

    # pip
    p_pip = subparsers.add_parser("pip", help="Cross-compile and manage PyPI packages for AsteroidOS")
    pip_subs = p_pip.add_subparsers(dest="pip_action", required=True)

    p_pip_install = pip_subs.add_parser("install", help="Cross-compile and install packages from PyPI")
    p_pip_install.add_argument("packages", nargs="*", help="Package names (e.g. numpy, requests)")
    p_pip_install.add_argument("--target", "-t", default="emulator", choices=["emulator", "arm", "watch"], help="Target device architecture")
    p_pip_install.add_argument("--dest", "-d", help="Custom destination site-packages directory")
    p_pip_install.add_argument("--project-dir", help="Project directory")
    p_pip_install.add_argument("--clean-cache", action="store_true", help="Clear wheel cache before building")
    p_pip_install.set_defaults(func=cmd_pip)

    p_pip_list = pip_subs.add_parser("list", help="List PyPI dependencies declared in the project")
    p_pip_list.add_argument("project_dir", nargs="?", default=".", help="Project directory")
    p_pip_list.set_defaults(func=cmd_pip)

    # deploy
    p_deploy = subparsers.add_parser("deploy", help="Deploy .ipk package to emulator or physical watch")
    p_deploy.add_argument("package_or_dir", nargs="?", default=".", help="Path to .ipk or project build directory")
    p_deploy.add_argument("--target", "-t", default="emulator", choices=["emulator", "watch"], help="Target device")
    p_deploy.add_argument("--host", "-H", help="Target IP or hostname")
    p_deploy.add_argument("--port", "-p", type=int, help="SSH port")
    p_deploy.add_argument("--user", "-u", help="SSH user")
    p_deploy.set_defaults(func=cmd_deploy)

    # emulator
    p_emu = subparsers.add_parser("emulator", help="Manage AsteroidOS QEMU emulator")
    p_emu.add_argument("action", choices=["start", "stop", "status", "wait"], help="Action")
    p_emu.add_argument("--foreground", "-f", action="store_true", help="Run emulator in foreground")
    p_emu.add_argument("--no-accel", action="store_true", help="Disable KVM acceleration")
    p_emu.add_argument("--timeout", type=int, default=60, help="Wait timeout in seconds")
    p_emu.set_defaults(func=cmd_emulator)

    # screenshot
    p_shot = subparsers.add_parser("screenshot", help="Capture a screenshot from target device")
    p_shot.add_argument("output", nargs="?", default="screenshot.png", help="Output PNG path")
    p_shot.add_argument("--target", "-t", default="emulator", choices=["emulator", "watch"], help="Target device")
    p_shot.add_argument("--host", "-H", help="Target IP or hostname")
    p_shot.add_argument("--port", "-p", type=int, help="SSH port")
    p_shot.add_argument("--user", "-u", help="SSH user")
    p_shot.set_defaults(func=cmd_screenshot)

    # doctor
    p_doc = subparsers.add_parser("doctor", help="Run system diagnostics")
    p_doc.set_defaults(func=cmd_doctor)

    # templates
    p_tmpl = subparsers.add_parser("templates", help="List available application templates")
    p_tmpl.set_defaults(func=cmd_templates)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        return args.func(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())


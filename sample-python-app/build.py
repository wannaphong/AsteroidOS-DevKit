#!/usr/bin/env python3
"""
Build script for sample-python-app.
Uses the AsteroidOS Python SDK to package the app into an installable .ipk package.
"""

from pathlib import Path
import sys

# Ensure python-sdk is in path if running from source checkout
repo_root = Path(__file__).resolve().parent.parent
sdk_path = repo_root / "python-sdk"
if sdk_path.exists():
    sys.path.insert(0, str(sdk_path))

from asteroidos import App, Target

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build and package AsteroidOS Python application")
    parser.add_argument("-t", "--target", default="emulator", choices=["emulator", "watch", "arm", "all"],
                        help="Target device architecture (default: emulator)")
    parser.add_argument("--no-standalone", action="store_true", help="Do not bundle standalone Python runtime")
    args = parser.parse_args()

    app_dir = Path(__file__).resolve().parent
    print(f"Loading AsteroidOS application from {app_dir}...")
    app = App.load(app_dir)

    target_map = {
        "emulator": Target.EMULATOR,
        "watch": Target.ARM,
        "arm": Target.ARM,
        "all": Target.ALL,
    }
    target = target_map.get(args.target, Target.EMULATOR)
    standalone = not args.no_standalone if target != Target.ALL else False

    print(f"Packaging {app.name} (version {app.version}) for target '{args.target}' (standalone={standalone})...")
    ipk_path = app.package(target=target, standalone=standalone)

    print(f"\n[OK] Package built successfully!")
    print(f"Output IPK: {ipk_path}")
    print(f"Size: {ipk_path.stat().st_size} bytes")
    print(f"\nDeploy to emulator:")
    print(f"  asteroidos deploy {ipk_path} --target emulator")
    print(f"Or using make:")
    print(f"  make deploy-sample-python")

if __name__ == "__main__":
    main()


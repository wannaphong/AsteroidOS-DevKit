# ==============================================================================
# AsteroidOS DevKit Makefile
# ==============================================================================

.PHONY: help prereqs setup-emulator setup-sdk setup-sdk-arm setup-sdk-all emulator emulator-gtk ssh build-sample-emulator build-sample-arm deploy-sample clean

help:
	@echo "AsteroidOS DevKit Commands:"
	@echo ""
	@echo "  make prereqs               - Install host dependencies (apt, dnf, pacman, etc.)"
	@echo "  make setup-emulator        - Download AsteroidOS emulator kernel & rootfs"
	@echo "  make setup-sdk             - Download & install Qt6 SDK for Emulator (default)"
	@echo "  make setup-sdk-arm         - Download & install Qt6 SDK for ARM smartwatches"
	@echo "  make setup-sdk-all         - Download & install both Emulator and ARM SDKs"
	@echo "  make emulator              - Launch AsteroidOS Emulator (SDL display)"
	@echo "  make emulator-gtk          - Launch Emulator with GTK frontend & cursor visible"
	@echo "  make ssh                   - Connect to running Emulator via SSH"
	@echo "  make build-sample-emulator - Compile sample-app for Emulator and generate .ipk"
	@echo "  make build-sample-arm      - Compile sample-app for ARM watch and generate .ipk"
	@echo "  make deploy-sample         - Deploy sample-app IPK to running emulator"
	@echo "  make build-sample-python   - Package sample Python watch app (sample-python-app)"
	@echo "  make deploy-sample-python  - Deploy sample Python app to running emulator"
	@echo "  make build-python-examples - Run Python SDK example app builders"
	@echo "  make python-sdk-install    - Install Python SDK in editable mode"
	@echo "  make python-sdk-test       - Run Python SDK test suite"
	@echo "  make clean                 - Remove build artifacts from sample apps"
	@echo ""

prereqs:
	@./scripts/install-prereqs.sh

setup-emulator:
	@./scripts/setup-emulator.sh

setup-sdk:
	@./scripts/setup-sdk.sh --target emulator

setup-sdk-arm:
	@./scripts/setup-sdk.sh --target arm

setup-sdk-all:
	@./scripts/setup-sdk.sh --target all

emulator:
	@./scripts/run-emulator.sh

emulator-gtk:
	@./scripts/run-emulator.sh --display gtk --show-cursor

ssh:
	@./scripts/ssh-emulator.sh

build-sample-emulator:
	@./scripts/build-app.sh sample-app --target emulator

build-sample-arm:
	@./scripts/build-app.sh sample-app --target arm

deploy-sample:
	@./scripts/deploy-app.sh sample-app/build-emulator

build-sample-python:
	@python3 sample-python-app/build.py

deploy-sample-python:
	@./scripts/deploy-app.sh sample-python-app/dist

build-python-examples:
	@echo "==> Running Example 1 (Native App Build):"
	@python3 python-sdk/examples/01_create_native_app.py
	@echo ""
	@echo "==> Running Example 2 (Python App Package):"
	@python3 python-sdk/examples/02_create_python_app.py

python-sdk-install:
	@pip install --break-system-packages -e ./python-sdk || pip install -e ./python-sdk

python-sdk-test:
	@python3 -m unittest discover -s python-sdk/tests -v

clean:
	@rm -rf sample-app/build-emulator sample-app/build-arm sample-python-app/dist


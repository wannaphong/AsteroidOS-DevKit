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
	@echo "  make clean                 - Remove build artifacts from sample-app"
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

clean:
	@rm -rf sample-app/build-emulator sample-app/build-arm


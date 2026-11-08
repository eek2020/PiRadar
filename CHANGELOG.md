# Changelog

All notable changes will be documented here. The project follows [Semantic Versioning](https://semver.org/) once the first release is tagged.

## [Unreleased]

### Added

- Product definition and engineering documentation
- Dependency-light Python application scaffold
- Normalized aircraft-provider interface and mock provider
- Touch-oriented radar UI scaffold
- Tests, CI, systemd and installation scaffolding
- Live adsb.lol provider with caching and stale/offline recovery
- Full-screen geographic aircraft map with touch-sized controls and selectable telemetry
- Persistent postcode-based radar positioning
- In-app NetworkManager Wi-Fi scanning and connection controls
- Touchscreen calibration and kiosk input hardening for the reference display
- Public contribution and security-reporting guidance
- Hardware-beta README with verified display, stylus, Wi-Fi, operating, and future receiver guidance
- Separate on-screen keyboards: a large-key postcode pad and a full UK keyboard with Shift and Caps Lock for passwords and API keys
- Show/hide toggle on every password field
- Safe Shut down and Restart under Map options → Power
- Clear Wi-Fi failure messages (wrong-length password, WPA3 mixed mode, weak signal, no address) with NetworkManager's reason shown and logged
- Wi-Fi compatibility mode for WPA2/WPA3 mixed-mode routers, on by default for Pi 3 / Zero 2 boards and delivered over the air (`scripts/wifi-compat.sh`)
- Version and build shown at the foot of Map options
- Optional PiRadar boot, restart and shutdown splash (`scripts/install-splash.sh`)
- Over-the-air updates: Software update panel (check, install, automatic updates every 15 minutes, on by default, with self-restart when needed) driving `scripts/update.sh`, with exact-commit installs, pre-install tests, health check, automatic rollback and no downgrades

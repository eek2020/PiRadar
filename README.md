# PiRadar

PiRadar is a dedicated Raspberry Pi aircraft-radar appliance designed to boot directly into a polished full-screen airspace display.

The first release will use an online ADS-B data provider. The architecture deliberately supports a later upgrade to a local 1090 MHz receiver using an RTL-SDR and `readsb`, without replacing the user interface or rebuilding the device.

## Current status

The hardware and kiosk approach have been proven on:

- Raspberry Pi 3 Model B v1.2
- Debian 13 (Trixie), 64-bit
- 5-inch 800×480 HDMI display
- XPT2046/ADS7846-compatible resistive touch controller
- Chromium 150 on Wayland

The current files on the Raspberry Pi are a proof of concept. This repository is the clean implementation source of truth.

## Product goals

- Power-on appliance experience
- Custom startup splash
- Automatic full-screen launch
- No visible Linux desktop or browser chrome
- Graceful offline and reconnecting states
- Self-recovery after application failure
- Configurable home location and radar range
- Optional future local RTL-SDR receiver
- Maintainable, documented and reproducible build

## Planned structure

```text
PiRadar/
├── backend/
├── frontend/
├── assets/
├── config/
├── docs/
├── hardware/
├── scripts/
├── systemd/
├── tests/
└── release/
```

See [`docs/`](docs/) for the project definition, architecture, status, roadmap and clean-build route.

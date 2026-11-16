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
- Aircraft drawn by type: specific silhouettes for airliners (A320, A330, A340, A380, 737, 747, 767, 777, 787, E-Jets, CRJ, Dash 8 and more), business jets and light aircraft (icons by ADS-B Radar, https://adsb-radar.com), plus PiRadar's own military set (Typhoon, Rafale, F-35, Hawk, Apache, Merlin, Chinook, C-130, C-17, A400M, Osprey); chosen on the Pi from the ICAO type code with an emitter-category fallback, sized by class
- Settings panels open as a centred, larger dialog over a dimmed map, with touch-sized text and controls; tap the map to close
- Jets whose type codes start with H (Hawk, Hawker 800, HondaJet) no longer draw as helicopters
- MIL button showing only military aircraft from adsb.lol's military feed, within `military_range_nm` (default 400 NM); the commercial feed is not fetched while it is on
- gzip-compressed adsb.lol requests, about 4-5x smaller downloads on mobile data
- Persistent postcode-based radar positioning
- In-app NetworkManager Wi-Fi scanning and connection controls
- Touchscreen calibration and kiosk input hardening for the reference display
- Public contribution and security-reporting guidance
- Hardware-beta README with verified display, stylus, Wi-Fi, operating, and future receiver guidance
- Separate on-screen keyboards: a large-key postcode pad and a full UK keyboard with Shift and Caps Lock for passwords and API keys
- Show/hide toggle on every password field
- Safe Shut down and Restart under Map options → Power
- Clear Wi-Fi failure messages (wrong-length password, WPA3 mixed mode, weak signal, no address) with NetworkManager's reason shown and logged
- `./emulate`: run the real PiRadar interface on an emulated Pi and router (scenarios for WPA2, WPA3 mixed/only, stale profiles, weak signal, no DHCP) to rehearse changes before pushing
- Wi-Fi Details screen: router security flags, compatibility mode state and the Pi's own Wi-Fi log, sized for one photo
- Saved Wi-Fi profiles for a network are cleared before each attempt, so a stale wrong password cannot block a correct one
- Wi-Fi compatibility mode for WPA2/WPA3 mixed-mode routers, on by default for Pi 3 / Zero 2 boards and delivered over the air (`scripts/wifi-compat.sh`)
- Version and build shown at the foot of Map options
- Optional PiRadar boot, restart and shutdown splash (`scripts/install-splash.sh`)
- Over-the-air updates: Software update panel (check, install, automatic updates every 15 minutes, on by default, with self-restart when needed) driving `scripts/update.sh`, with exact-commit installs, pre-install tests, health check, automatic rollback and no downgrades

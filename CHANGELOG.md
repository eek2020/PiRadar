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
- MIL button showing only military aircraft from adsb.lol's military feed, within `military_range_nm` (default 400 NM); the commercial feed is not fetched while it is on
- gzip-compressed adsb.lol requests, about 4-5x smaller downloads on mobile data
- Persistent postcode-based radar positioning
- In-app NetworkManager Wi-Fi scanning and connection controls
- Touchscreen calibration and kiosk input hardening for the reference display
- Public contribution and security-reporting guidance
- Hardware-beta README with verified display, stylus, Wi-Fi, operating, and future receiver guidance

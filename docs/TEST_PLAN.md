# Test Plan

## Automated

- Configuration parsing, precedence and validation
- Provider contract and generated track bounds
- Health, configuration and aircraft API responses
- Static-file routing and not-found behaviour
- Python compilation and unit tests in CI

## Manual desktop

- Run with mock data and verify continuous track motion
- Resize to 800×480 and confirm no page scrolling
- Select and dismiss multiple aircraft details
- Stop the backend and verify the offline state
- Confirm keyboard focus remains visible for development accessibility

## Target hardware

- Cold-boot and shutdown tests
- Touch accuracy at edges and controls
- Chromium kiosk and pointer hiding
- Wi-Fi loss/recovery and DNS/provider failure
- Backend crash recovery under systemd
- Four-hour and 24-hour soak tests with temperature and memory observation


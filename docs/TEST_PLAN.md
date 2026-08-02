# Test Plan

## Automated

- Configuration parsing, precedence and validation
- Provider contract and generated track bounds
- Live-provider normalization, refresh caching, selected-aircraft enrichment and stale/offline fallback
- Health, configuration and aircraft API responses
- Persistent enrichment expiry and owner-only credential storage
- Credential settings responses never disclose secret values
- Static-file routing and not-found behaviour
- Python compilation and unit tests in CI

## Manual desktop

- Run with mock data and verify continuous track motion
- Resize to 800×480 and confirm no page scrolling
- Select and dismiss multiple aircraft details
- Change map style, marker colour and callsign-label options; reload and confirm persistence
- Filter by each aircraft class and altitude band; confirm shown/total counts and reset behaviour
- Select a moving aircraft and confirm its green trail grows without blocking marker selection
- Toggle airports and confirm OXF/EGTK and nearby coded airfields appear at appropriate zoom levels
- Select several airport markers and confirm the airfield detail card opens above all map layers
- Stop the backend and verify the offline state
- Save, replace and clear a test data-service credential; verify only configured status is shown
- Confirm no configured optional provider is contacted while its connector remains disabled
- Confirm keyboard focus remains visible for development accessibility

## Target hardware

- Cold-boot and shutdown tests
- Touch accuracy at edges, map gestures, aircraft selection and display controls
- Chromium kiosk and pointer hiding over both Leaflet and application controls
- Wi-Fi loss/recovery and DNS/provider failure
- Backend crash recovery under systemd
- Four-hour and 24-hour soak tests with temperature and memory observation

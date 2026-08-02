# Technical Specification

## Runtime

- Python 3.11 or newer, using the operating-system interpreter
- A dependency-light HTTP process managed by systemd
- Chromium in kiosk mode, pointed at the loopback service
- JSON configuration in `/etc/piradar/piradar.json` for deployment

The initial runtime has no third-party Python dependencies, so the appliance service runs directly from `/opt/piradar/backend` without a virtual environment or package download.

## Boundaries

The backend owns configuration, provider access, normalization and static delivery. Providers return `Aircraft` domain objects. The browser owns visualization and transient selection state, and polls the normalized endpoint. No provider response shape may leak into frontend code.

The frontend vendors Leaflet 1.9.4 locally and reads its raster tile URL template from public configuration. The initial default is the standard OpenStreetMap HTTPS tile service. Browser caching and referer behaviour are left intact, attribution remains visible, and PiRadar never prefetches or bulk-downloads tiles. A production release must review tile capacity and may select another OSM-derived provider without changing the application code.

The `adsb_lol` adapter requests the documented nearby-aircraft endpoint at no more than the configured refresh interval. Successful results are cached; a later upstream failure returns the last snapshot as stale rather than clearing the display. The mock adapter remains the deterministic offline development source.

## Aircraft contract

Each track provides an ICAO hex identifier, callsign, latitude, longitude, altitude in feet, ground speed in knots, true track in degrees and vertical rate in feet per minute. Missing upstream fields will be handled explicitly when the live provider is introduced.

## Configuration precedence

Built-in safe defaults are overridden by a JSON file selected with `PIRADAR_CONFIG`, then by individual `PIRADAR_*` environment variables. Secrets will be referenced through environment or a protected file and will never be returned from `/api/config`.

## Reliability direction

The service exposes health separately from aircraft data. systemd restarts unexpected exits. The UI applies a freshness threshold to snapshots and retains a clear status indicator throughout provider failures.

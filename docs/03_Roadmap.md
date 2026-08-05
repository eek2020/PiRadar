# Roadmap

## Phase 1 — Foundation

- [x] Establish repository and documentation
- [x] Define the internal aircraft API
- [x] Add a runnable mock-data vertical slice
- [ ] Confirm target Pi deployment from a clean OS image

## Phase 2 — Kiosk appliance

- [ ] Calibrate touch
- [ ] Launch Chromium automatically in kiosk mode
- [ ] Add splash, watchdog and graceful shutdown behaviour

## Phase 3 — Radar engine

- [x] Integrate adsb.lol behind the provider interface
- [x] Normalize tracks behind the internal aircraft contract
- [ ] Confirm provider production usage and attribution presentation
- [ ] Add filtering, selection and trail history

## Phase 4 — Polish

- [ ] Settings UI, offline states and reconnect behaviour
- [ ] Performance and soak testing
- [ ] Gift-ready setup and operating guide

## Phase 5 — Travel and positioning

- [x] Allow a destination postcode to become the persistent radar centre
- [ ] Add optional USB GNSS/GPS support through `gpsd`
- [ ] Refresh the radar centre only after a configurable movement threshold or interval
- [ ] Preserve manual postcode selection as a fallback when GPS is absent or has no fix
- [ ] Show GPS fix age and accuracy without retaining a location history

## Phase 6 — Local receiver

- [ ] Add RTL-SDR and `readsb` provider
- [ ] Support provider selection without frontend changes

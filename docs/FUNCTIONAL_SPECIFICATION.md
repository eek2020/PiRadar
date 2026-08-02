# Functional Specification

## Core behaviour

| ID | Requirement | Acceptance signal |
|---|---|---|
| FR-001 | Start automatically after boot | Radar appears with no user input |
| FR-002 | Display aircraft within the configured range | Visible tracks match normalized provider data |
| FR-003 | Show callsign, altitude, speed and direction | Selecting a track presents available details |
| FR-004 | Support touch-first interaction | Primary actions work without hover or keyboard |
| FR-005 | Explain loading, offline and provider-error states | UI never fails to an empty unlabelled screen |
| FR-006 | Recover after service or provider interruption | Updates resume without restarting the device |
| FR-007 | Store location and range outside source code | Settings are loaded from deployment configuration |
| FR-008 | Isolate provider-specific formats | Frontend uses only the PiRadar API contract |

## Non-functional requirements

- The application must fit an 800×480 viewport without scrolling in normal operation.
- Runtime dependencies and background work should be conservative for a Pi 3B.
- Public API responses must contain no credentials or private configuration paths.
- Logs must be useful through `journalctl` and must not contain provider tokens.
- Aircraft data is informational and must not be represented as complete or safety-critical.


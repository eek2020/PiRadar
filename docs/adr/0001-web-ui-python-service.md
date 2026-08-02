# ADR 0001: Web UI with a Python service

- Status: Accepted
- Date: 2026-08-02

## Context

The reference Pi must provide a polished kiosk while remaining approachable to contributors and replaceable at component boundaries.

## Decision

Use a local HTML/CSS/JavaScript frontend served by a Python service. Chromium provides the appliance viewport. The backend owns data retrieval and normalization.

## Consequences

The interface can be developed on any desktop browser and the backend can use the mature Python Raspberry Pi ecosystem. Chromium adds memory overhead, so UI complexity and long-running resource use must be tested on the Pi 3B.


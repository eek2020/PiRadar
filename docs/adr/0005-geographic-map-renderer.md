# ADR 0005: Use a geographic map as the primary display

- Status: Accepted
- Date: 2026-08-02

## Context

A circular radar plot preserves distance and bearing but lacks the town, road and terrain context that makes a nearby-aircraft appliance immediately understandable. Dense UK traffic also turns plot labels into clutter.

## Decision

Use a full-screen Leaflet map with oriented aircraft markers and an overlaid selection card. Vendor the stable Leaflet 1.9.4 runtime so UI startup does not depend on a CDN. Read the HTTPS tile URL template from configuration and initially use standard OpenStreetMap raster tiles with visible attribution and normal browser caching.

## Consequences

The display resembles a geographic aircraft tracker rather than a traditional scope and uses the whole 800×480 viewport. Map tiles require internet access and a policy-compliant provider. OpenStreetMap's community tile servers are best effort, prohibit bulk/offline downloading and may not be appropriate for a widely deployed production appliance; the configurable tile URL allows a later provider change.

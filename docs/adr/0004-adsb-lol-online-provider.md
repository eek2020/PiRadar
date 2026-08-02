# ADR 0004: Use adsb.lol as the initial online provider

- Status: Accepted for development; production contact pending
- Date: 2026-08-02

## Context

Version 1 needs an internet-fed source of nearby ADS-B positions. Spike 001 proved the adsb.lol v2 point/radius endpoint on the reference Pi, and the service publishes an OpenAPI description.

## Decision

Implement adsb.lol as the first online adapter behind PiRadar's internal aircraft contract. Poll no faster than every eight seconds by default, identify requests with a PiRadar user agent, cache successful responses and retain stale data through temporary failures. Keep the mock provider as the default for development.

## Consequences

The appliance gains live nearby-aircraft positions without credentials or extra Python packages. Public data is ODbL-licensed and requires appropriate attribution in a production release. The service states that production consumers should contact its operator and warns that an API key may be required later, so this decision must be reviewed before v1.0.

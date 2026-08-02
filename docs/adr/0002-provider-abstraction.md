# ADR 0002: Normalize aircraft providers behind an internal API

- Status: Accepted
- Date: 2026-08-02

## Context

Version 1 uses internet-fed ADS-B data, while a future version may consume local `readsb` output. Their schemas and failure modes differ.

## Decision

Provider adapters return common aircraft domain objects. The frontend consumes only the PiRadar JSON API and never calls an external provider directly.

## Consequences

Provider changes do not require a UI rewrite and credentials remain server-side. The internal contract must be deliberately versioned if breaking changes become necessary.


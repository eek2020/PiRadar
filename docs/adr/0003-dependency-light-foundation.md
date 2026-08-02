# ADR 0003: Begin with a dependency-light foundation

- Status: Accepted
- Date: 2026-08-02

## Context

The initial vertical slice needs to run on a clean development machine and on modest hardware before the live provider is selected.

## Decision

Use the Python standard library for the first HTTP and test scaffold. Introduce third-party dependencies only when a concrete requirement justifies them.

## Consequences

Bootstrap and recovery are simple. If routing, concurrency or validation needs grow, this decision should be superseded by an ADR selecting a maintained web framework.


# Project Definition

## Purpose

PiRadar turns a Raspberry Pi 3B and compact touch display into a single-purpose nearby-aircraft display. It should feel calm, immediate and dependable enough to give as a finished appliance while remaining understandable to an open-source contributor.

## Version 1 outcome

A user can power on the device, see a branded startup transition and reach a full-screen radar display automatically. Nearby aircraft from an internet service appear with useful flight information. Temporary loss of internet or provider service is explained and recovered from without user intervention.

## Users

- An owner who wants an attractive always-on view of nearby aviation
- A maker reproducing the appliance on supported hardware
- A contributor adding providers, UI features or hardware support

## In scope for v1

- Raspberry Pi 3B reference hardware
- 800×480 landscape touch display
- Internet-fed ADS-B positions
- Configurable home position and range
- Radar overview and aircraft detail
- Offline/reconnecting states
- Automatic startup and process recovery
- Reproducible installation documentation

## Explicitly later

- Direct 1090 MHz reception through RTL-SDR and `readsb`
- Route enrichment requiring separate commercial data
- Multiple displays, remote fleet management or cloud accounts
- Navigation, collision avoidance or safety-critical use

## Success measures

- Cold boot reaches the radar without keyboard or mouse input
- A service failure recovers automatically
- Network loss never leaves a blank or misleading display
- The main view remains responsive with 100 visible aircraft on a Pi 3B
- A new installation can be reproduced from the repository instructions


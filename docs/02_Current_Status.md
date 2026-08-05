# Current Status

## Proven on the reference appliance

- Raspberry Pi OS installed
- Raspberry Pi Connect working
- 5-inch 800×480 HDMI display working
- Chromium kiosk launch proven
- XPT2046 resistive touch enabled and detected through the kernel ADS7846 driver
- Full-screen geographic map, live aircraft plotting, touch pan/zoom and marker selection proven
- Display options, aircraft filters, type-specific silhouettes, local trails and a public-domain UK airport layer implemented
- Persistent enrichment cache and protected in-app credential storage prepared for optional data providers
- Persistent postcode-based radar positioning and in-app Wi-Fi selection
- Kiosk cursor hidden across the map and controls
- Initial branded loading screen created
- Project workspace created under `/opt/piradar`

## Clean implementation

The repository now contains a working hardware-beta implementation: a Python service, mock and adsb.lol aircraft-data providers, a geographic browser radar UI, persistent settings, tests and deployment support. The current build has been demonstrated to its new owner on the reference Pi, including calibrated touch and in-app Wi-Fi selection.
The deployment scaffold incorporates the proven Cage, Wayland and Chromium kiosk route from Spike 001.

## Outstanding

- Confirm production usage expectations with the adsb.lol operator
- Reproduce the complete installation from a clean OS image
- Add the custom boot splash
- Add watchdog and offline recovery validation
- Implement and explicitly enable optional paid-provider adapters only if a service is selected later
- Package and test a reproducible release image

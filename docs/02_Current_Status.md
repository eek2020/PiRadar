# Current Status

## Proven on the prototype

- Raspberry Pi OS installed
- Raspberry Pi Connect working
- 5-inch 800×480 HDMI display working
- Chromium kiosk launch proven
- XPT2046 resistive touch enabled and detected through the kernel ADS7846 driver
- Full-screen geographic map, live aircraft plotting, touch pan/zoom and marker selection proven
- Display options, aircraft filters, type-specific silhouettes, local trails and a public-domain UK airport layer implemented
- Persistent enrichment cache and protected in-app credential storage prepared for optional data providers
- Kiosk cursor hidden across the map and controls
- Initial branded loading screen created
- Project workspace created under `/opt/piradar`

## Clean implementation

The repository now contains the initial application scaffold: a Python service, mock and adsb.lol aircraft-data providers, a browser radar UI, configuration, tests and deployment support.
The deployment scaffold incorporates the proven Cage, Wayland and Chromium kiosk route from Spike 001.

## Outstanding

- Confirm touch calibration at all four display edges
- Confirm production usage expectations with the adsb.lol operator
- Configure production autostart and kiosk session
- Add the custom boot splash
- Add watchdog and offline recovery validation
- Implement and explicitly enable optional paid-provider adapters only if a service is selected later
- Package and test a reproducible release image

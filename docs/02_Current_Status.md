# Current Status

## Proven on the prototype

- Raspberry Pi OS installed
- Raspberry Pi Connect working
- 5-inch 800×480 HDMI display working
- Chromium kiosk launch proven
- Initial branded loading screen created
- Project workspace created under `/opt/piradar`

## Clean implementation

The repository now contains the initial application scaffold: a Python service, mock and adsb.lol aircraft-data providers, a browser radar UI, configuration, tests and deployment support.
The deployment scaffold incorporates the proven Cage, Wayland and Chromium kiosk route from Spike 001.

## Outstanding

- Validate and calibrate touch input on the target hardware
- Confirm production usage expectations with the adsb.lol operator
- Configure production autostart and kiosk session
- Add the custom boot splash
- Add watchdog and offline recovery validation
- Build the settings UI
- Package and test a reproducible release image

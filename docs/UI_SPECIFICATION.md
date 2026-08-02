# UI Specification

## Design intent

The display should feel like a purpose-built instrument: dark, high-contrast, restrained and legible at arm's length. It should borrow the clarity of aviation displays without pretending to be certified equipment.

## Reference viewport

Design and acceptance testing target 800×480 landscape first. Interactive controls have a minimum 44-pixel touch target. The primary radar view must not require scrolling.

## Main view

- Top status rail: product identity, provider state and local UTC time
- Full-screen geographic map centred on the configured home location
- Oriented aircraft symbols placed over towns, roads and other geographic context
- Home control and large zoom controls suitable for touch
- Selected aircraft opens a compact identity, route and telemetry card over the map
- Display options provide colour/dark map styles, altitude/amber aircraft colours and optional callsign labels
- Data Services settings accept optional provider credentials and show configured status without redisplaying secrets
- Traffic filters cover aircraft class and altitude, with a clear shown/total count
- Airliners, light aircraft, rotorcraft, gliders and other traffic use distinct silhouettes
- A selected aircraft develops a green local trail from positions observed during the current kiosk session
- Toggleable airport markers show nearby IATA or ICAO codes without obscuring the base map
- Bottom rail: visible aircraft count, configured range and data caveat

The default zoom deliberately shows a useful local subset rather than forcing the entire configured query radius onto one screen. Users can pan, zoom and return home. All loaded aircraft remain available but filters can temporarily hide classes or altitude bands. Aircraft identity and route enrichment is loaded only after selection and explicitly identifies unavailable or uncertain data. Display preferences and filters persist locally in the kiosk browser. Live views show aircraft, map and airport-data attribution. The kiosk hides the pointer across the map and controls; touch feedback and focus styling provide interaction cues instead.

## States

- **Starting:** branded field with an initialization message
- **Live:** current tracks and a positive but unobtrusive status
- **Stale:** last snapshot may remain visible but is clearly marked
- **Offline/error:** explanation and automatic retry status
- **No traffic:** valid connected state with a deliberate empty-radar message
- **Map unavailable:** aircraft status remains explicit even if geographic tiles cannot load

## Design tokens

- Background: near-black navy
- Primary plotting colour: altitude scale from green through cyan and amber to coral, with an amber-only option
- Secondary text: muted blue-grey
- Attention: amber; fault: coral red
- Type: system sans-serif for UI, tabular numerals for telemetry

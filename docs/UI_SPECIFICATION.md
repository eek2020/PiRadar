# UI Specification

## Design intent

The display should feel like a purpose-built instrument: dark, high-contrast, restrained and legible at arm's length. It should borrow the clarity of aviation displays without pretending to be certified equipment.

## Reference viewport

Design and acceptance testing target 800×480 landscape first. Interactive controls have a minimum 44-pixel touch target. The primary radar view must not require scrolling.

## Main view

- Top status rail: product identity, provider state and local UTC time
- Left radar field: range rings, cardinal labels, home marker and oriented aircraft symbols
- Right traffic rail: eight nearest aircraft with altitude and distance as large touch targets
- Selected aircraft replaces the traffic rail with a focused telemetry panel and is labelled on the radar
- Bottom rail: visible aircraft count, configured range and data caveat

All in-range aircraft remain represented. When traffic is dense, compact directional symbols preserve the overall airspace picture without turning callsigns into an unreadable cloud. Identities live in the nearest-traffic rail; selecting any symbol or row opens its detail and labels it on the radar. Live data views include the provider's required attribution in the bottom rail.

## States

- **Starting:** branded field with an initialization message
- **Live:** current tracks and a positive but unobtrusive status
- **Stale:** last snapshot may remain visible but is clearly marked
- **Offline/error:** explanation and automatic retry status
- **No traffic:** valid connected state with a deliberate empty-radar message

## Design tokens

- Background: near-black navy
- Primary plotting colour: phosphor mint
- Secondary text: muted blue-grey
- Attention: amber; fault: coral red
- Type: system sans-serif for UI, tabular numerals for telemetry

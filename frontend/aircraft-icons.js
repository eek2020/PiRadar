// Aircraft map silhouettes, one per icon family chosen by the backend
// (backend/piradar/aircraft_icons.py). Original artwork on a 32x32 grid,
// nose up; outlines are mirror-symmetric. Sizes are on-screen pixels, so a
// C-17 draws larger than a Cessna.
(function () {
  const FIXED_WING = {
  heavy4: {
    size: 42,
    body: "M16 1 L17.1 2.6 L17.3 11 L30.5 19.5 L30.5 21 L17.3 16.8 L17.1 25.5 L23 29 L23 30.5 L16.8 29.6 L16 31.2 L15.2 29.6 L9 30.5 L9 29 L14.9 25.5 L14.7 16.8 L1.5 21 L1.5 19.5 L14.7 11 L14.9 2.6 Z",
    extra: "M20.7 14.6 a0.9 1.9 0 1 0 1.8 0 a0.9 1.9 0 1 0 -1.8 0 Z M9.5 14.6 a0.9 1.9 0 1 0 1.8 0 a0.9 1.9 0 1 0 -1.8 0 Z M25.3 17.6 a0.9 1.9 0 1 0 1.8 0 a0.9 1.9 0 1 0 -1.8 0 Z M4.9 17.6 a0.9 1.9 0 1 0 1.8 0 a0.9 1.9 0 1 0 -1.8 0 Z"
  },
  widebody: {
    size: 38,
    body: "M16 1 L17.3 2.8 L17.5 11.5 L30 19 L30 20.6 L17.5 16.8 L17.3 25.5 L23 29 L23 30.4 L16.8 29.6 L16 31 L15.2 29.6 L9 30.4 L9 29 L14.7 25.5 L14.5 16.8 L2 20.6 L2 19 L14.5 11.5 L14.7 2.8 Z",
    extra: "M21.3 15.4 a1.1 2.1 0 1 0 2.2 0 a1.1 2.1 0 1 0 -2.2 0 Z M8.5 15.4 a1.1 2.1 0 1 0 2.2 0 a1.1 2.1 0 1 0 -2.2 0 Z"
  },
  narrowbody: {
    size: 32,
    body: "M16 1.5 L17 3 L17.1 12 L28.5 18.5 L28.5 20 L17.1 17 L17 25.5 L22 28.5 L22 30 L16.7 29.4 L16 30.8 L15.3 29.4 L10 30 L10 28.5 L15 25.5 L14.9 17 L3.5 20 L3.5 18.5 L14.9 12 L15 3 Z",
    extra: "M20.5 14.9 a0.9 1.8 0 1 0 1.8 0 a0.9 1.8 0 1 0 -1.8 0 Z M9.7 14.9 a0.9 1.8 0 1 0 1.8 0 a0.9 1.8 0 1 0 -1.8 0 Z"
  },
  airlifter: {
    size: 38,
    body: "M16 1.4 L17.6 3.4 L17.7 10.6 L30.8 11.2 L30.8 14.2 L17.7 14.8 L17.6 24 L24 27.4 L24 29.4 L17 28.8 L16 31 L15 28.8 L8 29.4 L8 27.4 L14.4 24 L14.3 14.8 L1.2 14.2 L1.2 11.2 L14.3 10.6 L14.4 3.4 Z",
    extra: "M19.65 10.8 a0.95 2.4 0 1 0 1.9 0 a0.95 2.4 0 1 0 -1.9 0 Z M10.45 10.8 a0.95 2.4 0 1 0 1.9 0 a0.95 2.4 0 1 0 -1.9 0 Z M24.25 11.2 a0.95 2.4 0 1 0 1.9 0 a0.95 2.4 0 1 0 -1.9 0 Z M5.85 11.2 a0.95 2.4 0 1 0 1.9 0 a0.95 2.4 0 1 0 -1.9 0 Z",
    props: "M18.5 8.2 H22.7 M9.3 8.2 H13.5 M23.1 8.2 H27.3 M4.7 8.2 H8.9"
  },
  regional: {
    size: 30,
    body: "M16 2 L17.2 3.8 L17.2 12 L29.5 12.6 L29.5 15.2 L17.2 15.8 L17 25 L21.8 26.6 L21.8 28.4 L16.7 28.2 L16 29.6 L15.3 28.2 L10.2 28.4 L10.2 26.6 L15 25 L14.8 15.8 L2.5 15.2 L2.5 12.6 L14.8 12 L14.8 3.8 Z",
    extra: "M19.9 9 H22.1 V16.4 H19.9 Z M9.9 9 H12.1 V16.4 H9.9 Z",
    props: "M18.4 8.6 H23.6 M8.4 8.6 H13.6"
  },
  twinprop: {
    size: 26,
    body: "M16 2 L17.2 3.8 L17.2 12 L29.5 12.6 L29.5 15.2 L17.2 15.8 L17 25 L21.8 26.6 L21.8 28.4 L16.7 28.2 L16 29.6 L15.3 28.2 L10.2 28.4 L10.2 26.6 L15 25 L14.8 15.8 L2.5 15.2 L2.5 12.6 L14.8 12 L14.8 3.8 Z",
    extra: "M19.9 9 H22.1 V16.4 H19.9 Z M9.9 9 H12.1 V16.4 H9.9 Z",
    props: "M18.4 8.6 H23.6 M8.4 8.6 H13.6"
  },
  bizjet: {
    size: 27,
    body: "M16 2 L16.9 3.8 L17 13 L26.5 19.5 L26.5 21 L17 18 L17 25 L21.5 28 L21.5 29.4 L16.6 29 L16 30 L15.4 29 L10.5 29.4 L10.5 28 L15 25 L15 18 L5.5 21 L5.5 19.5 L15 13 L15.1 3.8 Z",
    extra: "M17.9 22.4 a1 2.1 0 1 0 2 0 a1 2.1 0 1 0 -2 0 Z M12.1 22.4 a1 2.1 0 1 0 2 0 a1 2.1 0 1 0 -2 0 Z"
  },
  delta: {
    size: 29,
    body: "M16 0.6 L16.8 4.2 L17.2 7.4 L21 9.6 L21 10.8 L17.6 10.4 L17.9 13 L28.4 25.2 L28.4 26.8 L18 26.6 L17.2 29.8 L16 30.6 L14.8 29.8 L14 26.6 L3.6 26.8 L3.6 25.2 L14.1 13 L14.4 10.4 L11 10.8 L11 9.6 L14.8 7.4 L15.2 4.2 Z"
  },
  fighter: {
    size: 29,
    body: "M16 0.8 L16.8 4.5 L17.3 9.5 L18 12.5 L27.5 19.5 L27.5 21.5 L18.4 20.8 L18.4 23.5 L23 27.8 L23 29.8 L17.2 28.6 L16 30.6 L14.8 28.6 L9 29.8 L9 27.8 L13.6 23.5 L13.6 20.8 L4.5 21.5 L4.5 19.5 L14 12.5 L14.7 9.5 L15.2 4.5 Z"
  },
  light: {
    size: 26,
    body: "M16 4 L17.4 5.4 L17.5 9 L29.5 9.2 L29.5 13.2 L17.5 13.4 L16.9 22.4 L21.8 23.2 L21.8 25.6 L16.6 25.4 L16 26.6 L15.4 25.4 L10.2 25.6 L10.2 23.2 L15.1 22.4 L14.5 13.4 L2.5 13.2 L2.5 9.2 L14.5 9 L14.6 5.4 Z",
    props: "M12.6 3.6 H19.4"
  },
  glider: {
    size: 30,
    body: "M16 4 L16.6 5.6 L16.7 12 L31.4 13 L31.4 14.4 L16.7 15 L16.3 26 L19.2 26.6 L19.2 27.8 L16.2 27.6 L16 28.6 L15.8 27.6 L12.8 27.8 L12.8 26.6 L15.7 26 L15.3 15 L0.6 14.4 L0.6 13 L15.3 12 L15.4 5.6 Z"
  },
  drone: {
    size: 28,
    body: "M16 4.5 L16.9 6.2 L17 12.2 L30.6 12.8 L30.6 14.2 L17 14.8 L16.8 23.8 L20.6 27.4 L20.2 28.2 L16.4 26.4 L16 27.2 L15.6 26.4 L11.8 28.2 L11.4 27.4 L15.2 23.8 L15 14.8 L1.4 14.2 L1.4 12.8 L15 12.2 L15.1 6.2 Z",
    props: "M13.4 28.4 H18.6"
  },
  tiltrotor: {
    size: 32,
    body: "M16 3 L17.2 5 L17.3 12.4 L24.4 12.4 L24.4 15.6 L17.3 15.6 L17.1 25 L21 26 L21 28 L16.6 28 L16 29.2 L15.4 28 L11 28 L11 26 L14.9 25 L14.7 15.6 L7.6 15.6 L7.6 12.4 L14.7 12.4 L14.8 5 Z",
    extra: "M24.2 10.2 H26.8 V17.6 H24.2 Z M5.2 10.2 H7.8 V17.6 H5.2 Z"
  },
  unknown: {
    size: 26,
    body: "M16 3 L26 27 L16 22 L6 27 Z"
  },
  };

  const ROTORCRAFT = {
    helicopter: {
      size: 28,
      markup: `
        <path class="airframe" d="M16 7c-3 0-5 3-5 7v6c0 3 2 5 4 6v3h2v-3c2-1 4-3 4-6v-6c0-4-2-7-5-7z"/>
        <path class="airframe" d="M15 25h2v4h5v1H10v-1h5z"/>
        <path class="rotor" d="M3 10h26M16 2v16"/>
        <circle class="hub" cx="16" cy="10" r="2"/>`,
    },
    tandem: {
      size: 34,
      markup: `
        <path class="airframe" d="M13.6 5.5c0-2 1.1-3 2.4-3s2.4 1 2.4 3v21c0 2-1.1 3-2.4 3s-2.4-1-2.4-3z"/>
        <path class="rotor" d="M8.5 1.5 23.5 12.5M23.5 1.5 8.5 12.5M8.5 19.5 23.5 30.5M23.5 19.5 8.5 30.5"/>
        <circle class="hub" cx="16" cy="7" r="1.7"/>
        <circle class="hub" cx="16" cy="25" r="1.7"/>`,
    },
  };

  // Which Filters button each family belongs to.
  const FILTER_CLASS = {
    heavy4: "airliner", widebody: "airliner", narrowbody: "airliner", regional: "airliner",
    twinprop: "light", bizjet: "light", light: "light",
    helicopter: "rotorcraft", tandem: "rotorcraft", tiltrotor: "rotorcraft",
    glider: "glider",
  };

  function family(track) {
    const name = track.icon || "unknown";
    return FIXED_WING[name] || ROTORCRAFT[name] ? name : "unknown";
  }

  function markup(name) {
    if (ROTORCRAFT[name]) return ROTORCRAFT[name].markup;
    const shape = FIXED_WING[name];
    let svg = `<path class="airframe" d="${shape.body}"/>`;
    if (shape.extra) svg += `<path class="airframe engines" d="${shape.extra}"/>`;
    if (shape.props) svg += `<path class="prop" d="${shape.props}"/>`;
    if (name === "tiltrotor") svg += '<circle class="rotor-disc" cx="25.5" cy="13.9" r="5.4"/><circle class="rotor-disc" cx="6.5" cy="13.9" r="5.4"/>';
    return svg;
  }

  window.PiRadarIcons = {
    family,
    markup,
    size: (name) => (FIXED_WING[name] || ROTORCRAFT[name]).size,
    filterClass: (name) => FILTER_CLASS[name] || "other",
  };
})();

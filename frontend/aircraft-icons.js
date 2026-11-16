// Draw aircraft with the silhouette the backend chose from the ICAO type code
// (backend/piradar/aircraft_icons.py). Shapes come from aircraft-shapes.js,
// generated from assets/aircraft-icons (see its README for sources and
// licences). Sizes are on-screen pixels, so a C-17 draws larger than a Cessna.
(function () {
  const SIZE = {
    a380: 44, b747: 42, c17: 40, a340: 40, b777: 40, a400m: 38, a330: 38, b787: 38,
    md11: 38, b767: 36, c130: 36, a5: 36, a4: 34,
    a320: 32, b737: 32, a3: 32, e195: 30, f100: 30, dh8a: 30, erj: 28, crjx: 28,
    glf5: 28, fa7x: 28, learjet: 26, a2: 26, beechcraft: 26, cessna: 24, a1: 24,
    typhoon: 30, rafale: 30, f35: 30, fighter: 30, hawk: 28, a6: 30,
    chinook: 36, merlin: 34, apache: 32, osprey: 34, a7: 30,
    b1: 30, a0: 28,
  };

  // Which Filters button each icon belongs to; anything unlisted is "other".
  const FILTER_CLASS = {};
  const classes = {
    airliner: ["a380", "b747", "a340", "b777", "a330", "b787", "md11", "b767", "a320", "b737",
      "e195", "f100", "dh8a", "erj", "crjx", "a3", "a4", "a5"],
    light: ["glf5", "fa7x", "learjet", "beechcraft", "cessna", "a1", "a2"],
    rotorcraft: ["a7", "apache", "merlin", "chinook", "osprey"],
    glider: ["b1"],
  };
  Object.entries(classes).forEach(([filter, icons]) => icons.forEach((icon) => { FILTER_CLASS[icon] = filter; }));

  function family(track) {
    const name = track.icon || "a0";
    return window.PiRadarShapes[name] ? name : "a0";
  }

  window.PiRadarIcons = {
    family,
    markup: (name) => `<g class="airframe">${window.PiRadarShapes[name].markup}</g>`,
    viewBox: (name) => window.PiRadarShapes[name].viewBox,
    size: (name) => SIZE[name] || 30,
    filterClass: (name) => FILTER_CLASS[name] || "other",
  };
})();

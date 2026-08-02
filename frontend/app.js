const state = {
  config: null,
  map: null,
  tileLayer: null,
  homeMarker: null,
  airportLayer: null,
  airports: [],
  markers: new Map(),
  history: new Map(),
  selectedTrail: null,
  selectedHex: null,
  latest: [],
  preferences: {
    mapStyle: "colour",
    aircraftColour: "altitude",
    showLabels: false,
  },
  filters: {
    aircraftType: "all",
    altitudeBand: "all",
    showAirports: true,
  },
};

const elements = {
  connection: document.querySelector("#connection"),
  clock: document.querySelector("#clock"),
  message: document.querySelector("#message"),
  count: document.querySelector("#aircraft-count"),
  countLabel: document.querySelector("#aircraft-count-label"),
  range: document.querySelector("#range"),
  detail: document.querySelector("#detail"),
  options: document.querySelector("#options"),
  optionsControl: document.querySelector("#options-control"),
  filters: document.querySelector("#filters"),
  filterControl: document.querySelector("#filter-control"),
  showLabels: document.querySelector("#show-labels"),
  showAirports: document.querySelector("#show-airports"),
  attribution: document.querySelector("#attribution"),
};

function setConnection(label, kind) {
  elements.connection.dataset.state = kind;
  elements.connection.lastElementChild.textContent = label;
}

function initializeMap() {
  state.map = L.map("map", {
    attributionControl: true,
    doubleClickZoom: true,
    scrollWheelZoom: false,
    zoomControl: false,
    zoomSnap: 0.5,
  });
  L.control.zoom({ position: "bottomleft" }).addTo(state.map);
  state.tileLayer = L.tileLayer(state.config.map_tile_url, {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    maxZoom: 18,
  }).addTo(state.map);

  state.homeMarker = L.marker(
    [state.config.home_latitude, state.config.home_longitude],
    {
      icon: L.divIcon({ className: "home-marker", html: "", iconSize: [18, 18] }),
      interactive: false,
      keyboard: false,
      zIndexOffset: 1000,
    },
  ).addTo(state.map);
  state.airportLayer = L.layerGroup().addTo(state.map);
  state.map.on("click", clearSelection);
  state.map.on("zoomend", renderAirports);
  centerHome();
}

function centerHome() {
  const latDelta = state.config.range_nm / 60;
  const lonDelta = latDelta / Math.max(Math.cos(state.config.home_latitude * Math.PI / 180), 0.2);
  state.map.fitBounds(
    [
      [state.config.home_latitude - latDelta, state.config.home_longitude - lonDelta],
      [state.config.home_latitude + latDelta, state.config.home_longitude + lonDelta],
    ],
    { animate: false, padding: [18, 18] },
  );
  state.map.setZoom(Math.min(state.map.getZoom() + 1, 13), { animate: false });
}

function distanceFromHome(track) {
  const latNm = (track.latitude - state.config.home_latitude) * 60;
  const lonNm = (track.longitude - state.config.home_longitude) * 60 * Math.cos(state.config.home_latitude * Math.PI / 180);
  return Math.hypot(latNm, lonNm);
}

function distanceFromHomeCoordinates(latitude, longitude) {
  return distanceFromHome({ latitude, longitude });
}

function altitudeColour(track) {
  if (state.preferences.aircraftColour === "amber") return "#ffc56e";
  if (track.altitude_ft <= 0) return "#aeb8b6";
  if (track.altitude_ft < 10000) return "#65e5a5";
  if (track.altitude_ft < 25000) return "#65cfff";
  if (track.altitude_ft < 35000) return "#ffc45f";
  return "#ff7f78";
}

function aircraftClass(track) {
  const type = (track.aircraft_type || "").toUpperCase();
  const category = (track.category || "").toUpperCase();
  if (category === "A7" || /^(H|R22|R44|EC|AS|B06|S76|AW)/.test(type)) return "rotorcraft";
  if (category === "B1" || /^(GLID|ASW|DG|LS|SZD|VENT|DUOD|JANU)/.test(type)) return "glider";
  if (["A3", "A4", "A5"].includes(category) || /^(A3|A2[013]|B7|B8|B9|E1|E2|CRJ|DH8|AT7)/.test(type)) return "airliner";
  if (["A1", "A2", "B4"].includes(category) || /^(C1|C2|P28|PA|BE|DA|SR|M20|TB|PC)/.test(type)) return "light";
  return "other";
}

function aircraftPath(kind) {
  if (kind === "glider") return "M15 2 L16 14 L29 17 L29 19 L16 17 L16 25 L20 28 L20 29 L15 27 L10 29 L10 28 L14 25 L14 17 L1 19 L1 17 L14 14 Z";
  if (kind === "rotorcraft") return "M4 7 L14 7 L14 3 L16 3 L16 7 L27 7 L27 9 L17 9 L20 14 L20 20 L26 24 L26 26 L18 23 L16 28 L13 28 L12 22 L7 21 L4 17 L5 12 L12 10 L4 9 Z";
  if (kind === "light") return "M15 2 L17 12 L26 16 L26 18 L17 17 L17 23 L22 26 L22 28 L15 26 L8 28 L8 26 L13 23 L13 17 L4 18 L4 16 L13 12 Z";
  if (kind === "other") return "M15 2 L18 12 L26 16 L26 19 L18 17 L18 24 L21 27 L21 29 L15 26 L9 29 L9 27 L12 24 L12 17 L4 19 L4 16 L12 12 Z";
  return "M15 1 L18 11 L28 16 L28 19 L18 17 L18 24 L22 27 L22 29 L15 26 L8 29 L8 27 L12 24 L12 17 L2 19 L2 16 L12 11 Z";
}

function aircraftIcon(track, selected) {
  const rotation = Number.isFinite(track.track_deg) ? track.track_deg : 0;
  const kind = aircraftClass(track);
  const label = state.preferences.showLabels
    ? `<span class="aircraft-label">${escapeHtml(track.callsign || track.hex)}</span>`
    : "";
  return L.divIcon({
    className: `aircraft-marker ${kind}${selected ? " selected" : ""}`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    html: `<svg viewBox="0 0 30 30" aria-hidden="true" style="--aircraft-color:${altitudeColour(track)};transform:rotate(${rotation}deg)"><path d="${aircraftPath(kind)}"/></svg>${label}`,
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function recordHistory(aircraft) {
  aircraft.forEach((track) => {
    const points = state.history.get(track.hex) || [];
    const previous = points.at(-1);
    if (!previous || Math.abs(previous[0] - track.latitude) > 0.00015 || Math.abs(previous[1] - track.longitude) > 0.00015) {
      points.push([track.latitude, track.longitude]);
      if (points.length > 240) points.shift();
      state.history.set(track.hex, points);
    }
  });
}

function passesFilters(track) {
  if (state.filters.aircraftType !== "all" && aircraftClass(track) !== state.filters.aircraftType) return false;
  if (state.filters.altitudeBand === "low" && track.altitude_ft >= 10000) return false;
  if (state.filters.altitudeBand === "mid" && (track.altitude_ft < 10000 || track.altitude_ft >= 25000)) return false;
  if (state.filters.altitudeBand === "high" && track.altitude_ft < 25000) return false;
  return true;
}

function updateSelectedTrail() {
  if (state.selectedTrail) {
    state.selectedTrail.remove();
    state.selectedTrail = null;
  }
  if (!state.selectedHex) return;
  const points = state.history.get(state.selectedHex) || [];
  if (points.length < 2) return;
  state.selectedTrail = L.polyline(points, {
    color: "#35ef35",
    weight: 4,
    opacity: 0.88,
    lineCap: "round",
    lineJoin: "round",
  }).addTo(state.map);
}

function renderAircraft(aircraft) {
  state.latest = aircraft;
  recordHistory(aircraft);
  const visibleAircraft = aircraft.filter(passesFilters);
  const incoming = new Set();

  visibleAircraft.forEach((track) => {
    incoming.add(track.hex);
    const selected = track.hex === state.selectedHex;
    let marker = state.markers.get(track.hex);
    if (!marker) {
      marker = L.marker([track.latitude, track.longitude], {
        icon: aircraftIcon(track, selected),
        keyboard: true,
        riseOnHover: true,
        title: track.callsign || track.hex,
      });
      marker.on("click", () => selectAircraft(track.hex));
      marker.addTo(state.map);
      state.markers.set(track.hex, marker);
    } else {
      marker.setLatLng([track.latitude, track.longitude]);
      marker.setIcon(aircraftIcon(track, selected));
    }
    marker.setZIndexOffset(selected ? 2000 : Math.max(0, 50000 - track.altitude_ft));
  });

  state.markers.forEach((marker, hex) => {
    if (!incoming.has(hex)) {
      marker.remove();
      state.markers.delete(hex);
    }
  });

  const filtering = visibleAircraft.length !== aircraft.length;
  elements.count.textContent = filtering ? `${visibleAircraft.length}/${aircraft.length}` : String(aircraft.length);
  elements.countLabel.textContent = filtering ? " shown" : " aircraft";
  elements.message.hidden = visibleAircraft.length > 0;
  if (!aircraft.length) elements.message.textContent = "No aircraft in range";
  else if (!visibleAircraft.length) elements.message.textContent = "No aircraft match filters";

  if (state.selectedHex) {
    const selected = visibleAircraft.find((track) => track.hex === state.selectedHex);
    if (selected) populateDetail(selected);
    else clearSelection();
  }
  updateSelectedTrail();
}

function selectAircraft(hex) {
  state.selectedHex = hex;
  const selected = state.latest.find((track) => track.hex === hex);
  if (!selected) return;
  closeOptions();
  closeFilters();
  populateDetail(selected, true);
  elements.detail.hidden = false;
  renderAircraft(state.latest);
  loadAircraftDetails(hex);
}

function clearSelection() {
  if (!state.selectedHex && elements.detail.hidden) return;
  state.selectedHex = null;
  elements.detail.hidden = true;
  updateSelectedTrail();
  renderAircraft(state.latest);
}

function populateDetail(track, resetEnrichment = false) {
  document.querySelector("#detail-callsign").textContent = track.callsign || "Unknown";
  document.querySelector("#detail-altitude").textContent = track.altitude_ft <= 0 ? "Ground" : `${track.altitude_ft.toLocaleString()} ft`;
  document.querySelector("#detail-speed").textContent = `${track.ground_speed_kt} kt`;
  document.querySelector("#detail-distance").textContent = `${distanceFromHome(track).toFixed(1)} NM`;
  document.querySelector("#detail-track").textContent = `${String(track.track_deg).padStart(3, "0")}°`;
  document.querySelector("#detail-vertical").textContent = `${track.vertical_rate_fpm > 0 ? "+" : ""}${track.vertical_rate_fpm.toLocaleString()} fpm`;
  document.querySelector("#detail-hex").textContent = track.hex;
  document.querySelector("#detail-squawk").textContent = track.squawk || "—";
  if (resetEnrichment) {
    document.querySelector("#detail-registration").textContent = track.registration || "Registration unavailable";
    document.querySelector("#detail-type").textContent = track.aircraft_type || "Aircraft type unavailable";
    document.querySelector("#detail-operator").textContent = "Operator unavailable";
    document.querySelector("#detail-origin").textContent = "—";
    document.querySelector("#detail-origin-name").textContent = "Origin unavailable";
    document.querySelector("#detail-destination").textContent = "—";
    document.querySelector("#detail-destination-name").textContent = "Destination unavailable";
    document.querySelector("#detail-lookup").textContent = "Looking up aircraft and route…";
  }
}

async function loadAircraftDetails(hex, attempt = 0) {
  try {
    const response = await fetch(`/api/aircraft/${encodeURIComponent(hex)}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const details = await response.json();
    if (state.selectedHex !== hex) return;

    const typeName = [details.manufacturer, details.model].filter(Boolean).join(" ");
    document.querySelector("#detail-type").textContent = typeName || details.type_code || "Aircraft type unavailable";
    document.querySelector("#detail-registration").textContent = details.registration || "Registration unavailable";
    document.querySelector("#detail-operator").textContent = details.operator || "Operator unavailable";

    if (details.route) {
      document.querySelector("#detail-origin").textContent = details.route.origin.code || "—";
      document.querySelector("#detail-origin-name").textContent = details.route.origin.location || details.route.origin.name || "Origin";
      document.querySelector("#detail-destination").textContent = details.route.destination.code || "—";
      document.querySelector("#detail-destination-name").textContent = details.route.destination.location || details.route.destination.name || "Destination";
      document.querySelector("#detail-lookup").textContent = details.route.plausible
        ? "Route matched to the aircraft’s current position"
        : "Published route · current-position match uncertain";
    } else {
      document.querySelector("#detail-lookup").textContent = attempt < 2
        ? "Route not found yet · retrying…"
        : "Route unavailable for this callsign";
      if (attempt < 2) {
        window.setTimeout(() => {
          if (state.selectedHex === hex) loadAircraftDetails(hex, attempt + 1);
        }, 25000);
      }
    }
  } catch (error) {
    console.error("Aircraft detail lookup failed", error);
    if (state.selectedHex === hex) {
      document.querySelector("#detail-lookup").textContent = attempt < 2
        ? "Detail service unavailable · retrying…"
        : "Additional details temporarily unavailable";
      if (attempt < 2) {
        window.setTimeout(() => {
          if (state.selectedHex === hex) loadAircraftDetails(hex, attempt + 1);
        }, 25000);
      }
    }
  }
}

function airportIcon(airport) {
  const code = airport.iata || airport.icao;
  return L.divIcon({
    className: `airport-marker ${airport.type}`,
    iconSize: [30, 38],
    iconAnchor: [15, 34],
    html: `<span class="pin"></span><span class="tower"></span><span class="code">${escapeHtml(code)}</span>`,
  });
}

function renderAirports() {
  if (!state.airportLayer) return;
  state.airportLayer.clearLayers();
  if (!state.filters.showAirports) return;
  const includeSmall = state.map.getZoom() >= 9;
  state.airports
    .filter((airport) => includeSmall || airport.type !== "small")
    .forEach((airport) => {
      L.marker([airport.latitude, airport.longitude], {
        icon: airportIcon(airport),
        keyboard: false,
        title: `${airport.iata || airport.icao} · ${airport.name}`,
        zIndexOffset: -500,
      }).addTo(state.airportLayer);
    });
}

async function loadAirports() {
  try {
    const response = await fetch("/data/airports-gb.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const airports = await response.json();
    state.airports = airports.filter((airport) => (
      distanceFromHomeCoordinates(airport.latitude, airport.longitude) <= state.config.range_nm * 1.4
    ));
    state.map.attributionControl.addAttribution('Airports: <a href="https://ourairports.com/data/">OurAirports</a>');
    renderAirports();
  } catch (error) {
    console.warn("Airport layer unavailable", error);
  }
}

function loadPreferences() {
  try {
    const saved = JSON.parse(window.localStorage.getItem("piradar-display") || "{}");
    if (["colour", "dark"].includes(saved.mapStyle)) state.preferences.mapStyle = saved.mapStyle;
    if (["altitude", "amber"].includes(saved.aircraftColour)) state.preferences.aircraftColour = saved.aircraftColour;
    if (typeof saved.showLabels === "boolean") state.preferences.showLabels = saved.showLabels;
  } catch (error) {
    console.warn("Could not load display preferences", error);
  }
}

function loadFilters() {
  try {
    const saved = JSON.parse(window.localStorage.getItem("piradar-filters") || "{}");
    if (["all", "airliner", "light", "rotorcraft", "glider", "other"].includes(saved.aircraftType)) state.filters.aircraftType = saved.aircraftType;
    if (["all", "low", "mid", "high"].includes(saved.altitudeBand)) state.filters.altitudeBand = saved.altitudeBand;
    if (typeof saved.showAirports === "boolean") state.filters.showAirports = saved.showAirports;
  } catch (error) {
    console.warn("Could not load filters", error);
  }
}

function filtersActive() {
  return state.filters.aircraftType !== "all" || state.filters.altitudeBand !== "all";
}

function applyFilters() {
  document.querySelectorAll(".choice-grid button").forEach((button) => {
    const option = button.parentElement.dataset.filter;
    button.setAttribute("aria-pressed", String(state.filters[option] === button.dataset.value));
  });
  elements.showAirports.checked = state.filters.showAirports;
  elements.filterControl.dataset.active = String(filtersActive());
  try {
    window.localStorage.setItem("piradar-filters", JSON.stringify(state.filters));
  } catch (error) {
    console.warn("Could not save filters", error);
  }
  if (state.map) {
    renderAircraft(state.latest);
    renderAirports();
  }
}

function applyPreferences() {
  document.querySelector(".map-panel").dataset.mapStyle = state.preferences.mapStyle;
  document.querySelectorAll(".choice-row button").forEach((button) => {
    const option = button.parentElement.dataset.option;
    button.setAttribute("aria-pressed", String(state.preferences[option] === button.dataset.value));
  });
  elements.showLabels.checked = state.preferences.showLabels;
  try {
    window.localStorage.setItem("piradar-display", JSON.stringify(state.preferences));
  } catch (error) {
    console.warn("Could not save display preferences", error);
  }
  if (state.map) renderAircraft(state.latest);
}

function openOptions() {
  clearSelection();
  closeFilters();
  elements.options.hidden = false;
  elements.optionsControl.setAttribute("aria-expanded", "true");
}

function closeOptions() {
  elements.options.hidden = true;
  elements.optionsControl.setAttribute("aria-expanded", "false");
}

function openFilters() {
  clearSelection();
  closeOptions();
  elements.filters.hidden = false;
  elements.filterControl.setAttribute("aria-expanded", "true");
}

function closeFilters() {
  elements.filters.hidden = true;
  elements.filterControl.setAttribute("aria-expanded", "false");
}

async function updateAircraft() {
  try {
    const response = await fetch("/api/aircraft", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const snapshot = await response.json();
    renderAircraft(snapshot.aircraft);
    elements.attribution.textContent = snapshot.source === "adsb.lol"
      ? "Data © adsb.lol · ODbL · not for navigation"
      : "Informational display · not for navigation";
    if (snapshot.status === "stale") {
      setConnection("Stale data", "error");
    } else if (snapshot.status === "offline") {
      setConnection("Provider offline", "error");
      if (!snapshot.aircraft.length) {
        elements.message.hidden = false;
        elements.message.textContent = "Provider unavailable · retrying";
      }
    } else {
      setConnection(snapshot.source === "mock" ? "Mock data" : "Live", "live");
    }
  } catch (error) {
    console.error("Aircraft update failed", error);
    setConnection("Reconnecting", "error");
    elements.message.hidden = false;
    elements.message.textContent = "Data unavailable · retrying";
  }
}

async function start() {
  try {
    const response = await fetch("/api/config", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.config = await response.json();
    elements.range.textContent = String(state.config.range_nm);
    loadPreferences();
    loadFilters();
    applyPreferences();
    applyFilters();
    initializeMap();
    loadAirports();
    await updateAircraft();
    window.setInterval(updateAircraft, 3000);
  } catch (error) {
    console.error("PiRadar startup failed", error);
    setConnection("Offline", "error");
    elements.message.textContent = "Service unavailable · retrying";
    window.setTimeout(start, 3000);
  }
}

document.querySelector("#close-detail").addEventListener("click", clearSelection);
document.querySelector("#home-control").addEventListener("click", centerHome);
elements.optionsControl.addEventListener("click", () => elements.options.hidden ? openOptions() : closeOptions());
document.querySelector("#close-options").addEventListener("click", closeOptions);
elements.filterControl.addEventListener("click", () => elements.filters.hidden ? openFilters() : closeFilters());
document.querySelector("#close-filters").addEventListener("click", closeFilters);
document.querySelectorAll(".choice-row button").forEach((button) => {
  button.addEventListener("click", () => {
    state.preferences[button.parentElement.dataset.option] = button.dataset.value;
    applyPreferences();
  });
});
elements.showLabels.addEventListener("change", () => {
  state.preferences.showLabels = elements.showLabels.checked;
  applyPreferences();
});
document.querySelectorAll(".choice-grid button").forEach((button) => {
  button.addEventListener("click", () => {
    state.filters[button.parentElement.dataset.filter] = button.dataset.value;
    applyFilters();
  });
});
elements.showAirports.addEventListener("change", () => {
  state.filters.showAirports = elements.showAirports.checked;
  applyFilters();
});
document.querySelector("#reset-filters").addEventListener("click", () => {
  state.filters.aircraftType = "all";
  state.filters.altitudeBand = "all";
  applyFilters();
});

window.setInterval(() => {
  elements.clock.textContent = new Date().toISOString().slice(11, 19) + "Z";
}, 1000);

start();

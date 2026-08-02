const state = {
  config: null,
  map: null,
  tileLayer: null,
  homeMarker: null,
  markers: new Map(),
  selectedHex: null,
  latest: [],
  preferences: {
    mapStyle: "colour",
    aircraftColour: "altitude",
    showLabels: false,
  },
};

const elements = {
  connection: document.querySelector("#connection"),
  clock: document.querySelector("#clock"),
  message: document.querySelector("#message"),
  count: document.querySelector("#aircraft-count"),
  range: document.querySelector("#range"),
  detail: document.querySelector("#detail"),
  options: document.querySelector("#options"),
  optionsControl: document.querySelector("#options-control"),
  showLabels: document.querySelector("#show-labels"),
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
  state.map.on("click", clearSelection);
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

function altitudeColour(track) {
  if (state.preferences.aircraftColour === "amber") return "#ffc56e";
  if (track.altitude_ft <= 0) return "#aeb8b6";
  if (track.altitude_ft < 10000) return "#65e5a5";
  if (track.altitude_ft < 25000) return "#65cfff";
  if (track.altitude_ft < 35000) return "#ffc45f";
  return "#ff7f78";
}

function aircraftIcon(track, selected) {
  const rotation = Number.isFinite(track.track_deg) ? track.track_deg : 0;
  const label = state.preferences.showLabels
    ? `<span class="aircraft-label">${escapeHtml(track.callsign || track.hex)}</span>`
    : "";
  return L.divIcon({
    className: `aircraft-marker${selected ? " selected" : ""}`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    html: `<svg viewBox="0 0 30 30" aria-hidden="true" style="--aircraft-color:${altitudeColour(track)};transform:rotate(${rotation}deg)"><path d="M15 1 L18 11 L28 16 L28 19 L18 17 L18 24 L22 27 L22 29 L15 26 L8 29 L8 27 L12 24 L12 17 L2 19 L2 16 L12 11 Z"/></svg>${label}`,
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

function renderAircraft(aircraft) {
  state.latest = aircraft;
  const incoming = new Set();

  aircraft.forEach((track) => {
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

  elements.count.textContent = String(aircraft.length);
  elements.message.hidden = aircraft.length > 0;
  if (!aircraft.length) elements.message.textContent = "No aircraft in range";

  if (state.selectedHex) {
    const selected = aircraft.find((track) => track.hex === state.selectedHex);
    if (selected) populateDetail(selected);
    else clearSelection();
  }
}

function selectAircraft(hex) {
  state.selectedHex = hex;
  const selected = state.latest.find((track) => track.hex === hex);
  if (!selected) return;
  closeOptions();
  populateDetail(selected);
  elements.detail.hidden = false;
  renderAircraft(state.latest);
  loadAircraftDetails(hex);
}

function clearSelection() {
  if (!state.selectedHex && elements.detail.hidden) return;
  state.selectedHex = null;
  elements.detail.hidden = true;
  renderAircraft(state.latest);
}

function populateDetail(track) {
  document.querySelector("#detail-callsign").textContent = track.callsign || "Unknown";
  document.querySelector("#detail-altitude").textContent = track.altitude_ft <= 0 ? "Ground" : `${track.altitude_ft.toLocaleString()} ft`;
  document.querySelector("#detail-speed").textContent = `${track.ground_speed_kt} kt`;
  document.querySelector("#detail-distance").textContent = `${distanceFromHome(track).toFixed(1)} NM`;
  document.querySelector("#detail-track").textContent = `${String(track.track_deg).padStart(3, "0")}°`;
  document.querySelector("#detail-vertical").textContent = `${track.vertical_rate_fpm > 0 ? "+" : ""}${track.vertical_rate_fpm.toLocaleString()} fpm`;
  document.querySelector("#detail-hex").textContent = track.hex;
  document.querySelector("#detail-squawk").textContent = track.squawk || "—";
  document.querySelector("#detail-registration").textContent = track.registration || "Registration unavailable";
  document.querySelector("#detail-type").textContent = track.aircraft_type || "Aircraft type unavailable";
  document.querySelector("#detail-operator").textContent = "Operator unavailable";
  document.querySelector("#detail-origin").textContent = "—";
  document.querySelector("#detail-origin-name").textContent = "Origin unavailable";
  document.querySelector("#detail-destination").textContent = "—";
  document.querySelector("#detail-destination-name").textContent = "Destination unavailable";
  document.querySelector("#detail-lookup").textContent = "Looking up aircraft and route…";
}

async function loadAircraftDetails(hex) {
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
      document.querySelector("#detail-lookup").textContent = "Route unavailable for this callsign";
    }
  } catch (error) {
    console.error("Aircraft detail lookup failed", error);
    if (state.selectedHex === hex) {
      document.querySelector("#detail-lookup").textContent = "Additional details temporarily unavailable";
    }
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
  elements.options.hidden = false;
  elements.optionsControl.setAttribute("aria-expanded", "true");
}

function closeOptions() {
  elements.options.hidden = true;
  elements.optionsControl.setAttribute("aria-expanded", "false");
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
    applyPreferences();
    initializeMap();
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

window.setInterval(() => {
  elements.clock.textContent = new Date().toISOString().slice(11, 19) + "Z";
}, 1000);

start();

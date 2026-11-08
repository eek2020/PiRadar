const state = {
  config: null,
  map: null,
  tileLayer: null,
  homeMarker: null,
  airportLayer: null,
  allAirports: [],
  airports: [],
  markers: new Map(),
  history: new Map(),
  selectedTrail: null,
  selectedHex: null,
  selectedAirport: null,
  selectedNetwork: null,
  keyboardTarget: null,
  keyboardShift: false,
  keyboardCaps: false,
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
  services: document.querySelector("#services"),
  wifi: document.querySelector("#wifi"),
  airportDetail: document.querySelector("#airport-detail"),
  showLabels: document.querySelector("#show-labels"),
  showAirports: document.querySelector("#show-airports"),
  attribution: document.querySelector("#attribution"),
  locationForm: document.querySelector("#location-form"),
  locationPostcode: document.querySelector("#location-postcode"),
  locationStatus: document.querySelector("#location-status"),
  saveLocation: document.querySelector("#save-location"),
  postcodeKeyboard: document.querySelector("#postcode-keyboard"),
  textKeyboard: document.querySelector("#text-keyboard"),
  power: document.querySelector("#power"),
  powerChoices: document.querySelector("#power-choices"),
  powerConfirm: document.querySelector("#power-confirm"),
  powerQuestion: document.querySelector("#power-question"),
  powerGo: document.querySelector("#power-go"),
  powerMessage: document.querySelector("#power-message"),
  powerOverlay: document.querySelector("#power-overlay"),
  powerOverlayTitle: document.querySelector("#power-overlay-title"),
  powerOverlayText: document.querySelector("#power-overlay-text"),
  wifiStatus: document.querySelector("#wifi-status"),
  wifiNetworks: document.querySelector("#wifi-networks"),
  wifiForm: document.querySelector("#wifi-form"),
  wifiSelected: document.querySelector("#wifi-selected"),
  wifiPasswordLabel: document.querySelector("#wifi-password-label"),
  wifiPassword: document.querySelector("#wifi-password"),
  connectWifi: document.querySelector("#connect-wifi"),
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
  state.map.attributionControl.setPrefix(false);
  L.control.zoom({ position: "bottomleft" }).addTo(state.map);
  state.tileLayer = L.tileLayer(state.config.map_tile_url, {
    attribution: "© OpenStreetMap contributors",
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
  state.map.on("click", () => {
    clearSelection();
    closeAirportDetail();
  });
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
  if (kind === "light") return "M15 2 L17 12 L26 16 L26 18 L17 17 L17 23 L22 26 L22 28 L15 26 L8 28 L8 26 L13 23 L13 17 L4 18 L4 16 L13 12 Z";
  if (kind === "other") return "M15 2 L18 12 L26 16 L26 19 L18 17 L18 24 L21 27 L21 29 L15 26 L9 29 L9 27 L12 24 L12 17 L4 19 L4 16 L12 12 Z";
  return "M15 1 L18 11 L28 16 L28 19 L18 17 L18 24 L22 27 L22 29 L15 26 L8 29 L8 27 L12 24 L12 17 L2 19 L2 16 L12 11 Z";
}

function aircraftMarkup(kind) {
  if (kind !== "rotorcraft") return `<path class="airframe" d="${aircraftPath(kind)}"/>`;
  return `
    <path class="helicopter-body" d="M15 7c-3 0-5 3-5 7v6c0 3 2 5 4 6v3h2v-3c2-1 4-3 4-6v-6c0-4-2-7-5-7z"/>
    <path class="helicopter-tail" d="M14 25h2v4h5v1H9v-1h5z"/>
    <path class="helicopter-rotor" d="M2 10h26M15 2v16"/>
    <circle class="helicopter-hub" cx="15" cy="10" r="2"/>
  `;
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
    html: `<svg viewBox="0 0 30 30" aria-hidden="true" style="--aircraft-color:${altitudeColour(track)};transform:rotate(${rotation}deg)">${aircraftMarkup(kind)}</svg>${label}`,
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
  closeServices();
  closeWifi();
  closeAirportDetail();
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
    className: `airport-marker ${airport.type}${state.selectedAirport === code ? " selected" : ""}`,
    iconSize: [34, 40],
    iconAnchor: [17, 36],
    html: `<svg viewBox="0 0 30 38" aria-hidden="true"><path class="airport-pin" d="M15 1C7 1 2 7 2 15c0 9 13 21 13 21s13-12 13-21C28 7 23 1 15 1z"/><path class="airport-tower" d="M9 10h12v4h-2l2 11H9l2-11H9zm3 4-1 8h8l-1-8zM8 25h14v2H8z"/></svg><span class="code">${escapeHtml(code)}</span>`,
  });
}

function airportTypeLabel(type) {
  if (type === "large") return "Large airport";
  if (type === "medium") return "Regional airport";
  return "Local airfield";
}

function selectAirport(airport) {
  const code = airport.iata || airport.icao;
  clearSelection();
  closeOptions();
  closeFilters();
  closeServices();
  closeWifi();
  state.selectedAirport = code;
  document.querySelector("#airport-code").textContent = code;
  document.querySelector("#airport-name").textContent = airport.name;
  document.querySelector("#airport-identifiers").textContent = [airport.iata, airport.icao].filter(Boolean).join(" · ");
  document.querySelector("#airport-type").textContent = airportTypeLabel(airport.type);
  document.querySelector("#airport-distance").textContent = `${distanceFromHomeCoordinates(airport.latitude, airport.longitude).toFixed(1)} NM`;
  elements.airportDetail.hidden = false;
  renderAirports();
}

function closeAirportDetail() {
  if (!state.selectedAirport && elements.airportDetail.hidden) return;
  state.selectedAirport = null;
  elements.airportDetail.hidden = true;
  if (state.airportLayer) renderAirports();
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
        bubblingMouseEvents: false,
        title: `${airport.iata || airport.icao} · ${airport.name}`,
        zIndexOffset: -500,
      }).on("click", () => selectAirport(airport)).addTo(state.airportLayer);
    });
}

function updateAirportsForLocation() {
  state.airports = state.allAirports.filter((airport) => (
    distanceFromHomeCoordinates(airport.latitude, airport.longitude) <= state.config.range_nm * 1.4
  ));
  renderAirports();
}

async function loadAirports() {
  try {
    const response = await fetch("/data/airports-gb.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.allAirports = await response.json();
    state.map.attributionControl.addAttribution("Airports: OurAirports");
    updateAirportsForLocation();
  } catch (error) {
    console.warn("Airport layer unavailable", error);
  }
}

function showLocation() {
  const postcode = state.config.postcode || "";
  elements.locationPostcode.value = postcode;
  elements.locationStatus.dataset.state = "";
  elements.locationStatus.textContent = postcode
    ? `Radar centred on ${postcode}`
    : "Using configured home location";
}

async function saveTravelLocation() {
  const postcode = elements.locationPostcode.value.trim();
  if (!postcode) {
    elements.locationStatus.dataset.state = "error";
    elements.locationStatus.textContent = "Enter a complete UK postcode.";
    return;
  }
  closeKeyboard();
  elements.saveLocation.disabled = true;
  elements.locationStatus.dataset.state = "";
  elements.locationStatus.textContent = "Finding postcode…";
  try {
    const response = await fetch("/api/settings/location", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ postcode }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);

    clearSelection();
    closeAirportDetail();
    state.config = payload.config;
    state.markers.forEach((marker) => marker.remove());
    state.markers.clear();
    state.history.clear();
    state.latest = [];
    state.homeMarker.setLatLng([state.config.home_latitude, state.config.home_longitude]);
    elements.range.textContent = String(state.config.range_nm);
    updateAirportsForLocation();
    centerHome();
    showLocation();
    await updateAircraft();
  } catch (error) {
    elements.locationStatus.dataset.state = "error";
    elements.locationStatus.textContent = error.message || "Could not update location.";
  } finally {
    elements.saveLocation.disabled = false;
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
  closePower();
  clearSelection();
  closeAirportDetail();
  closeFilters();
  closeServices();
  closeWifi();
  elements.options.hidden = false;
  elements.optionsControl.setAttribute("aria-expanded", "true");
}

function closeOptions() {
  elements.options.hidden = true;
  closeKeyboard();
  elements.optionsControl.setAttribute("aria-expanded", "false");
}

function openFilters() {
  closePower();
  clearSelection();
  closeAirportDetail();
  closeOptions();
  closeServices();
  closeWifi();
  elements.filters.hidden = false;
  elements.filterControl.setAttribute("aria-expanded", "true");
}

function closeFilters() {
  elements.filters.hidden = true;
  elements.filterControl.setAttribute("aria-expanded", "false");
}

function openServices() {
  closePower();
  clearSelection();
  closeAirportDetail();
  closeOptions();
  closeFilters();
  closeWifi();
  elements.services.hidden = false;
  loadServiceStatus();
}

function closeServices() {
  elements.services.hidden = true;
  maskPasswords(elements.services);
  closeKeyboard();
}

function openWifi() {
  closePower();
  clearSelection();
  closeAirportDetail();
  closeOptions();
  closeFilters();
  closeServices();
  elements.wifi.hidden = false;
  loadWifiNetworks();
}

function closeWifi() {
  elements.wifi.hidden = true;
  maskPasswords(elements.wifi);
  elements.wifiForm.hidden = true;
  state.selectedNetwork = null;
  if (state.keyboardTarget === elements.wifiPassword) {
    closeKeyboard();
    state.keyboardTarget = null;
  }
}

function signalLabel(signal) {
  if (signal >= 75) return "Excellent";
  if (signal >= 50) return "Good";
  if (signal >= 25) return "Fair";
  return "Weak";
}

function renderWifiNetworks(networks) {
  if (!networks.length) {
    elements.wifiNetworks.innerHTML = '<p class="services-intro">No visible Wi-Fi networks found.</p>';
    return;
  }
  elements.wifiNetworks.innerHTML = networks.map((network) => `
    <button class="wifi-network" type="button" data-ssid="${escapeHtml(network.ssid)}" data-connected="${network.connected}" ${network.supported ? "" : "disabled"}>
      <span><strong>${escapeHtml(network.ssid)}</strong><small>${escapeHtml(network.security)}${network.supported ? "" : " · unsupported"}</small></span>
      <span>${network.connected ? "Connected" : `${signalLabel(network.signal)} · ${network.signal}%`}</span>
    </button>
  `).join("");
  elements.wifiNetworks.querySelectorAll(".wifi-network:not(:disabled)").forEach((button) => {
    button.addEventListener("click", () => selectWifiNetwork(networks.find((network) => network.ssid === button.dataset.ssid)));
  });
}

async function loadWifiNetworks() {
  if (state.keyboardTarget === elements.wifiPassword) closeKeyboard();
  elements.wifiStatus.dataset.state = "";
  elements.wifiStatus.textContent = "Scanning for nearby networks…";
  elements.wifiForm.hidden = true;
  state.selectedNetwork = null;
  try {
    const response = await fetch("/api/settings/wifi", { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    renderWifiNetworks(payload.networks);
    const connected = payload.networks.find((network) => network.connected);
    elements.wifiStatus.textContent = connected ? `Connected to ${connected.ssid}` : "Select a network";
  } catch (error) {
    elements.wifiNetworks.innerHTML = "";
    elements.wifiStatus.dataset.state = "error";
    elements.wifiStatus.textContent = error.message || "Could not scan for networks.";
  }
}

function selectWifiNetwork(network) {
  if (!network) return;
  state.selectedNetwork = network;
  elements.wifiSelected.textContent = network.ssid;
  elements.wifiPassword.value = "";
  maskPasswords(elements.wifi);
  elements.wifiPasswordLabel.hidden = !network.secured;
  elements.wifiPassword.closest(".password-field").hidden = !network.secured;
  elements.wifiForm.hidden = false;
  if (network.secured) {
    openKeyboard(elements.wifiPassword);
  } else {
    closeKeyboard();
  }
}

async function connectWifiNetwork() {
  if (!state.selectedNetwork) return;
  const password = elements.wifiPassword.value;
  if (state.selectedNetwork.secured && !password) {
    elements.wifiStatus.dataset.state = "error";
    elements.wifiStatus.textContent = "Enter the network password.";
    return;
  }
  closeKeyboard();
  elements.connectWifi.disabled = true;
  elements.wifiStatus.dataset.state = "";
  elements.wifiStatus.textContent = `Connecting to ${state.selectedNetwork.ssid}…`;
  try {
    const response = await fetch("/api/settings/wifi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ssid: state.selectedNetwork.ssid, password }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    elements.wifiPassword.value = "";
    elements.wifiForm.hidden = true;
    elements.wifiStatus.textContent = `Connected to ${payload.connection.ssid}`;
    window.setTimeout(loadWifiNetworks, 800);
  } catch (error) {
    elements.wifiStatus.dataset.state = "error";
    elements.wifiStatus.textContent = error.message || "Could not connect to the network.";
  } finally {
    elements.connectWifi.disabled = false;
  }
}

function renderServiceStatus(services) {
  document.querySelectorAll(".service-card").forEach((card) => {
    const configured = Boolean(services?.[card.dataset.service]?.configured);
    card.dataset.configured = String(configured);
    card.querySelector(".service-status").textContent = configured ? "Configured" : "Not configured";
    card.querySelectorAll("input").forEach((input) => {
      input.value = "";
      input.placeholder = configured ? "Stored · enter to replace" : "Enter credential";
    });
  });
}

async function loadServiceStatus() {
  try {
    const response = await fetch("/api/settings/services", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    renderServiceStatus(payload.services);
  } catch (error) {
    document.querySelectorAll(".service-status").forEach((status) => { status.textContent = "Unavailable"; });
  }
}

async function updateService(card, clear = false) {
  const message = card.querySelector(".service-message");
  const credentials = {};
  card.querySelectorAll("input").forEach((input) => {
    credentials[input.dataset.field] = clear ? "" : input.value.trim();
  });
  if (!clear && Object.values(credentials).some((value) => !value)) {
    message.dataset.state = "error";
    message.textContent = "Enter every field before saving.";
    return;
  }
  message.dataset.state = "";
  message.textContent = clear ? "Clearing…" : "Saving locally…";
  try {
    const response = await fetch("/api/settings/services", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service: card.dataset.service, credentials }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    renderServiceStatus(payload.services);
    message.textContent = clear ? "Credential removed." : "Saved securely on this Pi.";
  } catch (error) {
    message.dataset.state = "error";
    message.textContent = error.message || "Could not save credential.";
  }
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
    showLocation();
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
document.querySelector("#close-airport-detail").addEventListener("click", closeAirportDetail);
document.querySelector("#home-control").addEventListener("click", centerHome);
elements.optionsControl.addEventListener("click", () => elements.options.hidden ? openOptions() : closeOptions());
document.querySelector("#close-options").addEventListener("click", closeOptions);
document.querySelector("#open-services").addEventListener("click", openServices);
document.querySelector("#close-services").addEventListener("click", closeServices);
document.querySelector("#open-wifi").addEventListener("click", openWifi);
document.querySelector("#close-wifi").addEventListener("click", closeWifi);
document.querySelector("#scan-wifi").addEventListener("click", loadWifiNetworks);
document.querySelector("#cancel-wifi").addEventListener("click", () => {
  elements.wifiForm.hidden = true;
  closeKeyboard();
  state.selectedNetwork = null;
});
elements.wifiForm.addEventListener("submit", (event) => {
  event.preventDefault();
  connectWifiNetwork();
});
document.querySelectorAll(".service-card [data-action]").forEach((button) => {
  button.addEventListener("click", () => updateService(button.closest(".service-card"), button.dataset.action === "clear"));
});
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
elements.locationForm.addEventListener("submit", (event) => {
  event.preventDefault();
  saveTravelLocation();
});
// ---------------------------------------------------------------------------
// On-screen keyboards
//
// Every typeable field carries a data-osk attribute saying which keyboard it
// wants:
//   data-osk="postcode" : a large-key pad with capitals, digits, space,
//                         delete and Set. Nothing else, because a UK postcode
//                         needs nothing else.
//   data-osk            : a full UK (ISO) desktop-style keyboard with Caps
//                         Lock, both Shift keys and the UK symbol positions,
//                         including £ on Shift+3 and @ on Shift+'. Non-ASCII
//                         characters such as £ are sent as UTF-8, which is
//                         what routers and NetworkManager both use.
//
// Layouts are plain data, so changing a key means editing the arrays below.
// A key is either a single character string (width 1) or an object:
//   { char, w }                 character key with a custom width
//   { action, label, w, cls }   function key (backspace, shift, caps, ...)
//   { spacer: true, w }         empty gap, used for the row stagger
// Widths are relative within a row; each row fills the keyboard width.
// ---------------------------------------------------------------------------
// UK layout: what each key types with Shift held.
const OSK_SHIFTED = {
  "`": "¬", "1": "!", "2": '"', "3": "£", "4": "$", "5": "%", "6": "^", "7": "&",
  "8": "*", "9": "(", "0": ")", "-": "_", "=": "+", "[": "{", "]": "}",
  ";": ":", "'": "@", "#": "~", "\\": "|", ",": "<", ".": ">", "/": "?",
};

const OSK_LAYOUTS = {
  postcode: [
    [..."1234567890"],
    [..."QWERTYUIOP"],
    [..."ASDFGHJKL", { action: "backspace", label: "⌫", aria: "Delete last character" }],
    [..."ZXCVBNM", { action: "space", label: "Space", w: 1.5 }, { action: "submit", label: "Set", w: 1.5, cls: "keyboard-set" }],
  ],
  text: [
    [..."`1234567890-=", { action: "backspace", label: "⌫", w: 2, aria: "Delete last character" }],
    [{ spacer: true, w: 1.5 }, ..."qwertyuiop[]", { spacer: true, w: 1.5 }],
    [{ action: "caps", label: "Caps", w: 1.5, cls: "keyboard-mod" }, ..."asdfghjkl;'#", { action: "submit", label: "Enter", w: 1.5, cls: "keyboard-set" }],
    [{ action: "shift", label: "Shift", w: 1.25, cls: "keyboard-mod" }, ..."\\zxcvbnm,./", { action: "shift", label: "Shift", w: 2.75, cls: "keyboard-mod" }],
    [{ action: "clear", label: "Clear", w: 2.5, cls: "keyboard-mod" }, { action: "space", label: "Space", w: 10 }, { action: "hide", label: "Hide", w: 2.5, cls: "keyboard-mod" }],
  ],
};

// Build a keyboard's buttons from its layout.
function buildKeyboard(section, layout) {
  layout.forEach((row) => {
    const rowEl = document.createElement("div");
    rowEl.className = "keyboard-row";
    const specs = row.map((key) => (typeof key === "string" ? { char: key } : key));
    rowEl.style.gridTemplateColumns = specs.map((spec) => `${spec.w || 1}fr`).join(" ");
    specs.forEach((spec) => {
      if (spec.spacer) { rowEl.append(document.createElement("span")); return; }
      const button = document.createElement("button");
      button.type = "button";
      if (spec.cls) button.className = spec.cls;
      if (spec.aria) button.setAttribute("aria-label", spec.aria);
      if (spec.action) {
        button.dataset.action = spec.action;
        button.textContent = spec.label;
      } else {
        button.dataset.char = spec.char;
        // Show the shifted symbol in the corner, as on a real keycap.
        if (OSK_SHIFTED[spec.char]) button.dataset.alt = OSK_SHIFTED[spec.char];
      }
      rowEl.append(button);
    });
    section.append(rowEl);
  });
}

buildKeyboard(elements.postcodeKeyboard, OSK_LAYOUTS.postcode);
buildKeyboard(elements.textKeyboard, OSK_LAYOUTS.text);
const oskKeyboards = [elements.postcodeKeyboard, elements.textKeyboard];

// The character a key types right now, given Shift and Caps Lock.
// Like a real keyboard, Caps Lock affects letters only.
function oskCharFor(button) {
  const base = button.dataset.char;
  if (/^[a-z]$/.test(base)) return state.keyboardShift !== state.keyboardCaps ? base.toUpperCase() : base;
  return state.keyboardShift && OSK_SHIFTED[base] ? OSK_SHIFTED[base] : base;
}

// Repaint the full keyboard's labels and modifier highlights.
function renderTextKeyboard() {
  elements.textKeyboard.querySelectorAll("[data-char]").forEach((button) => {
    button.textContent = oskCharFor(button);
    // When Shift is down the main label already shows the shifted symbol.
    button.classList.toggle("show-alt", !state.keyboardShift && Boolean(button.dataset.alt));
  });
  elements.textKeyboard.querySelectorAll('[data-action="shift"]').forEach((button) => {
    button.setAttribute("aria-pressed", String(state.keyboardShift));
  });
  elements.textKeyboard.querySelector('[data-action="caps"]').setAttribute("aria-pressed", String(state.keyboardCaps));
}

// Postcode keys never change, so label them once.
elements.postcodeKeyboard.querySelectorAll("[data-char]").forEach((button) => {
  button.textContent = button.dataset.char;
});

// Inputs without a maxlength attribute report -1, which must mean "no limit".
function keyboardRoom(target) {
  return target.maxLength > 0 ? target.value.length < target.maxLength : true;
}

function openKeyboard(target) {
  const keyboard = target.dataset.osk === "postcode" ? elements.postcodeKeyboard : elements.textKeyboard;
  // Tapping the field already being typed into keeps Shift/Caps as they are.
  if (state.keyboardTarget === target && !keyboard.hidden) return;
  state.keyboardTarget = target;
  state.keyboardShift = false;
  state.keyboardCaps = false;
  oskKeyboards.forEach((section) => { section.hidden = section !== keyboard; });
  if (keyboard === elements.textKeyboard) {
    keyboard.querySelector('[data-action="submit"]').textContent =
      target === elements.wifiPassword ? "Connect" : target.closest(".service-card") ? "Save" : "Enter";
    renderTextKeyboard();
  }
  // Shrink tall panels so the field being typed into stays above the keyboard.
  document.body.style.setProperty("--osk-height", `${keyboard.offsetHeight + 16}px`);
  document.body.classList.add("osk-open");
  target.scrollIntoView({ block: "nearest" });
}

function closeKeyboard() {
  oskKeyboards.forEach((section) => { section.hidden = true; });
  state.keyboardTarget = null;
  document.body.classList.remove("osk-open");
}

function submitKeyboardTarget(target) {
  if (target === elements.wifiPassword) elements.wifiForm.requestSubmit();
  else if (target === elements.locationPostcode) elements.locationForm.requestSubmit();
  else {
    const card = target.closest(".service-card");
    if (!card) return;
    // Amadeus has two fields: move on to the next empty one before saving.
    const next = Array.from(card.querySelectorAll("input")).find((input) => input !== target && !input.value);
    if (next) { next.focus(); openKeyboard(next); return; }
    closeKeyboard();
    updateService(card);
  }
}

function handleKeyboardPress(button) {
  const target = state.keyboardTarget;
  if (!target) return;
  switch (button.dataset.action) {
    case "shift": state.keyboardShift = !state.keyboardShift; renderTextKeyboard(); return;
    case "caps": state.keyboardCaps = !state.keyboardCaps; renderTextKeyboard(); return;
    case "space": if (keyboardRoom(target)) target.value += " "; return;
    case "backspace": target.value = target.value.slice(0, -1); return;
    case "clear": target.value = ""; return;
    case "hide": target.blur(); closeKeyboard(); return;
    case "submit": submitKeyboardTarget(target); return;
    default: break;
  }
  if (!button.dataset.char || !keyboardRoom(target)) return;
  const onTextKeyboard = button.closest("#text-keyboard") !== null;
  target.value += onTextKeyboard ? oskCharFor(button) : button.dataset.char;
  // Shift applies to one character, then lets go, as on a real keyboard.
  if (onTextKeyboard && state.keyboardShift) {
    state.keyboardShift = false;
    renderTextKeyboard();
  }
}

oskKeyboards.forEach((section) => {
  // pointerdown + preventDefault stops a key stealing focus from the input,
  // so the field keeps its caret while typing.
  section.addEventListener("pointerdown", (event) => {
    if (event.target.closest("button")) event.preventDefault();
  });
  section.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (button) handleKeyboardPress(button);
  });
});

// Any field marked data-osk opens the keyboard it asks for.
document.querySelectorAll("input[data-osk]").forEach((input) => {
  input.addEventListener("focus", () => openKeyboard(input));
  input.addEventListener("click", () => openKeyboard(input));
});

// ---------------------------------------------------------------------------
// Show / hide password
//
// Every password box sits in a .password-field with an eye button. Tapping
// the eye switches the input between masked and plain text. maskPasswords()
// puts them all back to masked, and is called whenever a panel closes or a
// new Wi-Fi network is picked.
// ---------------------------------------------------------------------------
function setPasswordVisible(toggle, visible) {
  const input = toggle.closest(".password-field").querySelector("input");
  input.type = visible ? "text" : "password";
  toggle.setAttribute("aria-pressed", String(visible));
  toggle.setAttribute("aria-label", visible ? "Hide password" : "Show password");
}

function maskPasswords(scope = document) {
  scope.querySelectorAll("[data-reveal]").forEach((toggle) => setPasswordVisible(toggle, false));
}

document.querySelectorAll("[data-reveal]").forEach((toggle) => {
  // Keep focus (and the on-screen keyboard) on the input while toggling.
  toggle.addEventListener("pointerdown", (event) => event.preventDefault());
  toggle.addEventListener("click", (event) => {
    event.preventDefault();
    setPasswordVisible(toggle, toggle.getAttribute("aria-pressed") !== "true");
  });
});

// ---------------------------------------------------------------------------
// Power: safe shut down and restart
//
// Two taps are always needed: pick an action, then confirm it. On confirm the
// screen switches to a full-screen notice straight away, because the backend
// may be stopped by the shutdown before its reply arrives.
// ---------------------------------------------------------------------------
const POWER_TEXT = {
  poweroff: {
    question: "Shut down PiRadar?",
    button: "Shut down",
    title: "Shutting down…",
    detail: "Wait until the green light on the Pi stops flashing, then it is safe to unplug.",
  },
  reboot: {
    question: "Restart PiRadar?",
    button: "Restart",
    title: "Restarting…",
    detail: "The radar will be back in about a minute.",
  },
};
let pendingPowerAction = null;

function openPower() {
  clearSelection();
  closeAirportDetail();
  closeOptions();
  closeFilters();
  closeWifi();
  closeServices();
  resetPowerPanel();
  elements.power.hidden = false;
}

function closePower() {
  elements.power.hidden = true;
  resetPowerPanel();
}

function resetPowerPanel() {
  pendingPowerAction = null;
  elements.powerChoices.hidden = false;
  elements.powerConfirm.hidden = true;
  elements.powerMessage.textContent = "";
  elements.powerMessage.dataset.state = "";
}

function askPowerConfirm(action) {
  pendingPowerAction = action;
  elements.powerQuestion.textContent = POWER_TEXT[action].question;
  elements.powerGo.textContent = POWER_TEXT[action].button;
  elements.powerChoices.hidden = true;
  elements.powerConfirm.hidden = false;
}

async function runPowerAction() {
  const action = pendingPowerAction;
  if (!action) return;
  const text = POWER_TEXT[action];
  elements.powerOverlayTitle.textContent = text.title;
  elements.powerOverlayText.textContent = text.detail;
  elements.powerOverlay.hidden = false;
  try {
    const response = await fetch("/api/system/power", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  } catch (error) {
    // A dropped connection means the shutdown has already started, so keep
    // the notice up. Only a real error reply from the Pi undoes it.
    if (!(error instanceof TypeError)) {
      elements.powerOverlay.hidden = true;
      elements.powerMessage.dataset.state = "error";
      elements.powerMessage.textContent = error.message || "The Pi refused the request.";
      elements.powerChoices.hidden = false;
      elements.powerConfirm.hidden = true;
    }
  }
}

document.querySelector("#open-power").addEventListener("click", openPower);
document.querySelector("#close-power").addEventListener("click", closePower);
elements.powerChoices.addEventListener("click", (event) => {
  const button = event.target.closest("[data-power]");
  if (button) askPowerConfirm(button.dataset.power);
});
document.querySelector("#power-cancel").addEventListener("click", resetPowerPanel);
elements.powerGo.addEventListener("click", runPowerAction);

function preventKioskNavigation(event) {
  const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
  if (!link) return;
  if (link.closest(".leaflet-control-zoom")) return;
  event.preventDefault();
  event.stopImmediatePropagation();
}

document.addEventListener("click", preventKioskNavigation, true);
document.addEventListener("auxclick", preventKioskNavigation, true);
document.addEventListener("dragstart", preventKioskNavigation, true);
document.addEventListener("contextmenu", (event) => event.preventDefault(), true);

window.setInterval(() => {
  elements.clock.textContent = new Date().toISOString().slice(11, 19) + "Z";
}, 1000);

start();

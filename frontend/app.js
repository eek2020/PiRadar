const state = {
  config: null,
  selectedHex: null,
  latest: [],
};

const RADAR = { x: 210, y: 200, radius: 184 };

const elements = {
  tracks: document.querySelector("#tracks"),
  connection: document.querySelector("#connection"),
  clock: document.querySelector("#clock"),
  message: document.querySelector("#message"),
  count: document.querySelector("#aircraft-count"),
  range: document.querySelector("#range"),
  detail: document.querySelector("#detail"),
  attribution: document.querySelector("#attribution"),
  trafficList: document.querySelector("#traffic-list"),
  trafficSummary: document.querySelector("#traffic-summary"),
};

function setConnection(label, kind) {
  elements.connection.dataset.state = kind;
  elements.connection.lastElementChild.textContent = label;
}

function positionFor(track) {
  const latNm = (track.latitude - state.config.home_latitude) * 60;
  const lonNm = (track.longitude - state.config.home_longitude) * 60 * Math.cos(state.config.home_latitude * Math.PI / 180);
  const scale = RADAR.radius / state.config.range_nm;
  return {
    x: RADAR.x + lonNm * scale,
    y: RADAR.y - latNm * scale,
    distanceNm: Math.hypot(latNm, lonNm),
  };
}

function renderAircraft(aircraft) {
  state.latest = aircraft;
  elements.tracks.replaceChildren();
  const plotted = aircraft
    .map((track) => {
      const position = positionFor(track);
      return { track, position, distanceNm: position.distanceNm };
    })
    .filter(({ distanceNm }) => distanceNm <= state.config.range_nm)
    .sort((left, right) => left.distanceNm - right.distanceNm);
  const dense = plotted.length > 60;

  plotted.forEach(({ track, position }) => {

    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.classList.add("track");
    if (dense) group.classList.add("dense");
    if (track.hex === state.selectedHex) group.classList.add("selected");
    group.setAttribute("transform", `translate(${position.x.toFixed(1)} ${position.y.toFixed(1)})`);
    group.setAttribute("tabindex", "0");
    group.setAttribute("role", "button");
    group.setAttribute("aria-label", `${track.callsign || track.hex}, ${track.altitude_ft} feet`);

    const hitTarget = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    hitTarget.classList.add("hit-target");
    hitTarget.setAttribute("r", "14");

    const plane = document.createElementNS("http://www.w3.org/2000/svg", "path");
    plane.classList.add("plane");
    plane.setAttribute("d", dense
      ? "M0 -5 L4 4 L0 2 L-4 4 Z"
      : "M0 -8 L3 -2 L8 2 L8 4 L2 2 L2 6 L4 8 L0 7 L-4 8 L-2 6 L-2 2 L-8 4 L-8 2 L-3 -2 Z");
    plane.setAttribute("transform", `rotate(${track.track_deg})`);

    group.append(hitTarget, plane);
    if (track.hex === state.selectedHex) {
      group.classList.add("labelled");
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.classList.add("label");
      label.setAttribute("x", "12");
      label.setAttribute("y", "-2");
      label.textContent = track.callsign || track.hex;
      const altitude = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
      altitude.classList.add("altitude");
      altitude.setAttribute("x", "12");
      altitude.setAttribute("dy", "11");
      altitude.textContent = `${Math.round(track.altitude_ft / 100)} · ${track.ground_speed_kt}kt`;
      label.append(altitude);
      group.append(label);
    }

    const select = () => {
      showDetail(track);
      renderAircraft(state.latest);
    };
    group.addEventListener("click", select);
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") select();
    });
    elements.tracks.append(group);
  });

  renderTrafficList(plotted);
  elements.count.textContent = String(plotted.length);
  elements.message.hidden = plotted.length > 0;
  if (!plotted.length) elements.message.textContent = "No aircraft in range";
  if (state.selectedHex) {
    const selected = aircraft.find((track) => track.hex === state.selectedHex);
    if (selected) {
      populateDetail(selected);
    } else {
      state.selectedHex = null;
      elements.detail.hidden = true;
    }
  }
}

function renderTrafficList(plotted) {
  const nearest = plotted.slice(0, 8);
  elements.trafficList.replaceChildren();
  elements.trafficSummary.textContent = plotted.length
    ? `${nearest.length} of ${plotted.length} in range`
    : "No traffic in range";

  nearest.forEach(({ track, distanceNm }) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.classList.add("traffic-row");
    button.type = "button";
    button.setAttribute("aria-pressed", String(track.hex === state.selectedHex));
    button.setAttribute("aria-label", `${track.callsign || track.hex}, ${distanceNm.toFixed(1)} nautical miles`);

    const callsign = document.createElement("span");
    callsign.classList.add("traffic-callsign");
    callsign.textContent = track.callsign || track.hex;
    const altitude = document.createElement("span");
    altitude.classList.add("traffic-altitude");
    altitude.textContent = track.altitude_ft <= 0 ? "GND" : `${Math.round(track.altitude_ft / 100)}00ft`;
    const distance = document.createElement("span");
    distance.classList.add("traffic-distance");
    distance.textContent = `${distanceNm.toFixed(1)}nm`;

    button.addEventListener("click", () => {
      showDetail(track);
      renderAircraft(state.latest);
    });
    button.append(callsign, altitude, distance);
    item.append(button);
    elements.trafficList.append(item);
  });
}

function populateDetail(track) {
  document.querySelector("#detail-callsign").textContent = track.callsign || "Unknown";
  document.querySelector("#detail-altitude").textContent = `${track.altitude_ft.toLocaleString()} ft`;
  document.querySelector("#detail-speed").textContent = `${track.ground_speed_kt} kt`;
  document.querySelector("#detail-distance").textContent = `${positionFor(track).distanceNm.toFixed(1)} NM`;
  document.querySelector("#detail-track").textContent = `${String(track.track_deg).padStart(3, "0")}°`;
  document.querySelector("#detail-vertical").textContent = `${track.vertical_rate_fpm > 0 ? "+" : ""}${track.vertical_rate_fpm.toLocaleString()} fpm`;
  document.querySelector("#detail-hex").textContent = track.hex;
}

function showDetail(track) {
  state.selectedHex = track.hex;
  populateDetail(track);
  elements.detail.hidden = false;
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
    await updateAircraft();
    window.setInterval(updateAircraft, 3000);
  } catch (error) {
    console.error("PiRadar startup failed", error);
    setConnection("Offline", "error");
    elements.message.textContent = "Service unavailable · retrying";
    window.setTimeout(start, 3000);
  }
}

document.querySelector("#close-detail").addEventListener("click", () => {
  state.selectedHex = null;
  elements.detail.hidden = true;
  renderAircraft(state.latest);
});

window.setInterval(() => {
  elements.clock.textContent = new Date().toISOString().slice(11, 19) + "Z";
}, 1000);

start();

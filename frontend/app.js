const state = {
  config: null,
  selectedHex: null,
  latest: [],
};

const elements = {
  tracks: document.querySelector("#tracks"),
  connection: document.querySelector("#connection"),
  clock: document.querySelector("#clock"),
  message: document.querySelector("#message"),
  count: document.querySelector("#aircraft-count"),
  range: document.querySelector("#range"),
  detail: document.querySelector("#detail"),
  attribution: document.querySelector("#attribution"),
};

function setConnection(label, kind) {
  elements.connection.dataset.state = kind;
  elements.connection.lastElementChild.textContent = label;
}

function positionFor(track) {
  const latNm = (track.latitude - state.config.home_latitude) * 60;
  const lonNm = (track.longitude - state.config.home_longitude) * 60 * Math.cos(state.config.home_latitude * Math.PI / 180);
  const scale = 184 / state.config.range_nm;
  return { x: 400 + lonNm * scale, y: 200 - latNm * scale };
}

function renderAircraft(aircraft) {
  state.latest = aircraft;
  elements.tracks.replaceChildren();
  const plotted = aircraft
    .map((track) => {
      const position = positionFor(track);
      return { track, position, distance: Math.hypot(position.x - 400, position.y - 200) };
    })
    .filter(({ distance }) => distance <= 184)
    .sort((left, right) => left.distance - right.distance);
  const labelBoxes = [];

  plotted.forEach(({ track, position }) => {

    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.classList.add("track");
    group.setAttribute("transform", `translate(${position.x.toFixed(1)} ${position.y.toFixed(1)})`);
    group.setAttribute("tabindex", "0");
    group.setAttribute("role", "button");
    group.setAttribute("aria-label", `${track.callsign || track.hex}, ${track.altitude_ft} feet`);

    const plane = document.createElementNS("http://www.w3.org/2000/svg", "path");
    plane.classList.add("plane");
    plane.setAttribute("d", "M0 -9 L3 -2 L9 2 L9 4 L2 2 L2 7 L5 9 L5 10 L0 8 L-5 10 L-5 9 L-2 7 L-2 2 L-9 4 L-9 2 L-3 -2 Z");
    plane.setAttribute("transform", `rotate(${track.track_deg})`);

    const box = { left: position.x + 10, right: position.x + 78, top: position.y - 13, bottom: position.y + 14 };
    const collides = labelBoxes.some((placed) => !(
      box.right < placed.left || box.left > placed.right || box.bottom < placed.top || box.top > placed.bottom
    ));
    const showLabel = track.hex === state.selectedHex || (labelBoxes.length < 16 && !collides);
    if (showLabel) {
      group.classList.add("labelled");
      labelBoxes.push(box);
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
    group.prepend(plane);
    elements.tracks.append(group);
  });

  elements.count.textContent = String(plotted.length);
  elements.message.hidden = plotted.length > 0;
  if (!plotted.length) elements.message.textContent = "No aircraft in range";
  if (state.selectedHex) {
    const selected = aircraft.find((track) => track.hex === state.selectedHex);
    if (selected) populateDetail(selected);
  }
}

function populateDetail(track) {
  document.querySelector("#detail-callsign").textContent = track.callsign || "Unknown";
  document.querySelector("#detail-altitude").textContent = `${track.altitude_ft.toLocaleString()} ft`;
  document.querySelector("#detail-speed").textContent = `${track.ground_speed_kt} kt`;
  document.querySelector("#detail-track").textContent = `${String(track.track_deg).padStart(3, "0")}°`;
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

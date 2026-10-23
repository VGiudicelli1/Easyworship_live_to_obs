"use strict";

const stage = document.getElementById("stage");
const box = document.getElementById("text");
const params = new URLSearchParams(location.search);
const MIN_FONT_PX = 8;
let maxFontPx = Infinity;

// --- réglages par l'URL (valeurs validées : jamais de contenu injecté tel quel dans le CSS) ---
function applyParams() {
  const css = document.documentElement.style;
  const color = (name, variable) => {
    let value = params.get(name);
    if (value && /^[0-9a-f]{3,8}$/i.test(value)) value = "#" + value; // "?bg=000000" sans #
    if (value && CSS.supports("color", value)) css.setProperty(variable, value);
  };
  const length = (name, variable) => {
    const value = parseFloat(params.get(name));
    if (Number.isFinite(value) && value >= 0) css.setProperty(variable, value + "px");
  };
  color("bg", "--bg");
  color("color", "--color");
  length("padding", "--padding");
  length("margin", "--margin");
  length("radius", "--radius");
  const font = params.get("font");
  if (font && /^[\w\s,"'-]+$/.test(font)) css.setProperty("--font", font);
  const align = { left: "flex-start", center: "center", right: "flex-end" }[params.get("align")];
  if (align) {
    css.setProperty("--halign", align);
    css.setProperty("--talign", params.get("align"));
  }
  const valign = { top: "flex-start", middle: "center", bottom: "flex-end" }[params.get("valign")];
  if (valign) css.setProperty("--valign", valign);
  const max = parseFloat(params.get("max"));
  if (Number.isFinite(max) && max > 0) maxFontPx = max;
}

// --- taille de police : la plus grande qui tient dans la zone (recherche dichotomique) ---
function overflows(element) {
  return element.scrollHeight > element.clientHeight + 1 || element.scrollWidth > element.clientWidth + 1;
}

function fit() {
  if (box.hidden) return;
  let low = MIN_FONT_PX;
  let high = Math.max(MIN_FONT_PX, Math.min(maxFontPx, stage.clientHeight));
  for (let i = 0; i < 16 && high - low > 0.5; i++) {
    const middle = (low + high) / 2;
    box.style.fontSize = middle + "px";
    if (overflows(box)) high = middle;
    else low = middle;
  }
  box.style.fontSize = low + "px";
}

// --- affichage : textContent uniquement, jamais de HTML ---
function render(state) {
  const text = state && state.visible ? String(state.text || "") : "";
  box.textContent = text;
  box.hidden = text === "";
  fit();
}

// --- connexion à l'application, avec reconnexion automatique ---
let retries = 0;
function connect() {
  const scheme = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(scheme + "//" + location.host + "/ws");
  socket.onopen = () => {
    retries = 0;
  };
  socket.onmessage = (event) => {
    try {
      render(JSON.parse(event.data));
    } catch (error) {
      console.warn("message illisible", error);
    }
  };
  socket.onclose = () => {
    render(null); // application arrêtée ou injoignable : ne pas laisser un texte périmé
    setTimeout(connect, Math.min(500 * 2 ** retries++, 5000));
  };
  socket.onerror = () => socket.close();
}

applyParams();
window.addEventListener("resize", fit);
if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);

if (params.has("demo")) {
  // ?demo=1 ou ?demo=Mon%20texte : aperçu du style dans OBS sans application
  const demo = params.get("demo");
  render({ visible: true, text: demo === "1" || demo === "" ? "Texte de démonstration\nDeuxième ligne 😀" : demo });
} else {
  connect();
}

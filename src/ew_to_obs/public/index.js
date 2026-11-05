"use strict";

const stage = document.getElementById("stage");
const box = document.getElementById("text");
const params = new URLSearchParams(location.search);
const MIN_FONT_PX = 8;
let maxFontPx = (100 * 96) / 72; // 100 pt, plafond de la V2 (?max=PX pour le changer)
let graceMs = 2000; // connexion perdue : le texte reste ce délai avant d'être masqué (config / ?grace=)
let graceFromUrl = false;
let referenceLines = 0; // ?lines=N : taille stable jusqu'à N lignes (voir fit)

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
  const grace = parseFloat(params.get("grace"));
  if (Number.isFinite(grace) && grace >= 0 && grace <= 60) {
    graceMs = grace * 1000;
    graceFromUrl = true;
  }
  const lines = parseFloat(params.get("lines"));
  if (Number.isFinite(lines) && lines >= 1) referenceLines = lines;
}

// --- taille de police : la plus grande qui tient dans la zone (recherche dichotomique) ---
function overflows(element) {
  return element.scrollHeight > element.clientHeight + 1 || element.scrollWidth > element.clientWidth + 1;
}

// Avec ?lines=N : la police ne dépasse jamais celle qui fait tenir N lignes dans la zone. Les textes
// de moins de N lignes gardent donc la même taille ; au-delà de N lignes elle diminue.
function linesCap() {
  if (!referenceLines) return Infinity;
  const padding = parseFloat(getComputedStyle(box).paddingTop) * 2;
  return Math.max(MIN_FONT_PX, (stage.clientHeight - padding) / (referenceLines * 1.2));
}

function fit() {
  if (box.hidden) return;
  let low = MIN_FONT_PX;
  let high = Math.max(MIN_FONT_PX, Math.min(maxFontPx, linesCap(), stage.clientHeight));
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

// Délai de grâce : si la connexion à l'application se coupe, le texte reste affiché ce délai (une
// micro-coupure ne fait pas clignoter OBS) ; il est masqué si la connexion ne revient pas à temps.
let hideTimer = null;
function cancelHide() {
  if (hideTimer !== null) {
    clearTimeout(hideTimer);
    hideTimer = null;
  }
}
function scheduleHide() {
  if (hideTimer !== null) return;
  if (graceMs <= 0) {
    render(null);
    return;
  }
  hideTimer = setTimeout(() => {
    hideTimer = null;
    render(null);
  }, graceMs);
}

// Réglage de la config de l'application ; en cas d'échec, la valeur par défaut (2 s) reste.
function loadSettings() {
  if (graceFromUrl) return;
  fetch("/settings.json", { cache: "no-store" })
    .then((response) => response.json())
    .then((settings) => {
      const grace = Number(settings.grace);
      if (Number.isFinite(grace) && grace >= 0 && grace <= 60) graceMs = grace * 1000;
    })
    .catch(() => {});
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
      const state = JSON.parse(event.data);
      cancelHide(); // la connexion est revenue (ou n'a jamais été perdue) : l'état reçu fait foi
      render(state);
    } catch (error) {
      console.warn("message illisible", error);
    }
  };
  socket.onclose = () => {
    scheduleHide(); // application arrêtée ou injoignable : pas de texte périmé au-delà du délai
    setTimeout(connect, Math.min(500 * 2 ** retries++, 5000));
  };
  socket.onerror = () => socket.close();
}

applyParams();
loadSettings();
window.addEventListener("resize", fit);
if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);

if (params.has("demo")) {
  // ?demo=1 ou ?demo=Mon%20texte : aperçu du style dans OBS sans application
  const demo = params.get("demo");
  render({ visible: true, text: demo === "1" || demo === "" ? "Texte de démonstration\nDeuxième ligne 😀" : demo });
} else {
  connect();
}

/* ==========================================================================
   NexFleet — Logique de l'application (ES6, fonctionne sans compilation)
   Source TypeScript équivalente : ts/app.ts
   ========================================================================== */
"use strict";

/* --------------------------------------------------------------- état global */
const state = {
  token: localStorage.getItem("nf_token") || "",
  user: JSON.parse(localStorage.getItem("nf_user") || "null"),
  view: "dashboard",
  cache: {},
};

const TITLES = {
  dashboard: ["Tableau de bord", "Vue d'ensemble de votre parc"],
  vehicles: ["Véhicules", "Gérez votre flotte et les échéances"],
  drivers: ["Conducteurs", "Permis, affectations et coordonnées"],
  controls: ["Contrôles", "Fiches de contrôle et conformité"],
  maintenance: ["Maintenance", "Interventions et historique"],
  vidanges: ["Vidanges", "Suivi des vidanges et de l'huile"],
  budget: ["Budget", "Plan de maintenance préventive : prévu vs réalisé"],
  analytics: ["Analytique", "Coût total de possession (TCO) et tendances"],
  calendar: ["Calendrier", "Échéances et événements du parc"],
  maps: ["Cartes", "Localisation GPS des véhicules en temps réel"],
  reports: ["Rapports & PDF", "Documents professionnels exportables"],
  activity: ["Activité", "Journal d'audit et traces des actions"],
  settings: ["Paramètres", "Compte, sécurité, préférences et données"],
};

const CARBURANTS = ["Diesel", "Essence", "Hybride", "Électrique", "GPL", "Bioéthanol"];
const TYPES_VEH = ["Utilitaire", "Camion", "Berline", "4x4", "Moto", "Remorque"];
// Catégories standardisées de maintenance — alignées avec le plan budgétaire
// (backend/budget.py::CATEGORIES) pour permettre la comparaison prévu/réalisé.
const MAINT_CATEGORIES = ["Moteur", "Freinage", "Pompes", "Administratif", "Vidange",
  "Pneumatique", "Tôlerie", "Batterie", "Climatisation", "Électronique", "Révision", "Autre"];
const STATUTS = ["En service", "En maintenance", "En panne", "Hors service"];
const CHECKLIST = [
  "Carrosserie et état extérieur",
  "Pneumatiques et pression",
  "Freins et plaquettes",
  "Éclairage et signalisation",
  "Niveaux (huile, refroidissement)",
  "Batterie et démarrage",
  "Essuie-glaces et lave-glace",
  "Suspension et direction",
  "Documents de bord",
  "Sécurité (triangle, trousse)",
  "Climatisation / chauffage",
  "Roue de secours / kit",
];

/* --------------------------------------------------------------- utilitaires DOM */
const $$ = (s, r) => [...(r || document).querySelectorAll(s)];

function h(tag, attrs, children) {
  const node = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") node.className = v;
      else if (k === "html") node.innerHTML = v;
      else if (k === "text") node.textContent = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else if (k === "dataset") Object.assign(node.dataset, v);
      else node.setAttribute(k, v);
    }
  }
  (children || []).forEach((c) => {
    if (c == null) return;
    node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  });
  return node;
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/* --------------------------------------------------------------- icônes SVG */
const ICONS = {
  grid: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  car: '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  check: '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/>',
  wrench: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
  pencil: '<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
  eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-6.2-8.56"/><path d="M21 3v5h-5"/>',
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
};

function svg(name, cls) {
  const paths = ICONS[name] || ICONS.car;
  return `<svg class="${cls || "ico"}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
}

function skeleton(lines) {
  const items = [];
  for (let i = 0; i < (lines || 4); i++) items.push(h("div", { class: "skeleton", style: `height:64px;margin-bottom:10px` }));
  return h("div", { class: "content" }, items);
}

function emptyRow(colspan, icon, text) {
  const box = h("div", { class: "empty" }, [
    h("div", { class: "empty-ico", text: icon }),
    h("p", { text: text }),
  ]);
  const td = h("td", { colspan: colspan });
  td.appendChild(box);
  const tr = h("tr", null, [td]);
  return h("tbody", null, [tr]);
}

/* ------------------------------------------------------------------ toasts */
function toast(msg, type) {
  const root = document.getElementById("toast-root");
  const icons = { success: "✓", error: "✕", warning: "⚠", info: "ℹ" };
  const node = h("div", { class: `toast ${type}`, style: `--tcolor:${type === "error" ? "#f87171" : type === "warning" ? "#fbbf24" : "#34d399"}` }, [
    h("div", { class: "toast-ico", text: icons[type] || "✓" }),
    h("div", { text: msg }),
  ]);
  root.appendChild(node);
  setTimeout(() => {
    node.classList.add("out");
    setTimeout(() => node.remove(), 400);
  }, 4000);
}

/* ------------------------------------------------------------------ modales */
function openModal(html, wide) {
  closeModal();
  const root = document.getElementById("modal-root");
  root.innerHTML = "";
  const box = h("div", { class: `modal glass${wide ? " wide" : ""}` });
  box.innerHTML = html;
  root.append(
    h("div", { class: "modal-backdrop", onclick: closeModal }),
    box,
  );
  requestAnimationFrame(() => bindModal(root));
  return box;
}

function closeModal() {
  const root = document.getElementById("modal-root");
  root.innerHTML = "";
}

function bindModal(root) {
  $$("[data-close]", root).forEach((b) => b.addEventListener("click", closeModal));
  $$("form[data-modal]", root).forEach((f) => f.addEventListener("submit", (e) => e.preventDefault()));
  $$("[data-set-date]", root).forEach((b) => {
    b.addEventListener("click", () => {
      const input = document.getElementById(b.dataset.setDate);
      if (input) input.value = new Date().toISOString().slice(0, 10);
    });
  });
}

function confirmBox(title, msg, onYes) {
  const box = openModal(`
    <div class="modal-head"><h4>${esc(title)}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <p style="color:var(--text-dim);margin-bottom:22px">${esc(msg)}</p>
    <div style="display:flex;gap:10px;justify-content:flex-end">
      <button class="btn btn-ghost" data-close>Annuler</button>
      <button class="btn btn-danger" id="confirm-yes">Confirmer</button>
    </div>`);
  box.querySelector("#confirm-yes").addEventListener("click", () => {
    closeModal();
    onYes();
  });
}

/* ------------------------------------------------------------------ palette de commandes */
const PALETTE = [];
let paletteOpen = false;
let paletteIdx = 0;
let paletteResults = [];

function buildPalette() {
  PALETTE.length = 0;
  [
    ["dashboard", "Tableau de bord", "grid", "accueil vue d'ensemble"],
    ["vehicles", "Véhicules", "car", "flotte immatriculation parc"],
    ["drivers", "Conducteurs", "users", "permis chauffeur"],
    ["controls", "Contrôles", "check", "fiche conformité point"],
    ["maintenance", "Maintenance", "wrench", "intervention garage révision"],
    ["vidanges", "Vidanges", "wrench", "huile filtre vidange"],
    ["budget", "Budget", "file", "plan achat annuel prevu realise depense"],
    ["analytics", "Analytique", "grid", "tco cout total possession tendance"],
    ["calendar", "Calendrier", "history", "échéance événement date agenda"],
    ["reports", "Rapports & PDF", "file", "document export fiche"],
    ["activity", "Activité", "history", "journal audit trace journal"],
    ["settings", "Paramètres", "gear", "compte mot de passe sécurité"],
  ].forEach(([route, label, icon, kw]) => {
    PALETTE.push({ label, icon, kw: `${label} ${kw}`, run: () => navigate(route) });
  });
  PALETTE.push(
    { label: "Nouveau véhicule", icon: "car", kw: "ajouter créer véhicule", run: () => vehicleModal(null) },
    { label: "Nouveau conducteur", icon: "users", kw: "ajouter créer conducteur", run: () => driverModal(null) },
    {
      label: "Nouveau contrôle", icon: "check", kw: "ajouter créer contrôle fiche",
      run: async () => {
        const r = await Promise.all([api("/api/vehicles"), api("/api/drivers")]);
        controlModal(null, r[0].vehicles || [], r[1].drivers || []);
      },
    },
    {
      label: "Nouvelle intervention", icon: "wrench", kw: "ajouter création maintenance garage",
      run: async () => {
        const r = await api("/api/vehicles");
        maintenanceModal(null, r.vehicles || []);
      },
    },
    { label: "Rapport du parc (PDF)", icon: "file", kw: "pdf rapport document", run: () => parcPdf() },
    { label: "Nouvel utilisateur", icon: "users", kw: "ajouter créer compte utilisateur admin", run: () => userModal(null) },
    { label: "Exporter les véhicules (Excel)", icon: "file", kw: "export excel xlsx données", run: () => exportExcel() },
    { label: "Exporter les véhicules (CSV)", icon: "file", kw: "export csv données", run: () => exportCSV() },
    { label: "Télécharger le modèle d'import", icon: "file", kw: "template import modèle xlsx csv", run: () => downloadTemplate() },
    { label: "Importer des données", icon: "upload", kw: "import xlsx csv charger", run: () => importModal() },
    { label: "Importer le plan de maintenance (Budget)", icon: "upload", kw: "budget plan achat annuel import", run: () => budgetImportModal() },
    { label: "Demander à l'assistant NexFleet", icon: "search", kw: "assistant ia question chat", run: () => toggleAssistant(true) },
    { label: "Charger les données de démo", icon: "grid", kw: "demo démonstration", run: () => loadDemo() },
    { label: "Déconnexion", icon: "logout", kw: "quitter signout", run: () => logout() },
  );
}

function togglePalette(force) {
  const root = document.getElementById("palette-root");
  if (!root) return;
  paletteOpen = force != null ? force : !paletteOpen;
  if (!paletteOpen) { root.hidden = true; return; }
  root.hidden = false;
  const input = document.getElementById("palette-input");
  input.value = "";
  paletteIdx = 0;
  renderPalette();
  requestAnimationFrame(() => input.focus());
}

function renderPalette() {
  const input = document.getElementById("palette-input");
  const q = (input.value || "").toLowerCase().trim();
  paletteResults = PALETTE.filter((p) =>
    !q || p.label.toLowerCase().includes(q) || p.kw.toLowerCase().includes(q));
  const list = document.getElementById("palette-list");
  list.innerHTML = "";
  if (!paletteResults.length) {
    list.appendChild(h("div", { class: "palette-empty", html: `<span class="palette-empty-ico">${svg("search")}</span><span>Aucun résultat pour « ${esc(input.value)} »</span>` }));
    return;
  }
  if (paletteIdx > paletteResults.length - 1) paletteIdx = 0;
  paletteResults.forEach((p, i) => {
    list.appendChild(h("button", {
      class: "palette-item" + (i === paletteIdx ? " active" : ""),
      onclick: () => runPalette(i),
    }, [
      h("span", { class: "palette-ico", html: svg(p.icon) }),
      h("span", { class: "palette-label", text: p.label }),
      h("span", { class: "kbd", text: "↵" }),
    ]));
  });
  const active = list.querySelector(".palette-item.active");
  if (active) active.scrollIntoView({ block: "nearest" });
}

async function runPalette(i) {
  const p = paletteResults[i];
  if (!p) return;
  togglePalette(false);
  await p.run();
}

/* ------------------------------------------------------------------ API client */
async function api(path, method, body) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  const res = await fetch(path, {
    method: method || "GET",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch (_) { /* réponse vide */ }
  if (res.status === 401 && !path.startsWith("/api/auth/login") && !path.startsWith("/api/auth/register")) {
    logout();
    throw new Error("Session expirée.");
  }
  if (!res.ok) throw new Error((data && data.error) || "Erreur serveur.");
  return data;
}

async function downloadPdf(path, filename) {
  const res = await fetch(path, {
    headers: { Authorization: "Bearer " + state.token },
  });
  if (!res.ok) {
    let data = null;
    try { data = await res.json(); } catch (_) {}
    throw new Error((data && data.error) || "Génération du PDF impossible.");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = h("a", { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/* ------------------------------------------------------------------ formatage */
function fmtDate(iso) {
  if (!iso) return "—";
  const s = String(iso).replace(" ", "T");
  const d = new Date(s + (s.length === 10 ? "T00:00:00" : ""));
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function fmtDateTime(iso) {
  if (!iso) return "—";
  const s = String(iso).replace(" ", "T");
  const d = new Date(s + (s.length === 10 ? "T00:00:00" : ""));
  if (isNaN(d)) return iso;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fmtKm(n) {
  n = Number(n) || 0;
  return n.toLocaleString("fr-FR") + " km";
}

function fmtMoney(n) {
  n = Number(n) || 0;
  return Math.round(n).toLocaleString("fr-FR") + " FCFA";
}

function fmtFcfaShort(n) {
  n = Number(n) || 0;
  if (n >= 1000000) return (n / 1000000).toFixed(1).replace(".", ",") + " M";
  if (n >= 1000) return Math.round(n / 1000) + " k";
  return String(Math.round(n));
}

function daysLeft(iso) {
  if (!iso) return null;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const d = new Date(iso + "T00:00:00");
  return Math.round((d - today) / 86400000);
}

function daysChip(iso) {
  const dl = daysLeft(iso);
  if (dl == null) return h("span", { class: "days-chip days-ok", text: "—" });
  if (dl < 0) return h("span", { class: "days-chip days-danger", text: `expiré -${Math.abs(dl)}j` });
  if (dl <= 15) return h("span", { class: "days-chip days-warn", text: `${dl} j` });
  return h("span", { class: "days-chip days-ok", text: `${dl} j` });
}

function badgeForStatut(s) {
  const t = (s || "").toLowerCase();
  let cls = "badge badge-service", label = s;
  if (t.includes("maintenance")) { cls = "badge badge-maintenance"; }
  else if (t.includes("panne")) { cls = "badge badge-panne"; }
  else if (t.includes("hors")) { cls = "badge badge-muted"; }
  return h("span", { class: cls, text: label });
}

function badgeResultat(r) {
  const t = (r || "").toLowerCase();
  const cls = t.includes("non") || t.includes("refus") ? "badge badge-danger"
    : t.includes("surveill") ? "badge badge-warn" : "badge badge-ok";
  return h("span", { class: cls, text: r || "En cours" });
}

function vehicleThumb(v, size) {
  const style = size ? `width:${size}px;height:${size}px;min-width:${size}px;font-size:${Math.max(13, Math.round(size * 0.42))}px` : "";
  if (v.photo) {
    return h("span", {
      class: "veh-thumb zoomable",
      style: style,
      title: "Agrandir la photo",
      onclick: (e) => { e.stopPropagation(); viewVehiclePhoto(v); },
    }, [
      h("img", { src: v.photo_thumb || v.photo, alt: v.immatriculation || "véhicule", loading: "lazy" }),
    ]);
  }
  return h("span", { class: "veh-thumb veh-thumb-ph", style: style, text: (v.immatriculation || "V")[0] });
}

/* --------------------------------------------------------------- visionneuse photo plein écran */
function closePhotoViewer() {
  const root = document.getElementById("viewer-root");
  if (!root) return;
  root.classList.remove("open");
  setTimeout(() => root.remove(), 260);
}

function viewVehiclePhoto(v, src) {
  closePhotoViewer();
  const url = src || v.photo;
  if (!url) return;
  let root = document.getElementById("viewer-root");
  if (!root) {
    root = h("div", { id: "viewer-root", class: "viewer-root" });
    document.body.appendChild(root);
  }
  root.innerHTML = "";
  const title = `${v.marque || ""} ${v.modele || ""}`.trim();
  root.append(h("div", { class: "viewer-backdrop", onclick: closePhotoViewer, style: "position:absolute;inset:0" }),
    h("div", { class: "viewer-card" }, [
      h("div", { class: "viewer-head" }, [
        h("div", { class: "viewer-head-avatar" }, [h("img", { src: url, alt: v.immatriculation || "photo" })]),
        h("div", { class: "viewer-head-text" }, [
          h("strong", { text: title || v.immatriculation || "Photo du véhicule" }),
          h("small", { text: v.immatriculation || "" }),
        ]),
        h("button", { class: "viewer-close", title: "Fermer", onclick: closePhotoViewer, html: "✕" }),
      ]),
      h("div", { class: "viewer-stage" }, [
        h("img", { src: url, alt: v.immatriculation || "photo du véhicule" }),
      ]),
      h("div", { class: "viewer-foot" }, [
        h("small", { text: title ? `${title} · ${v.immatriculation || ""}` : (v.immatriculation || "Photo du véhicule") }),
        h("span", { class: "viewer-hint", text: "Échap pour fermer" }),
      ]),
    ]));
  requestAnimationFrame(() => root.classList.add("open"));
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closePhotoViewer();
});

/* ------------------------------------------------------------------ graphiques */
function prepCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 260;
  const h = canvas.clientHeight || 200;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return { ctx, w, h };
}

function drawDonut(canvas, entries, colors) {
  const { ctx, w, h } = prepCanvas(canvas);
  const cx = w / 2, cy = h / 2, r = Math.min(w, h) / 2 - 6, lw = 20;
  const total = entries.reduce((a, b) => a + b, 0) || 1;
  const t0 = performance.now(), dur = 900;
  (function step(t) {
    const p = Math.min(1, (t - t0) / dur), ease = 1 - Math.pow(1 - p, 3);
    ctx.clearRect(0, 0, w, h);
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(255,255,255,0.07)"; ctx.lineWidth = lw; ctx.stroke();
    let a = -Math.PI / 2;
    entries.forEach((v, i) => {
      if (!v) return;
      const ang = (v / total) * Math.PI * 2 * ease;
      ctx.beginPath(); ctx.arc(cx, cy, r, a, a + ang);
      ctx.strokeStyle = colors[i]; ctx.lineWidth = lw; ctx.lineCap = "butt"; ctx.stroke();
      a += ang;
    });
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}

function drawBars(canvas, labels, values, fmt) {
  const { ctx, w, h } = prepCanvas(canvas);
  const t0 = performance.now(), dur = 850;
  const pad = 30;
  const formatter = fmt || ((v) => String(v));
  (function step(t) {
    const p = Math.min(1, (t - t0) / dur), ease = 1 - Math.pow(1 - p, 3);
    ctx.clearRect(0, 0, w, h);
    const max = Math.max(...values, 1);
    const bw = (w - pad * 1.6) / labels.length;
    values.forEach((v, i) => {
      const bh = ((h - 34) * v / max) * ease;
      const x = pad + i * bw + bw * 0.22;
      const y = h - 26 - bh;
      const grad = ctx.createLinearGradient(0, y, 0, h);
      grad.addColorStop(0, "#6366f1"); grad.addColorStop(1, "#22d3ee");
      ctx.fillStyle = grad;
      roundRect(ctx, x, y, bw * 0.56, bh, 7);
      ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,0.6)"; ctx.font = "600 10px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(formatter(v), x + bw * 0.28, y - 5);
      ctx.fillStyle = "rgba(255,255,255,0.4)"; ctx.font = "600 10px Inter, sans-serif";
      const lbl = labels[i].slice(0, 4);
      ctx.fillText(lbl, x + bw * 0.28, h - 8);
    });
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}

function drawRing(canvas, ratio, color) {
  const { ctx, w, h } = prepCanvas(canvas);
  const cx = w / 2, cy = h / 2, r = Math.min(w, h) / 2 - 6, lw = 12;
  const t0 = performance.now(), dur = 900;
  (function step(t) {
    const p = Math.min(1, (t - t0) / dur), ease = 1 - Math.pow(1 - p, 3);
    ctx.clearRect(0, 0, w, h);
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(255,255,255,0.07)"; ctx.lineWidth = lw; ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * ratio * ease);
    ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = "round"; ctx.stroke();
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function animateCounter(node, target, suffix) {
  const t0 = performance.now(), dur = 900;
  (function step(t) {
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    node.textContent = Math.round(target * e).toLocaleString("fr-FR") + (suffix || "");
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}

/* ------------------------------------------------------------------ auth */
function showLogin() {
  document.getElementById("app-screen").hidden = true;
  document.getElementById("login-screen").hidden = false;
}

function showApp() {
  document.getElementById("login-screen").hidden = true;
  document.getElementById("app-screen").hidden = false;
  applyUser();
  loadNotifications();
}

function applyUser() {
  const u = state.user;
  if (!u) return;
  document.getElementById("sidebar-username").textContent = u.username;
  document.getElementById("sidebar-role").textContent = u.role === "admin" ? "Administrateur" : "Utilisateur";
  document.getElementById("sidebar-avatar").textContent = (u.username || "U")[0].toUpperCase();
}

function logout() {
  state.token = "";
  state.user = null;
  localStorage.removeItem("nf_token");
  localStorage.removeItem("nf_user");
  showLogin();
  location.hash = "#/login";
}

async function doLogin(e) {
  e.preventDefault();
  const btn = document.getElementById("login-submit");
  const ident = document.getElementById("login-ident").value.trim();
  const pass = document.getElementById("login-pass").value;
  btn.disabled = true; btn.querySelector(".btn-label").textContent = "Connexion…";
  try {
    const data = await api("/api/auth/login", "POST", { username: ident, password: pass });
    state.token = data.token;
    state.user = data.user;
    localStorage.setItem("nf_token", data.token);
    localStorage.setItem("nf_user", JSON.stringify(data.user));
    toast("Bienvenue, " + data.user.username + " !");
    showApp();
    navigate("dashboard");
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false; btn.querySelector(".btn-label").textContent = "Entrer dans NexFleet";
  }
}

async function doRegister(e) {
  e.preventDefault();
  const btn = document.getElementById("register-submit");
  const body = {
    username: document.getElementById("reg-name").value.trim(),
    email: document.getElementById("reg-email").value.trim(),
    password: document.getElementById("reg-pass").value,
  };
  btn.disabled = true; btn.querySelector(".btn-label").textContent = "Création…";
  try {
    const data = await api("/api/auth/register", "POST", body);
    state.token = data.token;
    state.user = data.user;
    localStorage.setItem("nf_token", data.token);
    localStorage.setItem("nf_user", JSON.stringify(data.user));
    toast("Compte créé. Bienvenue dans NexFleet !");
    showApp();
    navigate("dashboard");
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false; btn.querySelector(".btn-label").textContent = "Créer mon compte";
  }
}

/* ------------------------------------------------------------------ routeur */
function currentRoute() {
  const m = location.hash.match(/^#\/(\w+)/);
  return m && TITLES[m[1]] ? m[1] : (state.token ? "dashboard" : "login");
}

function navigate(route) {
  location.hash = "#/" + route;
}

function renderRoute() {
  const route = currentRoute();
  if (route === "login") { showLogin(); return; }
  if (!state.token) { location.hash = "#/login"; return; }
  state.view = route;
  showApp();
  const t = TITLES[route];
  document.getElementById("page-title").textContent = t[0];
  document.getElementById("page-sub").textContent = t[1];
  $$("#sidebar-nav .nav-item").forEach((n) =>
    n.classList.toggle("active", n.dataset.route === route));

  const content = document.getElementById("content");
  content.innerHTML = "";
  content.appendChild(skeleton(3));
  content.classList.remove("route-anim");
  void content.offsetWidth;
  content.classList.add("route-anim");

  const views = {
    dashboard: viewDashboard,
    vehicles: viewVehicles,
    drivers: viewDrivers,
    controls: viewControls,
    maintenance: viewMaintenance,
    vidanges: viewVidanges,
    budget: viewBudget,
    analytics: viewAnalytics,
    calendar: viewCalendar,
    maps: viewMaps,
    reports: viewReports,
    activity: viewActivity,
    settings: viewSettings,
  };
  (views[route] || viewDashboard)(content);
}

/* ==========================================================================
   VUE : TABLEAU DE BORD
   ========================================================================== */
async function viewDashboard(root) {
  const [data, notifRes, vgRes] = await Promise.all([
    api("/api/stats"), api("/api/notifications").catch(() => ({ events: [] })), api("/api/vidanges/stats").catch(() => null),
  ]);
  const vgStats = vgRes || {};
  const palette = ["#6366f1", "#22d3ee", "#a78bfa", "#f472b6", "#34d399", "#fbbf24"];

  const carbEntries = Object.entries(data.carburant || {});
  const carbVals = carbEntries.map((c) => c[1]);
  const siteEntries = Object.entries(data.by_site || {});
  const siteVals = siteEntries.map((s) => s[1]);
  const serviceRatio = data.total ? data.en_service / data.total : 0;
  const dispoPct = Math.round(serviceRatio * 100);

  const kpis = [
    { icon: "🚗", label: "Véhicules au total", value: data.total, tint: "rgba(99,102,241,0.18)", glow: "rgba(99,102,241,0.4)", trend: data.total ? `${data.total} immatriculé(s)` : "à compléter" },
    { icon: "✅", label: "En service", value: data.en_service, tint: "rgba(52,211,153,0.16)", glow: "rgba(52,211,153,0.35)", trend: data.total ? `${dispoPct}% du parc` : null },
    { icon: "🔧", label: "En maintenance", value: data.en_maintenance, tint: "rgba(251,191,36,0.16)", glow: "rgba(251,191,36,0.35)", trend: data.en_maintenance ? "à planifier" : null },
    { icon: "⚠️", label: "En panne", value: data.en_panne, tint: "rgba(248,113,113,0.16)", glow: "rgba(248,113,113,0.35)", trend: data.en_panne ? "bad" : null },
    { icon: "🪪", label: "Conducteurs", value: data.drivers, tint: "rgba(34,211,238,0.16)", glow: "rgba(34,211,238,0.35)", trend: null },
    { icon: "📋", label: "Contrôles ce mois", value: data.controls_month, tint: "rgba(167,139,250,0.16)", glow: "rgba(167,139,250,0.35)", trend: data.controls_total ? `${data.controls_total} au total` : null },
    { icon: "💰", label: "Coût maintenance", value: data.maintenance_total, tint: "rgba(244,114,182,0.16)", glow: "rgba(244,114,182,0.35)", trend: null, money: true },
    { icon: "🛢️", label: "Vidanges", value: data.vidanges_count || 0, tint: "rgba(251,146,60,0.16)", glow: "rgba(251,146,60,0.35)", trend: (data.vidanges_count || 0) ? `${(data.vidanges_total || 0).toLocaleString("fr-FR")} FCFA` : null },
  ];

  const statsGrid = h("div", { class: "stats-grid" });
  kpis.forEach((k, i) => {
    const card = h("div", {
      class: "stat-card glass reveal reveal-" + (i % 5 + 1),
      style: `--tint:${k.tint};--glow:${k.glow}`,
    }, [
      h("div", { class: "stat-icon", text: k.icon }),
      h("div", { class: "stat-value", id: "kpi-" + i }),
      h("div", { class: "stat-label", text: k.label }),
      k.trend ? h("span", { class: "stat-trend" + (k.trend === "bad" ? " bad" : ""), text: k.trend === "bad" ? "▼ à traiter" : k.trend }) : null,
    ]);
    statsGrid.appendChild(card);
  });

  if (data.total === 0) {
    statsGrid.appendChild(h("div", { class: "panel glass reveal reveal-1", style: "grid-column:1/-1" }, [
      h("div", { class: "empty" }, [
        h("div", { class: "empty-ico", text: "🚀" }),
        h("p", { text: "Bienvenue sur NexFleet ! Ajoutez votre premier véhicule pour démarrer le pilotage du parc." }),
        h("button", { class: "btn btn-primary btn-sm", onclick: () => navigate("vehicles"), html: svg("plus") + " Ajouter un véhicule" }),
      ]),
    ]));
  }

  const controlsByMonth = (data.controls_by_month || []).filter((m) => m.count > 0);

  const left = h("div", { class: "panel glass reveal reveal-2" }, [
    h("div", { class: "panel-title", html: "Contrôles — 6 derniers mois" }),
    h("div", { class: "panel-sub", text: "Activité de conformité du parc" }),
    h("div", { class: "chart-wrap", style: "height:230px" }, [h("canvas", { id: "chart-bars" })]),
    h("div", { class: "panel-title", style: "margin-top:24px", html: "Répartition par carburant" }),
    h("div", { class: "panel-sub", text: "Mix énergétique du parc" }),
    h("div", { class: "chart-wrap", style: "height:210px" }, [h("canvas", { id: "chart-donut" })]),
    h("div", { class: "legend" }, carbEntries.map((c, i) =>
      h("span", { class: "legend-item" }, [
        h("span", { class: "legend-dot", style: `background:${palette[i % palette.length]}` }),
        h("span", { text: `${c[0]} · ${c[1]}` }),
      ]))),
    h("div", { class: "panel-title", style: "margin-top:24px", html: "Coûts de maintenance par véhicule" }),
    h("div", { class: "panel-sub", text: "Total des interventions, en FCFA" }),
    h("div", { class: "chart-wrap", style: "height:210px" }, [h("canvas", { id: "chart-costs" })]),
  ]);

  const avgCostKm = (() => {
    const list = data.cost_per_km || [];
    if (!list.length) return 0;
    return list.reduce((a, c) => a + c.total, 0) / list.reduce((a, c) => a + Math.max(c.km, 1), 0);
  })();

  const right = h("div", { class: "panel glass reveal reveal-3" }, [
    h("div", { class: "panel-title", html: "Disponibilité du parc" }),
    h("div", { class: "panel-sub", text: "Part des véhicules en service" }),
    h("div", { class: "ring-progress" }, [
      h("canvas", { id: "chart-ring" }),
      h("div", { class: "ring-center" }, [
        h("strong", { id: "ring-value", text: "0%" }),
        h("small", { text: "en service" }),
      ]),
    ]),
    h("div", { class: "panel-title", style: "margin-top:24px", html: "Parc par site" }),
    h("div", { class: "panel-sub", text: "Répartition des affectations" }),
    h("div", { class: "chart-wrap", style: "height:180px" }, [h("canvas", { id: "chart-site" })]),
    h("div", { class: "legend" }, siteEntries.map((s, i) =>
      h("span", { class: "legend-item" }, [
        h("span", { class: "legend-dot", style: `background:${palette[(i + 2) % palette.length]}` }),
        h("span", { text: `${s[0]} · ${s[1]}` }),
      ]))),
    h("div", { class: "panel-title", style: "margin-top:24px", html: "Coût moyen d'exploitation" }),
    h("div", { class: "panel-sub", text: `Maintenance : ${fmtMoney(data.maintenance_total)} · vidanges : ${fmtMoney(data.vidanges_total || 0)} · ≈ ${avgCostKm.toLocaleString("fr-FR")} FCFA / km` }),
    h("div", { class: "panel-title", style: "margin-top:24px", html: "Alertes d'échéances" }),
    h("div", { class: "panel-sub", text: "Assurance · Vignette · Contrôle technique · Vidange" }),
  ]);

  const alertList = h("div", { class: "alert-list" });
  if ((data.alerts || []).length === 0) {
    alertList.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-ico", text: "🎉" }),
      h("p", { text: "Aucune échéance critique. Parc en ordre !" }),
    ]));
  } else {
    data.alerts.slice(0, 6).forEach((a) => {
      const danger = a.level === "danger";
      alertList.appendChild(h("div", { class: "alert-item " + (danger ? "danger" : "warning") }, [
        h("div", { class: "alert-ico", text: danger ? "🚨" : "⏰" }),
        h("div", { class: "alert-body" }, [
          h("strong", { text: `${a.vehicle} · ${a.immatriculation}` }),
          h("small", { text: a.msg }),
        ]),
        danger ? h("span", { class: "days-chip days-danger", text: a.label }) : null,
      ]));
    });
  }
  right.appendChild(alertList);

  const statusPanel = buildStatusPanel(data);
  const costPanel = buildTopCostsPanel(data);
  const feedPanel = buildFeedPanel(notifRes.events || []);
  const vgPanel = buildVidangesPanel(vgStats);
  const recentPanel = h("div", { class: "panel glass reveal reveal-4" }, [
    h("div", { class: "panel-title", html: "Flotte récente" }),
    h("div", { class: "panel-sub", text: "Derniers véhicules ajoutés" }),
  ]);
  try {
    const vres = await api("/api/vehicles");
    (vres.vehicles || []).slice(0, 5).forEach((v) => {
      recentPanel.appendChild(h("div", { class: "v-mini" }, [
        vehicleThumb(v, 38),
        h("div", { class: "v-mini-body" }, [
          h("strong", { text: `${v.marque} ${v.modele} · ${v.immatriculation}` }),
          h("small", { text: `${v.carburant} · ${fmtKm(v.kilometrage)}` }),
        ]),
        badgeForStatut(v.statut),
      ]));
    });
  } catch (_) {}

  root.innerHTML = "";
  root.append(
    statsGrid,
    h("div", { class: "dash-grid" }, [left, right]),
    h("div", { class: "dash-grid-3" }, [statusPanel, costPanel, vgPanel, feedPanel, recentPanel]),
  );

  requestAnimationFrame(() => {
    kpis.forEach((k, i) => {
      const node = document.getElementById("kpi-" + i);
      if (node) animateCounter(node, k.value, k.money ? " FCFA" : "");
    });
    const barsCanvas = document.getElementById("chart-bars");
    if (barsCanvas && controlsByMonth.length) {
      drawBars(barsCanvas, controlsByMonth.map((m) => m.month), controlsByMonth.map((m) => m.count));
    }
    const donutCanvas = document.getElementById("chart-donut");
    if (donutCanvas && carbVals.length) drawDonut(donutCanvas, carbVals, palette);
    drawRing(document.getElementById("chart-ring"), serviceRatio, "#34d399");
    const rv = document.getElementById("ring-value");
    if (rv) animateCounter(rv, dispoPct, "%");
    const costs = data.costs_by_vehicle || [];
    const costsCanvas = document.getElementById("chart-costs");
    if (costsCanvas && costs.length) {
      drawBars(costsCanvas, costs.map((c) => c.immatriculation), costs.map((c) => Number(c.total)), fmtFcfaShort);
    }
    const siteCanvas = document.getElementById("chart-site");
    if (siteCanvas && siteEntries.length) {
      drawDonut(siteCanvas, siteVals, palette);
    }
  });

  updateAlertBadge(data.alerts ? data.alerts.filter((a) => a.level === "danger").length : 0);
}

function buildStatusPanel(data) {
  const total = Math.max(data.total || 0, 1);
  const segs = [
    { label: "En service", count: data.en_service || 0, color: "#34d399" },
    { label: "En maintenance", count: data.en_maintenance || 0, color: "#fbbf24" },
    { label: "En panne", count: data.en_panne || 0, color: "#f87171" },
    { label: "Hors service", count: Math.max((data.total || 0) - (data.en_service || 0) - (data.en_maintenance || 0) - (data.en_panne || 0), 0), color: "#64748b" },
  ];
  const panel = h("div", { class: "panel glass reveal reveal-4" }, [
    h("div", { class: "panel-title", html: "Répartition des statuts" }),
    h("div", { class: "panel-sub", text: "État actuel de l'ensemble du parc" }),
    h("div", { class: "status-bar" }, segs.map((s) =>
      h("span", { class: "status-seg", style: `background:${s.color};flex:${s.count}` }, []))),
    h("div", { class: "status-legend" }, segs.map((s) =>
      h("span", { class: "status-legend-item" }, [
        h("span", { class: "legend-dot", style: `background:${s.color}` }),
        h("span", { text: `${s.label} · ${s.count}` }),
        h("strong", { text: `${Math.round((s.count / total) * 100)}%` }),
      ]))),
  ]);
  return panel;
}

function buildTopCostsPanel(data) {
  const panel = h("div", { class: "panel glass reveal reveal-4" }, [
    h("div", { class: "panel-title", html: "Top coûts maintenance" }),
    h("div", { class: "panel-sub", text: "Véhicules les plus coûteux à entretenir" }),
  ]);
  const costs = (data.costs_by_vehicle || []).filter((c) => Number(c.total) > 0).slice(0, 5);
  if (!costs.length) {
    panel.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-ico", text: "🛠️" }),
      h("p", { text: "Aucune intervention enregistrée pour le moment." }),
    ]));
    return panel;
  }
  const max = Math.max(...costs.map((c) => Number(c.total)), 1);
  const list = h("div", { class: "rank-list" });
  costs.forEach((c, i) => {
    list.appendChild(h("div", { class: "rank-item" }, [
      h("span", { class: "rank-pos" + (i < 3 ? " top" : ""), text: i + 1 }),
      h("div", { class: "rank-body" }, [
        h("div", { class: "rank-head" }, [
          h("strong", { text: `${c.marque} ${c.modele}` }),
          h("small", { text: c.immatriculation }),
        ]),
        h("div", { class: "rank-bar" }, [h("span", { class: "rank-fill", style: `width:${Math.round((Number(c.total) / max) * 100)}%` }, [])]),
      ]),
      h("span", { class: "rank-val", text: fmtFcfaShort(c.total) }),
    ]));
  });
  panel.appendChild(list);
  return panel;
}

function buildVidangesPanel(stats) {
  const panel = h("div", { class: "panel glass reveal reveal-4" }, [
    h("div", { class: "panel-title", html: "Prochaines vidanges" }),
    h("div", { class: "panel-sub", text: "Véhicules à passer à l'atelier" }),
  ]);
  const due = (stats.forecast || []).filter((f) => f.due).slice(0, 5);
  if (!due.length) {
    panel.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-ico", text: "🛢️" }),
      h("p", { text: "Aucune vidange à prévoir." }),
    ]));
    return panel;
  }
  const list = h("div", { class: "rank-list" });
  due.forEach((f) => {
    const over = f.km_left <= 0;
    list.appendChild(h("div", { class: "rank-item" }, [
      h("div", { class: "rank-body" }, [
        h("div", { class: "rank-head" }, [
          h("strong", { text: `${f.marque} ${f.modele}` }),
          h("small", { text: f.immatriculation }),
        ]),
        h("small", { style: "color:var(--text-dim)", text: over ? "vidange dépassée" : `${fmtKm(f.km_left)} restant · prochaine à ${fmtKm(f.km_due)} km` }),
      ]),
      h("span", { class: "badge " + (over ? "badge-danger" : "badge-maintenance"), text: over ? "En retard" : fmtKm(f.km_left) + " restant" }),
    ]));
  });
  panel.appendChild(list);
  panel.appendChild(h("div", { style: "text-align:right;margin-top:10px" }, [
    h("button", { class: "btn btn-ghost btn-sm", onclick: () => navigate("vidanges"), html: "Gérer →" }),
  ]));
  return panel;
}

function buildFeedPanel(events) {
  const panel = h("div", { class: "panel glass reveal reveal-4" }, [
    h("div", { class: "panel-title", html: "Activité récente" }),
    h("div", { class: "panel-sub", text: "Dernières actions enregistrées" }),
  ]);
  const list = h("div", { class: "feed-list" });
  if (!events.length) {
    panel.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-ico", text: "🕓" }),
      h("p", { text: "Aucune action enregistrée." }),
    ]));
    return panel;
  }
  events.slice(0, 6).forEach((e) => {
    list.appendChild(h("div", { class: "feed-item" }, [
      h("span", { class: "feed-ico", text: e.action === "login" ? "🔑" : e.action === "delete" ? "🗑️" : e.action === "create" ? "➕" : "✏️" }),
      h("div", { class: "feed-text" }, [
        h("strong", { text: `${e.username || "?"} · ${ACTION_LABEL[e.action] || e.action || ""}` }),
        h("small", { text: `${e.entity || ""}${e.details && typeof e.details === "object" && e.details.immatriculation ? " · " + e.details.immatriculation : ""}` }),
      ]),
      h("span", { class: "feed-time", text: fmtDateTime(e.created_at).split(" ").slice(1).join(" ") }),
    ]));
  });
  panel.appendChild(list);
  panel.appendChild(h("div", { style: "text-align:right;margin-top:10px" }, [
    h("button", { class: "btn btn-ghost btn-sm", onclick: () => navigate("activity"), html: "Tout voir →" }),
  ]));
  return panel;
}

function updateAlertBadge(n) {
  const b = document.getElementById("badge-alerts");
  b.hidden = n === 0;
  b.textContent = n;
}

/* ==========================================================================
   VUE : VÉHICULES
   ========================================================================== */
async function viewVehicles(root) {
  let sites = [];
  try { sites = Object.keys((await api("/api/stats")).by_site || {}); } catch (_) {}
  const toolbar = h("div", { class: "toolbar" }, [
    h("div", { class: "search-wrap" }, [h("input", {
      id: "veh-search", type: "search", placeholder: "Rechercher immatriculation, marque…",
      oninput: debounce(() => loadVehicles(), 300),
    })]),
    h("select", { class: "select", id: "veh-statut", onchange: loadVehicles }, [
      h("option", { value: "", text: "Tous les statuts" }),
      ...STATUTS.map((s) => h("option", { value: s, text: s })),
    ]),
    h("select", { class: "select", id: "veh-carburant", onchange: loadVehicles }, [
      h("option", { value: "", text: "Tous carburants" }),
      ...CARBURANTS.map((c) => h("option", { value: c, text: c })),
    ]),
    h("select", { class: "select", id: "veh-site", onchange: loadVehicles }, [
      h("option", { value: "", text: "Tous les sites" }),
      ...sites.map((s) => h("option", { value: s, text: s })),
    ]),
    h("div", { class: "spacer" }),
    h("button", { class: "btn btn-ghost btn-sm", onclick: () => importModal(), html: svg("upload") + " Importer" }),
    h("button", { class: "btn btn-primary btn-sm", onclick: () => vehicleModal(null), html: svg("plus") + " Ajouter <span class='btn-shine'></span>" }),
  ]);

  const tableCard = h("div", { class: "table-card glass reveal reveal-1" }, [
    h("div", { class: "table-scroll" }, [h("table", { class: "data", id: "veh-table" })]),
  ]);

  root.innerHTML = "";
  root.append(toolbar, tableCard);
  loadVehicles();
}

async function loadVehicles() {
  const table = document.getElementById("veh-table");
  const search = (document.getElementById("veh-search") || {}).value || "";
  const statut = (document.getElementById("veh-statut") || {}).value || "";
  const carburant = (document.getElementById("veh-carburant") || {}).value || "";
  const site = (document.getElementById("veh-site") || {}).value || "";
  const qs = new URLSearchParams();
  if (search) qs.set("search", search);
  if (statut) qs.set("statut", statut);
  if (carburant) qs.set("carburant", carburant);
  if (site) qs.set("site", site);
  const res = await api("/api/vehicles?" + qs.toString());
  const vehs = res.vehicles || [];

  const isAdmin = (state.user || {}).role === "admin";
  table.innerHTML = "";
  table.appendChild(h("thead", null, [h("tr", null, [
    h("th", { text: "" }), h("th", { text: "Immatriculation" }), h("th", { text: "Véhicule" }),
    h("th", { text: "Direction" }), h("th", { text: "Année" }), h("th", { text: "Carburant" }),
    h("th", { text: "Affectation" }), h("th", { text: "Kilométrage" }), h("th", { text: "Statut" }),
    h("th", { text: "Assurance" }), h("th", { text: "CT" }),
    h("th", { text: "", style: "text-align:right" }),
  ])]));

  if (!vehs.length) {
    table.appendChild(emptyRow(12, "🚗", search ? "Aucun résultat pour cette recherche." : "Aucun véhicule. Ajoutez votre premier véhicule !"));
    return;
  }

  const tbody = h("tbody", null, []);
  vehs.forEach((v) => {
    tbody.appendChild(h("tr", null, [
      h("td", { class: "td-thumb" }, [vehicleThumb(v, 40)]),
      h("td", { class: "td-mono", text: v.immatriculation }),
      h("td", null, [h("div", { class: "td-strong", text: `${v.marque} ${v.modele}` }), h("small", { class: "td-dim", text: v.type })]),
      h("td", { class: "td-dim", text: v.direction || "—" }),
      h("td", { class: "td-dim", text: v.annee || "—" }),
      h("td", { text: v.carburant }),
      h("td", { class: "td-dim", text: v.affectation || "—" }),
      h("td", { class: "td-dim", text: fmtKm(v.kilometrage) }),
      h("td", null, [badgeForStatut(v.statut)]),
      h("td", null, [daysChip(v.assurance_exp)]),
      h("td", null, [daysChip(v.ctrl_tech_exp)]),
      h("td", null, [h("div", { class: "row-actions" }, [
        h("button", { class: "mini-btn info", title: "Fiche complète", onclick: () => vehicleDetailDrawer(v), html: svg("eye") }),
        h("button", { class: "mini-btn success", title: "Fiche de contrôle PDF", onclick: () => getVehiclePdf(v), html: svg("file") }),
        h("button", { class: "mini-btn", title: "Modifier", onclick: () => vehicleModal(v), html: svg("pencil") }),
        isAdmin ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer le véhicule", `Supprimer ${v.marque} ${v.modele} (${v.immatriculation}) ? Cette action est irréversible.`, () => delVehicle(v)), html: svg("trash") }) : null,
      ])]),
    ]));
  });
  table.appendChild(tbody);
}

async function getVehiclePdf(v) {
  toast("Génération de la fiche PDF…", "info");
  try {
    await downloadPdf(`/api/vehicles/${v.id}/pdf`, `Fiche_controle_${v.immatriculation}.pdf`);
    toast("Fiche PDF téléchargée.", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function delVehicle(v) {
  try {
    await api(`/api/vehicles/${v.id}`, "DELETE");
    toast("Véhicule supprimé.", "success");
    loadVehicles();
  } catch (err) {
    toast(err.message, "error");
  }
}

function vehicleModal(v) {
  const editing = !!v;
  const val = (f) => v ? esc(v[f] || "") : "";
  let pendingPhoto = null;
  let removePhoto = false;
  openModal(`
    <div class="modal-head"><h4>${editing ? "Modifier le véhicule" : "Nouveau véhicule"}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="vehicle">
      <div class="veh-photo-row">
        <div class="veh-photo-preview${v && v.photo ? " zoomable" : ""}" id="v-photo-preview" title="${v && v.photo ? "Cliquer pour agrandir" : ""}">${v && v.photo ? `<img src="${esc(v.photo_thumb || v.photo)}" alt="photo" />` : `<span class="veh-photo-ph">${esc((v && v.immatriculation || "V")[0])}</span>`}</div>
        <div class="veh-photo-actions">
          <button type="button" class="btn btn-ghost btn-sm" id="v-photo-btn">${svg("upload")} Choisir une photo</button>
          <button type="button" class="btn btn-ghost btn-sm danger-text" id="v-photo-del" ${v && v.photo ? "" : "hidden"}>${svg("trash")} Retirer</button>
          <small class="veh-photo-hint">JPG, PNG ou WebP — 5 Mo max. La photo est visible dans la liste et la fiche du véhicule.</small>
          <input id="v-photo-file" type="file" accept="image/jpeg,image/png,image/webp,image/gif" style="display:none" />
        </div>
      </div>
      <div class="form-grid">
        <div class="field"><label>Immatriculation *</label>
          <div class="input-wrap"><input id="v-imm" type="text" placeholder="AB-123-CD" value="${val("immatriculation")}" required /></div></div>
        <div class="field"><label>Statut</label>
          <select class="select" id="v-statut" style="width:100%">
            ${STATUTS.map((s) => `<option ${v && v.statut === s ? "selected" : ""}>${s}</option>`).join("")}
          </select></div>
        <div class="field"><label>Marque *</label>
          <div class="input-wrap"><input id="v-marque" type="text" placeholder="Renault" value="${val("marque")}" required /></div></div>
        <div class="field"><label>Modèle *</label>
          <div class="input-wrap"><input id="v-modele" type="text" placeholder="Master" value="${val("modele")}" required /></div></div>
        <div class="field"><label>Année</label>
          <div class="input-wrap"><input id="v-annee" type="number" min="1970" max="2100" value="${val("annee")}" /></div></div>
        <div class="field"><label>Kilométrage</label>
          <div class="input-wrap"><input id="v-km" type="number" min="0" value="${val("kilometrage")}" /></div></div>
        <div class="field"><label>Type</label>
          <select class="select" id="v-type" style="width:100%">
            ${TYPES_VEH.map((t) => `<option ${v && v.type === t ? "selected" : ""}>${t}</option>`).join("")}
          </select></div>
        <div class="field"><label>Carburant</label>
          <select class="select" id="v-carburant" style="width:100%">
            ${CARBURANTS.map((c) => `<option ${v && v.carburant === c ? "selected" : ""}>${c}</option>`).join("")}
          </select></div>
        <div class="field"><label>Direction *</label>
          <div class="input-wrap"><input id="v-direction" type="text" placeholder="Direction Générale, DRH, DAF…" value="${val("direction")}" maxlength="120" required /></div></div>
        <div class="field"><label>Affectation</label>
          <div class="input-wrap"><input id="v-affectation" type="text" placeholder="Dépôt, agence, site…" value="${val("affectation")}" maxlength="120" /></div></div>
        <div class="field"><label>Échéance vignette <button type="button" class="mini-btn" data-set-date="v-vig" style="width:22px;height:22px;font-size:10px">auj.</button></label>
          <div class="input-wrap"><input id="v-vig" type="date" value="${val("vignette_exp")}" /></div></div>
        <div class="field"><label>Note vignette</label>
          <div class="input-wrap"><input id="v-vig-note" type="text" placeholder="Ex. : paiement en cours…" value="${val("vignette_note")}" maxlength="200" /></div></div>
        <div class="field"><label>Échéance assurance <button type="button" class="mini-btn" data-set-date="v-ass" style="width:22px;height:22px;font-size:10px">auj.</button></label>
          <div class="input-wrap"><input id="v-ass" type="date" value="${val("assurance_exp")}" /></div></div>
        <div class="field full"><label>Échéance contrôle technique <button type="button" class="mini-btn" data-set-date="v-ct" style="width:22px;height:22px;font-size:10px">auj.</button></label>
          <div class="input-wrap"><input id="v-ct" type="date" value="${val("ctrl_tech_exp")}" /></div></div>
        <div class="field full"><label>Note contrôle technique</label>
          <div class="input-wrap"><input id="v-ct-note" type="text" placeholder="Ex. : rendez-vous garage le…" value="${val("ct_note")}" maxlength="200" /></div></div>
        
        <div class="field"><label>N° Carte grise</label>
  <div class="input-wrap"><input id="v-carte_grise" type="text" placeholder="CG-12345-A" value="${val("carte_grise") || ""}" maxlength="30" /></div></div>
          <div class="field"><label>Expiration carte grise <button type="button" class="mini-btn" data-set-date="v-cg" style="width:22px;height:22px;font-size:10px">auj.</button></label>
  <div class="input-wrap"><input id="v-cg" type="date" value="${val("carte_grise_exp") || ""}" /></div></div>
        <div class="field full"><label>Note carte grise</label>
          <div class="input-wrap"><input id="v-cg-note" type="text" placeholder="Ex. : dossier en cours…" value="${val("carte_grise_note")}" maxlength="200" /></div></div>
       
          <div class="field"><label>N° Châssis (VIN)</label>
        <div class="input-wrap"><input id="v-chassis" type="text" placeholder="VF1MA2E0H…" value="${val("num_chassis")}" maxlength="30" /></div></div>
        <div class="field"><label>N° Moteur</label>
          <div class="input-wrap"><input id="v-moteur" type="text" placeholder="F4R710…" value="${val("num_moteur")}" maxlength="30" /></div></div>
  
        <div class="field"><label>Chevaux (CV)</label>
          <div class="input-wrap"><input id="v-cv" type="number" min="0" max="1000" placeholder="120" value="${val("cv")}" /></div></div>
        <div class="field"><label>Latitude GPS</label>
          <div class="input-wrap"><input id="v-lat" type="number" step="any" min="-90" max="90" placeholder="48.86" value="${val("lat")}" /></div></div>
        <div class="field"><label>Longitude GPS</label>
          <div class="input-wrap"><input id="v-lng" type="number" step="any" min="-180" max="180" placeholder="2.35" value="${val("lng")}" /></div></div>

      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button type="button" class="btn btn-ghost" data-close>Annuler</button>
        <button type="button" class="btn btn-primary" id="veh-save">${editing ? "Enregistrer" : "Ajouter"} <span class="btn-shine"></span></button>
      </div>
    </form>`, false);

  const photoInput = document.getElementById("v-photo-file");
  const photoPreview = document.getElementById("v-photo-preview");
  const photoDel = document.getElementById("v-photo-del");
  document.getElementById("v-photo-btn").addEventListener("click", () => photoInput.click());
  photoPreview.addEventListener("click", () => {
    const img = photoPreview.querySelector("img");
    if (!img) return;
    const meta = { marque: document.getElementById("v-marque").value, modele: document.getElementById("v-modele").value, immatriculation: document.getElementById("v-imm").value };
    viewVehiclePhoto(meta, img.src);
  });
  photoInput.addEventListener("change", () => {
    if (!photoInput.files.length) return;
    pendingPhoto = photoInput.files[0];
    removePhoto = false;
    const url = URL.createObjectURL(pendingPhoto);
    photoPreview.innerHTML = `<img src="${url}" alt="photo" />`;
    photoPreview.classList.add("zoomable");
    photoPreview.title = "Cliquer pour agrandir";
    if (photoDel) photoDel.hidden = false;
  });
  if (photoDel) photoDel.addEventListener("click", () => {
    pendingPhoto = null;
    removePhoto = true;
    photoInput.value = "";
    photoPreview.innerHTML = `<span class="veh-photo-ph">${esc((v && v.immatriculation || "V")[0])}</span>`;
    photoPreview.classList.remove("zoomable");
    photoPreview.title = "";
    photoDel.hidden = true;
  });

  let saving = false;
  document.getElementById("veh-save").addEventListener("click", async () => {
    if (saving) return;
    saving = true;
    const btn = document.getElementById("veh-save");
    btn.disabled = true;
    const body = {
      immatriculation: document.getElementById("v-imm").value,
      marque: document.getElementById("v-marque").value,
      modele: document.getElementById("v-modele").value,
      annee: document.getElementById("v-annee").value || null,
      kilometrage: document.getElementById("v-km").value || 0,
      type: document.getElementById("v-type").value,
      carburant: document.getElementById("v-carburant").value,
      affectation: document.getElementById("v-affectation").value.trim() || null,
      direction: document.getElementById("v-direction").value.trim() || null,
      statut: document.getElementById("v-statut").value,
      vignette_exp: document.getElementById("v-vig").value || null,
      assurance_exp: document.getElementById("v-ass").value || null,
      ctrl_tech_exp: document.getElementById("v-ct").value || null,
      vignette_note: document.getElementById("v-vig-note").value.trim() || null,
      ct_note: document.getElementById("v-ct-note").value.trim() || null,
      carte_grise_note: document.getElementById("v-cg-note").value.trim() || null,
      num_chassis: document.getElementById("v-chassis").value || null,
      num_moteur: document.getElementById("v-moteur").value || null,
      carte_grise: document.getElementById("v-carte_grise").value || null,
      carte_grise_exp: document.getElementById("v-cg").value || null,
      cv: document.getElementById("v-cv").value || null,
      lat: document.getElementById("v-lat").value || null,
      lng: document.getElementById("v-lng").value || null,
    };
    try {
      let vid = v && v.id;
      if (editing) await api(`/api/vehicles/${v.id}`, "PUT", body);
      else { const r = await api("/api/vehicles", "POST", body); vid = r.id; }
      if (pendingPhoto) await uploadVehiclePhoto(vid, pendingPhoto);
      else if (removePhoto && vid) await api(`/api/vehicles/${vid}/photo`, "DELETE");
      closeModal();
      toast(editing ? "Véhicule mis à jour." : "Véhicule ajouté !", "success");
      loadVehicles();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      saving = false;
      btn.disabled = false;
    }
  });
}

async function uploadVehiclePhoto(vid, file) {
  const fd = new FormData();
  fd.append("photo", file);
  const res = await fetch(`/api/vehicles/${vid}/photo`, {
    method: "POST",
    headers: { Authorization: "Bearer " + state.token },
    body: fd,
  });
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) throw new Error((data && data.error) || "Impossible d'envoyer la photo.");
  return data;
}

/* ==========================================================================
   VUE : CONDUCTEURS
   ========================================================================== */
async function viewDrivers(root) {
  root.innerHTML = "";
  root.appendChild(h("div", { class: "toolbar" }, [
    h("div", { class: "spacer" }),
    h("button", { class: "btn btn-primary btn-sm", onclick: () => driverModal(null), html: svg("plus") + " Ajouter <span class='btn-shine'></span>" }),
  ]));
  const card = h("div", { class: "table-card glass reveal reveal-1" }, [
    h("div", { class: "table-scroll" }, [h("table", { class: "data", id: "drv-table" })]),
  ]);
  root.appendChild(card);
  loadDrivers();
}

async function loadDrivers() {
  const table = document.getElementById("drv-table");
  const res = await api("/api/drivers");
  const drv = res.drivers || [];
  const isAdmin = (state.user || {}).role === "admin";
  table.innerHTML = "";
  table.appendChild(h("thead", null, [h("tr", null, [
    h("th", { text: "Conducteur" }), h("th", { text: "Matricule" }), h("th", { text: "Email" }),
    h("th", { text: "Téléphone" }), h("th", { text: "Permis" }), h("th", { text: "Validité permis" }),
    h("th", { text: "Expiration CNI" }), h("th", { text: "", style: "text-align:right" }),
  ])]));
  if (!drv.length) {
    table.appendChild(emptyRow(8, "🪪", "Aucun conducteur enregistré."));
    return;
  }
  const tbody = h("tbody", null, []);
  drv.forEach((d) => {
    tbody.appendChild(h("tr", null, [
      h("td", null, [h("div", { class: "td-strong", text: `${d.prenom} ${d.nom}` }), h("small", { class: "td-dim", text: "#" + d.id })]),
      h("td", { class: "td-mono", text: d.matricule || "—" }),
      h("td", { class: "td-dim", text: d.email || "—" }),
      h("td", { class: "td-dim", text: d.telephone || "—" }),
      h("td", { class: "td-mono", text: d.permis || "—" }),
      h("td", null, [daysChip(d.permis_exp)]),
      h("td", null, [daysChip(d.cni_exp)]),
      h("td", null, [h("div", { class: "row-actions" }, [
        h("button", { class: "mini-btn", title: "Modifier", onclick: () => driverModal(d), html: svg("pencil") }),
        isAdmin ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer le conducteur", `Supprimer ${d.prenom} ${d.nom} ?`, () => delDriver(d)), html: svg("trash") }) : null,
      ])]),
    ]));
  });
  table.appendChild(tbody);
}

async function delDriver(d) {
  try {
    await api(`/api/drivers/${d.id}`, "DELETE");
    toast("Conducteur supprimé.", "success");
    loadDrivers();
  } catch (err) {
    toast(err.message, "error");
  }
}

function driverModal(d) {
  const editing = !!d;
  const val = (f) => d ? esc(d[f] || "") : "";
  openModal(`
    <div class="modal-head"><h4>${editing ? "Modifier le conducteur" : "Nouveau conducteur"}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="driver">
      <div class="form-grid">
        <div class="field"><label>Prénom *</label>
          <div class="input-wrap"><input id="d-prenom" type="text" value="${val("prenom")}" required /></div></div>
        <div class="field"><label>Nom *</label>
          <div class="input-wrap"><input id="d-nom" type="text" value="${val("nom")}" required /></div></div>
        <div class="field"><label>Matricule</label>
          <div class="input-wrap"><input id="d-matricule" type="text" value="${val("matricule")}" placeholder="MAT-00123" /></div></div>
        <div class="field"><label>Email</label>
          <div class="input-wrap"><input id="d-email" type="email" value="${val("email")}" /></div></div>
        <div class="field"><label>Téléphone</label>
          <div class="input-wrap"><input id="d-tel" type="tel" value="${val("telephone")}" placeholder="06 12 34 56 78" /></div></div>
        <div class="field"><label>N° permis</label>
          <div class="input-wrap"><input id="d-permis" type="text" value="${val("permis")}" /></div></div>
        <div class="field"><label>Validité du permis <button type="button" class="mini-btn" data-set-date="d-permis-exp" style="width:22px;height:22px;font-size:10px">auj.</button></label>
          <div class="input-wrap"><input id="d-permis-exp" type="date" value="${val("permis_exp")}" /></div></div>
        <div class="field"><label>Expiration CNI <button type="button" class="mini-btn" data-set-date="d-cni-exp" style="width:22px;height:22px;font-size:10px">auj.</button></label>
          <div class="input-wrap"><input id="d-cni-exp" type="date" value="${val("cni_exp")}" /></div></div>
        <div class="field"><label>N° CNI</label>
          <div class="input-wrap"><input id="d-cni" type="text" value="${val("cni")}" maxlength="30" /></div></div>
        <div class="field"><label>Note permis</label>
          <div class="input-wrap"><input id="d-permis-note" type="text" value="${val("permis_note")}" maxlength="200" /></div></div>
        <div class="field"><label>Note CNI</label>
          <div class="input-wrap"><input id="d-cni-note" type="text" value="${val("cni_note")}" maxlength="200" /></div></div>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button type="button" class="btn btn-ghost" data-close>Annuler</button>
        <button type="button" class="btn btn-primary" id="drv-save">${editing ? "Enregistrer" : "Ajouter"} <span class="btn-shine"></span></button>
      </div>
    </form>`);

  document.getElementById("drv-save").addEventListener("click", async () => {
    const body = {
      prenom: document.getElementById("d-prenom").value,
      nom: document.getElementById("d-nom").value,
      matricule: document.getElementById("d-matricule").value,
      email: document.getElementById("d-email").value,
      telephone: document.getElementById("d-tel").value,
      permis: document.getElementById("d-permis").value,
      permis_exp: document.getElementById("d-permis-exp").value || null,
      cni: document.getElementById("d-cni").value.trim() || null,
      cni_exp: document.getElementById("d-cni-exp").value || null,
      permis_note: document.getElementById("d-permis-note").value.trim() || null,
      cni_note: document.getElementById("d-cni-note").value.trim() || null,
    };
    try {
      if (editing) await api(`/api/drivers/${d.id}`, "PUT", body);
      else await api("/api/drivers", "POST", body);
      closeModal();
      toast(editing ? "Conducteur mis à jour." : "Conducteur ajouté !", "success");
      loadDrivers();
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

/* ==========================================================================
   VUE : CONTRÔLES
   ========================================================================== */
async function viewControls(root) {
  const res = await Promise.all([api("/api/controls"), api("/api/vehicles"), api("/api/drivers")]);
  const controls = res[0].controls || [];
  const vehicles = res[1].vehicles || [];
  const drivers = res[2].drivers || [];
  state.cache.controls = { vehicles, drivers };

  const isAdmin = (state.user || {}).role === "admin";
  const card = h("div", { class: "table-card glass reveal reveal-1" }, [h("div", { class: "table-scroll" }, [h("table", { class: "data" })] )]);
  const tbl = card.querySelector("table");
  tbl.appendChild(h("thead", null, [h("tr", null, [
    h("th", { text: "Date" }), h("th", { text: "Véhicule" }), h("th", { text: "Conducteur" }),
    h("th", { text: "Type" }), h("th", { text: "Résultat" }), h("th", { text: "Observations" }),
    h("th", { text: "", style: "text-align:right" }),
  ])]));

  root.innerHTML = "";
  root.append(
    h("div", { class: "toolbar" }, [
      h("div", { class: "panel-sub", style: "margin:0", text: `${controls.length} contrôle(s) enregistré(s)` }),
      h("div", { class: "spacer" }),
      h("button", { class: "btn btn-primary btn-sm", onclick: () => controlModal(null, vehicles, drivers), html: svg("plus") + " Nouveau contrôle <span class='btn-shine'></span>" }),
    ]),
    card,
  );

  if (!controls.length) {
    tbl.appendChild(emptyRow(7, "✅", "Aucun contrôle. Lancez le premier contrôle d'un véhicule."));
    return;
  }
  const tbody = h("tbody", null, []);
  controls.forEach((c) => {
    const vname = c.immatriculation ? `${c.marque} ${c.modele} · ${c.immatriculation}` : "—";
    const dname = c.d_prenom ? `${c.d_prenom} ${c.d_nom}` : "—";
    tbody.appendChild(h("tr", null, [
      h("td", { class: "td-dim", text: fmtDate(c.date) }),
      h("td", { class: "td-strong", text: vname }),
      h("td", { class: "td-dim", text: dname }),
      h("td", { text: c.type }),
      h("td", null, [badgeResultat(c.resultat)]),
      h("td", { class: "td-dim", html: c.notes ? esc(c.notes).slice(0, 40) + (c.notes.length > 40 ? "…" : "") : "—" }),
      h("td", null, [h("div", { class: "row-actions" }, [
        h("button", { class: "mini-btn", title: "Modifier", onclick: () => controlModal(c, vehicles, drivers), html: svg("pencil") }),
        isAdmin ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer le contrôle", "Supprimer ce contrôle ?", () => delControl(c)), html: svg("trash") }) : null,
      ])]),
    ]));
  });
  tbl.appendChild(tbody);
}

async function delControl(c) {
  try {
    await api(`/api/controls/${c.id}`, "DELETE");
    toast("Contrôle supprimé.", "success");
    navigate("controls");
  } catch (err) {
    toast(err.message, "error");
  }
}

function controlModal(c, vehicles, drivers) {
  const editing = !!c;
  let items = c ? (typeof c.items === "string" ? safeParse(c.items) : c.items || {}) : {};
  const val = (f, dft) => c ? esc(c[f] || dft) : dft;

  const box = openModal(`
    <div class="modal-head"><h4>${editing ? "Modifier le contrôle" : "Nouveau contrôle"}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="control">
      <div class="form-grid">
        <div class="field"><label>Véhicule *</label>
          <select class="select" id="c-veh" style="width:100%">
            ${vehicles.map((v) => `<option value="${v.id}" ${c && c.vehicle_id === v.id ? "selected" : ""}>${esc(v.marque)} ${esc(v.modele)} · ${esc(v.immatriculation)}</option>`).join("")}
          </select></div>
        <div class="field"><label>Conducteur</label>
          <select class="select" id="c-drv" style="width:100%">
            <option value="">— Non affecté —</option>
            ${drivers.map((d) => `<option value="${d.id}" ${c && c.driver_id === d.id ? "selected" : ""}>${esc(d.prenom)} ${esc(d.nom)}</option>`).join("")}
          </select></div>
        <div class="field"><label>Date *</label>
          <div class="input-wrap"><input id="c-date" type="date" value="${val("date", new Date().toISOString().slice(0, 10))}" /></div></div>
        <div class="field"><label>Type</label>
          <select class="select" id="c-type" style="width:100%">
            <option ${(!c || c.type === "Contrôle technique") ? "selected" : ""}>Contrôle technique</option>
            <option ${c && c.type === "Contrôle d'usage" ? "selected" : ""}>Contrôle d'usage</option>
            <option ${c && c.type === "Contrôle de départ" ? "selected" : ""}>Contrôle de départ</option>
            <option ${c && c.type === "Contrôle de retour" ? "selected" : ""}>Contrôle de retour</option>
          </select></div>
        <div class="field full"><label>Résultat</label>
          <select class="select" id="c-result" style="width:100%">
            <option ${(!c || c.resultat === "Conforme") ? "selected" : ""}>Conforme</option>
            <option ${c && c.resultat === "À surveiller" ? "selected" : ""}>À surveiller</option>
            <option ${c && c.resultat === "Non conforme" ? "selected" : ""}>Non conforme</option>
            <option ${c && c.resultat === "En cours" ? "selected" : ""}>En cours</option>
          </select></div>
      </div>
      <div class="field full">
        <label>Points de contrôle — cochez « non conforme » pour signaler</label>
        <div class="check-group" id="check-group">
          ${CHECKLIST.map((name) => {
            const st = items[name] || "";
            const cls = st === "Non conforme" ? "no" : st === "À surveiller" ? "watch" : st === "Conforme" ? "ok" : "";
            return `<label class="check-item ${cls}" data-name="${esc(name)}">
              <input type="checkbox" data-state="bad" ${st === "Non conforme" ? "checked" : ""}>
              <span class="check-text">${esc(name)}</span>
            </label>`;
          }).join("")}
        </div>
        <small>Astuce : cochez pour marquer un point NON conforme ; cliquez ensuite sur un point pour changer son état.</small>
      </div>
      <div class="field full"><label>Observations</label>
        <div class="input-wrap"><textarea id="c-notes" rows="3" style="width:100%;resize:vertical;background:rgba(255,255,255,0.04);border:1px solid var(--border-strong);border-radius:12px;padding:12px;color:var(--text);font-family:var(--font);outline:none">${val("notes", "")}</textarea></div></div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button type="button" class="btn btn-ghost" data-close>Annuler</button>
        <button type="button" class="btn btn-primary" id="ctl-save">${editing ? "Enregistrer" : "Créer"} <span class="btn-shine"></span></button>
      </div>
    </form>`, true);

  // états des points de contrôle : click cycle Conforme → À surveiller → Non conforme
  $$("#check-group .check-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      if (e.target.tagName === "INPUT") return;
      e.preventDefault();
      const cur = item.classList.contains("no") ? "bad" : item.classList.contains("watch") ? "warn" : "ok";
      const cycle = { ok: "watch", watch: "no", no: "ok" };
      const next = cycle[cur];
      item.classList.remove("ok", "watch", "no");
      if (next === "watch") item.classList.add("watch");
      if (next === "no") item.classList.add("no");
      if (next === "ok") item.classList.add("ok");
      const cb = item.querySelector("input");
      if (cb) cb.checked = next === "no";
    });
  });

  document.getElementById("ctl-save").addEventListener("click", async () => {
    const itemsObj = {};
    $$("#check-group .check-item").forEach((item) => {
      const name = item.dataset.name;
      itemsObj[name] = item.classList.contains("no") ? "Non conforme"
        : item.classList.contains("watch") ? "À surveiller" : "Conforme";
    });
    const body = {
      vehicle_id: Number(document.getElementById("c-veh").value),
      driver_id: document.getElementById("c-drv").value ? Number(document.getElementById("c-drv").value) : null,
      date: document.getElementById("c-date").value,
      type: document.getElementById("c-type").value,
      resultat: document.getElementById("c-result").value,
      notes: document.getElementById("c-notes").value,
      items: itemsObj,
    };
    try {
      if (editing) await api(`/api/controls/${c.id}`, "PUT", body);
      else await api("/api/controls", "POST", body);
      closeModal();
      toast("Contrôle enregistré.", "success");
      navigate("controls");
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

function safeParse(s) {
  try { return JSON.parse(s); } catch (_) { return {}; }
}

/* ==========================================================================
   VUE : MAINTENANCE
   ========================================================================== */
async function viewMaintenance(root) {
  const res = await Promise.all([api("/api/maintenance"), api("/api/vehicles")]);
  const items = res[0].maintenance || [];
  const vehicles = res[1].vehicles || [];
  const isAdmin = (state.user || {}).role === "admin";
  let totalCost = 0;
  items.forEach((m) => (totalCost += Number(m.cout) || 0));

  const card = h("div", { class: "table-card glass reveal reveal-1" }, [h("div", { class: "table-scroll" }, [h("table", { class: "data" })] )]);
  const tbl = card.querySelector("table");
  tbl.appendChild(h("thead", null, [h("tr", null, [
    h("th", { text: "Date" }), h("th", { text: "Véhicule" }), h("th", { text: "Intervention" }),
    h("th", { text: "Coût" }), h("th", { text: "Garage" }), h("th", { text: "", style: "text-align:right" }),
  ])]));

  root.innerHTML = "";
  root.append(
    h("div", { class: "toolbar" }, [
      h("div", { class: "panel-sub", style: "margin:0", text: `${items.length} intervention(s) · coût total ${fmtMoney(totalCost)}` }),
      h("div", { class: "spacer" }),
      h("button", { class: "btn btn-primary btn-sm", onclick: () => maintenanceModal(null, vehicles), html: svg("plus") + " Intervention <span class='btn-shine'></span>" }),
    ]),
    card,
  );

  if (!items.length) {
    tbl.appendChild(emptyRow(6, "🔧", "Aucune intervention de maintenance."));
    return;
  }
  const tbody = h("tbody", null, []);
  items.forEach((m) => {
    const vname = m.immatriculation ? `${m.marque} ${m.modele} · ${m.immatriculation}` : "—";
    tbody.appendChild(h("tr", null, [
      h("td", { class: "td-dim", text: fmtDate(m.date) }),
      h("td", { class: "td-strong", text: vname }),
      h("td", null, [h("span", { class: "badge badge-info", text: m.type })]),
      h("td", { class: "td-mono", text: fmtMoney(m.cout) }),
      h("td", { class: "td-dim", text: m.garage || "—" }),
      h("td", null, [h("div", { class: "row-actions" }, [
        h("button", { class: "mini-btn", title: "Modifier", onclick: () => maintenanceModal(m, vehicles), html: svg("pencil") }),
        isAdmin ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer l'intervention", "Supprimer cette intervention ?", () => delMaintenance(m)), html: svg("trash") }) : null,
      ])]),
    ]));
  });
  tbl.appendChild(tbody);
}

async function delMaintenance(m) {
  try {
    await api(`/api/maintenance/${m.id}`, "DELETE");
    toast("Intervention supprimée.", "success");
    navigate("maintenance");
  } catch (err) {
    toast(err.message, "error");
  }
}

function maintenanceModal(m, vehicles) {
  const editing = !!m;
  const val = (f, dft) => m ? esc(m[f] || dft) : dft;
  openModal(`
    <div class="modal-head"><h4>${editing ? "Modifier l'intervention" : "Nouvelle intervention"}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="maintenance">
      <div class="form-grid">
        <div class="field full"><label>Véhicule *</label>
          <select class="select" id="m-veh" style="width:100%">
            ${vehicles.map((v) => `<option value="${v.id}" ${m && m.vehicle_id === v.id ? "selected" : ""}>${esc(v.marque)} ${esc(v.modele)} · ${esc(v.immatriculation)}</option>`).join("")}
          </select></div>
        <div class="field"><label>Type d'intervention</label>
          <select class="select" id="m-type" style="width:100%">
            ${MAINT_CATEGORIES.map((t) => `<option ${m && m.type === t ? "selected" : ""}>${t}</option>`).join("")}
          </select></div>
        <div class="field"><label>Date</label>
          <div class="input-wrap"><input id="m-date" type="date" value="${val("date", new Date().toISOString().slice(0, 10))}" /></div></div>
        <div class="field"><label>Coût (FCFA)</label>
          <div class="input-wrap"><input id="m-cout" type="number" min="0" step="0.01" value="${val("cout", 0)}" /></div></div>
        <div class="field"><label>Garage</label>
          <div class="input-wrap"><input id="m-garage" type="text" value="${val("garage")}" placeholder="Garage NexAUTO" /></div></div>
        <div class="field full"><label>Notes</label>
          <div class="input-wrap"><textarea id="m-notes" rows="2" style="width:100%;resize:vertical;background:rgba(255,255,255,0.04);border:1px solid var(--border-strong);border-radius:12px;padding:12px;color:var(--text);font-family:var(--font);outline:none">${val("notes", "")}</textarea></div></div>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button type="button" class="btn btn-ghost" data-close>Annuler</button>
        <button type="button" class="btn btn-primary" id="mnt-save">${editing ? "Enregistrer" : "Ajouter"} <span class="btn-shine"></span></button>
      </div>
    </form>`);

  document.getElementById("mnt-save").addEventListener("click", async () => {
    const body = {
      vehicle_id: Number(document.getElementById("m-veh").value),
      type: document.getElementById("m-type").value,
      date: document.getElementById("m-date").value,
      cout: Number(document.getElementById("m-cout").value) || 0,
      garage: document.getElementById("m-garage").value,
      notes: document.getElementById("m-notes").value,
    };
    try {
      if (editing) await api(`/api/maintenance/${m.id}`, "PUT", body);
      else await api("/api/maintenance", "POST", body);
      closeModal();
      toast("Intervention enregistrée.", "success");
      navigate("maintenance");
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

/* ==========================================================================
   VUE : VIDANGES
   ========================================================================== */
async function viewVidanges(root) {
  const [res, fRes] = await Promise.all([Promise.all([api("/api/vidanges"), api("/api/vehicles")]), api("/api/vidanges/stats").catch(() => null)]);
  const items = res[0].vidanges || [];
  const vehicles = res[1].vehicles || [];
  const isAdmin = (state.user || {}).role === "admin";
  const stats = fRes || {};
  let totalCost = 0;
  items.forEach((v) => (totalCost += Number(v.cout) || 0));
  const due = (stats.forecast || []).filter((f) => f.due);

  const toolbar = h("div", { class: "toolbar" }, [
    h("div", { class: "panel-sub", style: "margin:0", text: `${items.length} vidange(s) · coût total ${fmtMoney(totalCost)}` }),
    h("div", { class: "spacer" }),
    h("button", { class: "btn btn-ghost btn-sm", onclick: () => vidangesPdf(), html: svg("file") + " Rapport PDF" }),
    h("button", { class: "btn btn-primary btn-sm", onclick: () => vidangeModal(null, vehicles), html: svg("plus") + " Vidange <span class='btn-shine'></span>" }),
  ]);

  const warn = due.length ? h("div", { class: "panel glass", style: "margin:0 0 16px;border-color:rgba(245,158,11,0.3)" }, [
    h("div", { class: "panel-title", html: "⛽ Vidanges à prévoir (" + due.length + ")" }),
    h("div", { class: "v-list" }, due.map((f) => h("div", { class: "v-mini" }, [
      h("div", { class: "avatar", text: (f.immatriculation || "V")[0] }),
      h("div", { class: "v-mini-body" }, [
        h("strong", { text: `${f.marque} ${f.modele} · ${f.immatriculation}` }),
        h("small", { text: `prochaine vidange à ${fmtKm(f.km_due)} km` + (f.km_left <= 0 ? " · dépassée" : f.days_since != null && f.days_since > 365 ? " · >1 an" : "") }),
      ]),
      h("span", { class: "badge " + (f.km_left <= 0 ? "badge-danger" : "badge-maintenance"), text: f.km_left <= 0 ? "En retard" : fmtKm(f.km_left) + " restant" }),
    ]))),
  ]) : null;

  const card = h("div", { class: "table-card glass reveal reveal-1" }, [h("div", { class: "table-scroll" }, [h("table", { class: "data" })] )]);
  const tbl = card.querySelector("table");
  tbl.appendChild(h("thead", null, [h("tr", null, [
    h("th", { text: "Date" }), h("th", { text: "Véhicule" }), h("th", { text: "Km compteur" }),
    h("th", { text: "Intervalle" }), h("th", { text: "Prochaine" }), h("th", { text: "Restant" }),
    h("th", { text: "Huile" }), h("th", { text: "Filtres" }), h("th", { text: "Liquides" }),
    h("th", { text: "Coût" }), h("th", { text: "", style: "text-align:right" }),
  ])]));

  root.innerHTML = "";
  root.append(toolbar);
  if (warn) root.append(warn);
  root.append(card);

  if (!items.length) {
    tbl.appendChild(emptyRow(11, "🛢️", "Aucune vidange enregistrée."));
    return;
  }
  const vehKm = {};
  vehicles.forEach((x) => (vehKm[x.id] = Number(x.kilometrage) || 0));
  const tbody = h("tbody", null, []);
  items.forEach((v) => {
    const vname = v.immatriculation ? `${v.marque} ${v.modele} · ${v.immatriculation}` : "—";
    const kmLeft = (Number(v.prochaine_km) || 0) - (vehKm[v.vehicle_id] || 0);
    const fil = [];
    if (v.filtre_huile || v.filtre) fil.push(h("span", { class: "badge badge-info", text: "Huile" }));
    if (v.filtre_gasoil) fil.push(h("span", { class: "badge badge-warn", text: "Gasoil" }));
    const liq = [];
    if (v.liquide_refroidissement) liq.push(h("span", { class: "badge badge-maintenance", text: "Refroid." }));
    if (v.liquide_laveglace) liq.push(h("span", { class: "badge badge-maintenance", text: "Lave-glace" }));
    tbody.appendChild(h("tr", null, [
      h("td", { class: "td-dim", text: fmtDate(v.date) }),
      h("td", { class: "td-strong", text: vname }),
      h("td", { class: "td-mono", text: fmtKm(v.km) }),
      h("td", { class: "td-mono", text: Number(v.km_interval) ? fmtKm(v.km_interval) : "—" }),
      h("td", { class: "td-mono", text: Number(v.prochaine_km) ? fmtKm(v.prochaine_km) : "—" }),
      h("td", null, [Number(v.prochaine_km) ? h("span", { class: "badge " + (kmLeft <= 0 ? "badge-danger" : kmLeft <= 500 ? "badge-warn" : "badge-info"), text: kmLeft <= 0 ? "dépassée" : fmtKm(kmLeft) + " restant" }) : h("span", { class: "td-dim", text: "—" })]),
      h("td", null, [h("span", { class: "badge badge-info", text: v.huile || "—" })]),
h("td", null, fil.length ? fil : [h("span", { class: "td-dim", text: "—" })]),
      h("td", null, liq.length ? liq : [h("span", { class: "td-dim", text: "—" })]),
      h("td", { class: "td-mono", text: fmtMoney(v.cout) }),
      h("td", null, [h("div", { class: "row-actions" }, [
        h("button", { class: "mini-btn", title: "Modifier", onclick: () => vidangeModal(v, vehicles), html: svg("pencil") }),
        isAdmin ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer la vidange", "Supprimer cette vidange ?", () => delVidange(v)), html: svg("trash") }) : null,
      ])]),
    ]));
  });
  tbl.appendChild(tbody);
}

async function delVidange(v) {
  try {
    await api(`/api/vidanges/${v.id}`, "DELETE");
    toast("Vidange supprimée.", "success");
    navigate("vidanges");
  } catch (err) {
    toast(err.message, "error");
  }
}

function vidangeModal(v, vehicles) {
  const editing = !!v;
  const val = (f, dft) => v ? esc(v[f] || dft) : dft;
  const chk = (f, legacy) => v && ((v[f]) || (legacy && v[legacy])) ? "checked" : "";
  openModal(`
    <div class="modal-head"><h4>${editing ? "Modifier la vidange" : "Nouvelle vidange"}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="vidange">
      <div class="form-grid">
        <div class="field full"><label>Véhicule *</label>
          <select class="select" id="vg-veh" style="width:100%">
            ${vehicles.map((x) => `<option value="${x.id}" ${v && v.vehicle_id === x.id ? "selected" : ""}>${esc(x.marque)} ${esc(x.modele)} · ${esc(x.immatriculation)}</option>`).join("")}
          </select></div>
        <div class="field"><label>Date</label>
          <div class="input-wrap"><input id="vg-date" type="date" value="${val("date", new Date().toISOString().slice(0, 10))}" /></div></div>
        <div class="field"><label>Kilométrage à la vidange (compteur)</label>
          <div class="input-wrap"><input id="vg-km" type="number" min="0" value="${val("km", "")}" placeholder="Ex. 58400" /></div></div>
        <div class="field"><label>Km de la vidange (intervalle)</label>
          <div class="input-wrap"><input id="vg-km-interval" type="number" min="0" step="500" value="${val("km_interval", "")}" placeholder="Ex. 10000" /></div></div>
        <div class="field"><label>Prochaine vidange (km)</label>
          <div class="input-wrap"><input id="vg-prochaine" type="number" min="0" value="${val("prochaine_km", "")}" placeholder="auto : compteur + intervalle" /></div></div>
        <div class="field"><label>Huile utilisée</label>
          <div class="input-wrap"><input id="vg-huile" type="text" value="${val("huile")}" placeholder="Ex. 10W-40" /></div></div>
        <div class="field"><label>Quantité (L)</label>
          <div class="input-wrap"><input id="vg-quantite" type="number" min="0" step="0.1" value="${val("quantite", "")}" /></div></div>
        <div class="field"><label>Coût (FCFA)</label>
          <div class="input-wrap"><input id="vg-cout" type="number" min="0" step="0.01" value="${val("cout", 0)}" /></div></div>
        <div class="field"><label>Garage</label>
          <div class="input-wrap"><input id="vg-garage" type="text" value="${val("garage")}" placeholder="Garage NexAUTO" /></div></div>
        <div class="field full"><label>Remplacements effectués</label>
          <div class="check-grid">
            <label class="field-check"><input id="vg-filtre-huile" type="checkbox" ${chk("filtre_huile", "filtre")}> Filtre à huile</label>
            <label class="field-check"><input id="vg-filtre-gasoil" type="checkbox" ${chk("filtre_gasoil")}> Filtre à gazoil</label>
            <label class="field-check"><input id="vg-huile-transm" type="checkbox" ${chk("huile_transmission")}> Huile de transmission</label>
            <label class="field-check"><input id="vg-liq-refroid" type="checkbox" ${chk("liquide_refroidissement")}> Liquide de refroidissement</label>
            <label class="field-check"><input id="vg-liq-lave" type="checkbox" ${chk("liquide_laveglace")}> Liquide lave-glace</label>
          </div></div>
        <div class="field full"><label>Notes</label>
          <div class="input-wrap"><textarea id="vg-notes" rows="2" style="width:100%;resize:vertical;background:rgba(255,255,255,0.04);border:1px solid var(--border-strong);border-radius:12px;padding:12px;color:var(--text);font-family:var(--font);outline:none">${val("notes", "")}</textarea></div></div>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button type="button" class="btn btn-ghost" data-close>Annuler</button>
        <button type="button" class="btn btn-primary" id="vg-save">${editing ? "Enregistrer" : "Ajouter"} <span class="btn-shine"></span></button>
      </div>
    </form>`);

  const kmEl = document.getElementById("vg-km");
  const intEl = document.getElementById("vg-km-interval");
  const progEl = document.getElementById("vg-prochaine");
  let progTouched = false;
  progEl.addEventListener("input", () => { progTouched = true; });
  const autoProg = () => {
    const k = Number(kmEl.value) || 0, i = Number(intEl.value) || 0;
    if (!progTouched && (k || i)) progEl.value = k + i || "";
  };
  kmEl.addEventListener("input", autoProg);
  intEl.addEventListener("input", autoProg);

  document.getElementById("vg-save").addEventListener("click", async () => {
    const body = {
      vehicle_id: Number(document.getElementById("vg-veh").value),
      date: document.getElementById("vg-date").value,
      km: Number(document.getElementById("vg-km").value) || 0,
      km_interval: Number(document.getElementById("vg-km-interval").value) || 0,
      huile: document.getElementById("vg-huile").value,
      quantite: Number(document.getElementById("vg-quantite").value) || 0,
      filtre: document.getElementById("vg-filtre-huile").checked,
      filtre_huile: document.getElementById("vg-filtre-huile").checked,
      filtre_gasoil: document.getElementById("vg-filtre-gasoil").checked,
      huile_transmission: document.getElementById("vg-huile-transm").checked,
      liquide_refroidissement: document.getElementById("vg-liq-refroid").checked,
      liquide_laveglace: document.getElementById("vg-liq-lave").checked,
      cout: Number(document.getElementById("vg-cout").value) || 0,
      garage: document.getElementById("vg-garage").value,
      prochaine_km: Number(document.getElementById("vg-prochaine").value) || 0,
      notes: document.getElementById("vg-notes").value,
    };
    try {
      if (editing) await api(`/api/vidanges/${v.id}`, "PUT", body);
      else await api("/api/vidanges", "POST", body);
      closeModal();
      toast("Vidange enregistrée.", "success");
      navigate("vidanges");
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

async function vidangesPdf() {
  toast("Génération du rapport vidanges…", "info");
  try {
    await downloadPdf("/api/vidanges/pdf", `Rapport_vidanges_${new Date().toISOString().slice(0, 10)}.pdf`);
    toast("Rapport vidanges téléchargé.", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

/* ==========================================================================
   VUE : BUDGET & PLAN DE MAINTENANCE PRÉVENTIVE
   ========================================================================== */
let budgetState = { annee: new Date().getFullYear() };

function budgetLevelClass(level) {
  return level === "danger" ? "danger" : level === "warning" ? "warning" : "";
}

async function viewBudget(root) {
  const isAdmin = (state.user || {}).role === "admin";
  const years = await api("/api/budget/years").catch(() => ({ years: [] }));
  const yearList = years.years && years.years.length ? years.years : [budgetState.annee];
  if (!yearList.includes(budgetState.annee)) budgetState.annee = yearList[0];

  const [summary, forecastBudget] = await Promise.all([
    api(`/api/budget/summary?annee=${budgetState.annee}`),
    api("/api/maintenance/forecast/budget").catch(() => null),
  ]);

  root.innerHTML = "";

  const toolbar = h("div", { class: "toolbar" }, [
    h("select", {
      class: "select budget-year-select",
      onchange: (e) => { budgetState.annee = Number(e.target.value); navigate("budget"); },
    }, [...new Set([...yearList, new Date().getFullYear()])].sort((a, b) => b - a)
      .map((y) => h("option", { value: y, selected: y === budgetState.annee ? "selected" : null, text: String(y) }))),
    h("div", { class: "spacer" }),
    h("button", { class: "btn btn-ghost btn-sm", onclick: () => downloadApi(`/api/budget/export?annee=${budgetState.annee}`, `nexfleet_budget_${budgetState.annee}.xlsx`).then(() => toast("Export Excel téléchargé.", "success")).catch((e) => toast(e.message, "error")), html: svg("download") + " Excel" }),
    h("button", { class: "btn btn-ghost btn-sm", onclick: () => downloadPdf(`/api/budget/pdf?annee=${budgetState.annee}`, `nexfleet_budget_${budgetState.annee}.pdf`).then(() => toast("Rapport PDF téléchargé.", "success")).catch((e) => toast(e.message, "error")), html: svg("file") + " Rapport PDF" }),
    isAdmin ? h("button", { class: "btn btn-primary btn-sm", onclick: () => budgetImportModal(), html: svg("upload") + " Importer le plan <span class='btn-shine'></span>" }) : null,
  ]);
  root.appendChild(toolbar);

  if (!summary.has_plan) {
    root.appendChild(h("div", { class: "panel glass reveal reveal-1" }, [
      h("div", { class: "empty" }, [
        h("div", { class: "empty-ico", text: "📊" }),
        h("p", { text: `Aucun plan budgétaire importé pour ${budgetState.annee}.` }),
        isAdmin ? h("button", { class: "btn btn-primary btn-sm", style: "margin-top:14px", onclick: () => budgetImportModal(), html: svg("upload") + " Importer le plan d'achat annuel" }) : null,
      ]),
    ]));
    return;
  }

  const kpis = [
    { label: "Budget prévu", value: fmtMoney(summary.total_prevu), tint: "rgba(99,102,241,0.18)" },
    { label: "Réalisé à ce jour", value: fmtMoney(summary.total_realise), tint: "rgba(34,211,238,0.18)" },
    { label: "Écart", value: fmtMoney(summary.total_ecart), tint: summary.total_ecart < 0 ? "rgba(248,113,113,0.18)" : "rgba(52,211,153,0.18)" },
    { label: "Taux de consommation", value: summary.taux_global + " %", tint: "rgba(251,191,36,0.18)" },
  ];
  const statsGrid = h("div", { class: "stats-grid" });
  kpis.forEach((k, i) => {
    statsGrid.appendChild(h("div", { class: "stat-card glass reveal reveal-" + (i % 5 + 1), style: `--tint:${k.tint};--glow:${k.tint}` }, [
      h("div", { class: "stat-value", text: k.value }),
      h("div", { class: "stat-label", text: k.label }),
    ]));
  });
  root.appendChild(statsGrid);

  if (forecastBudget) {
    root.appendChild(h("div", { class: "budget-forecast-row" }, [
      h("div", { class: "budget-forecast-chip" }, [h("small", { text: "Prévu sous 30 jours" }), h("strong", { text: fmtMoney(forecastBudget.horizon_30j) }), h("small", { text: `${forecastBudget.count_30j} intervention(s) prédite(s)` })]),
      h("div", { class: "budget-forecast-chip" }, [h("small", { text: "Prévu sous 60 jours" }), h("strong", { text: fmtMoney(forecastBudget.horizon_60j) }), h("small", { text: `${forecastBudget.count_60j} intervention(s) prédite(s)` })]),
      h("div", { class: "budget-forecast-chip" }, [h("small", { text: "Prévu sous 90 jours" }), h("strong", { text: fmtMoney(forecastBudget.horizon_90j) }), h("small", { text: `${forecastBudget.count_90j} intervention(s) prédite(s)` })]),
    ]));
  }

  if (summary.alerts && summary.alerts.length) {
    root.appendChild(h("div", { class: "panel glass reveal reveal-2", style: "margin-bottom:16px;border-color:rgba(245,158,11,0.3)" }, [
      h("div", { class: "panel-title", html: "⚠️ Catégories à surveiller (" + summary.alerts.length + ")" }),
      h("div", { class: "v-list" }, summary.alerts.map((a) => h("div", { class: "v-mini" }, [
        h("div", { class: "avatar", text: a.categorie[0] }),
        h("div", { class: "v-mini-body" }, [
          h("strong", { text: a.categorie }),
          h("small", { text: `${fmtMoney(a.realise)} réalisés sur ${fmtMoney(a.prevu)} prévus` }),
        ]),
        h("span", { class: "badge " + (a.level === "danger" ? "badge-danger" : "badge-warn"), text: a.taux + " %" }),
      ]))),
    ]));
  }

  const panel = h("div", { class: "panel glass table-card reveal reveal-3" }, [
    h("div", { class: "panel-title", text: "Prévu vs réalisé par catégorie" }),
    h("div", { class: "panel-sub", text: `Exercice ${budgetState.annee} — comparé aux interventions enregistrées dans Maintenance et Vidanges` }),
  ]);
  const list = h("div", null, []);
  summary.categories
    .filter((c) => c.prevu > 0 || c.realise > 0)
    .sort((a, b) => b.prevu - a.prevu)
    .forEach((c) => {
      const pct = Math.min(100, c.taux);
      list.appendChild(h("div", { class: "budget-cat-row" }, [
        h("div", null, [
          h("div", { class: "budget-cat-name", text: c.categorie },),
          h("div", { class: "budget-cat-figures", text: `${fmtMoney(c.realise)} / ${fmtMoney(c.prevu)}` }),
        ]),
        h("div", { class: "budget-progress" }, [
          h("div", { class: "budget-progress-fill " + budgetLevelClass(c.level), style: `width:${pct}%` }),
        ]),
        h("div", { class: "budget-cat-taux", text: c.taux + " %" }),
        h("span", { class: "badge " + (c.level === "danger" ? "badge-danger" : c.level === "warning" ? "badge-warn" : "badge-ok"), text: c.level === "danger" ? "Dépassé" : c.level === "warning" ? "À surveiller" : "OK" }),
      ]));
    });
  panel.appendChild(list);
  root.appendChild(panel);
}

function budgetImportModal() {
  const box = openModal(`
    <div class="modal-head"><h4>Importer le plan de maintenance</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="budget-import">
      <p style="color:var(--text-dim);font-size:13px;line-height:1.6;margin:0 0 14px">
        Importez le fichier <b>.xlsx</b> « Plan d'achat annuel » du parc automobile
        (feuille avec trimestres, quantités et montants en FCFA). L'année et les catégories
        sont détectées automatiquement ; un import remplace le plan existant pour la même année.
      </p>
      <div id="bud-drop" class="dropzone">
        <span class="dz-ico">📊</span>
        <p><b>Glissez votre fichier ici</b><br/><small>ou cliquez pour parcourir — .xlsx uniquement</small></p>
        <input id="bud-file" type="file" accept=".xlsx" style="display:none" />
      </div>
      <div id="bud-result" class="import-result" hidden></div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button type="button" class="btn btn-ghost" data-close>Fermer</button>
        <button type="button" class="btn btn-primary" id="bud-submit" disabled>Importer <span class="btn-shine"></span></button>
      </div>
    </form>`, false);

  const input = box.querySelector("#bud-file");
  const drop = box.querySelector("#bud-drop");
  const submit = box.querySelector("#bud-submit");

  drop.addEventListener("click", () => input.click());
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  const pick = (file) => {
    if (!file.name.toLowerCase().endsWith(".xlsx")) { toast("Utilisez un fichier .xlsx.", "error"); return; }
    const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files;
    drop.querySelector("p").innerHTML = `<b>${esc(file.name)}</b><br/><small>${(file.size / 1024).toFixed(1)} Ko — prêt à importer</small>`;
    submit.disabled = false;
  };
  drop.addEventListener("drop", (e) => { if (e.dataTransfer.files.length) pick(e.dataTransfer.files[0]); });
  input.addEventListener("change", () => { if (input.files.length) pick(input.files[0]); });

  submit.addEventListener("click", async () => {
    const file = input.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    submit.disabled = true; submit.textContent = "Import en cours…";
    try {
      const res = await fetch("/api/budget/import", {
        method: "POST", headers: { Authorization: "Bearer " + state.token }, body: fd,
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error((data && data.error) || "Import échoué.");
      const result = box.querySelector("#bud-result");
      result.hidden = false;
      result.innerHTML = "";
      result.appendChild(h("div", { class: "import-summary" }, [
        importKind("Lignes importées", data.rows_imported, "success"),
        importKind("Année détectée", data.annee, "info"),
        importKind("Lignes ignorées", data.rows_skipped, "danger"),
      ]));
      toast(`Plan ${data.annee} importé : ${data.rows_imported} ligne(s).`, "success");
      budgetState.annee = data.annee;
      setTimeout(() => { closeModal(); navigate("budget"); }, 900);
    } catch (err) {
      toast(err.message, "error");
      submit.disabled = false; submit.textContent = "Importer";
    }
  });
  return box;
}

/* ==========================================================================
   VUE : ANALYTIQUE — COÛT TOTAL DE POSSESSION (TCO)
   ========================================================================== */
async function viewAnalytics(root) {
  const data = await api("/api/tco");
  root.innerHTML = "";

  const kpis = [
    { label: "Coût total du parc", value: fmtMoney(data.fleet_total_cost), tint: "rgba(99,102,241,0.18)" },
    { label: "Coût moyen / véhicule", value: fmtMoney(data.fleet_avg_cost), tint: "rgba(34,211,238,0.18)" },
    { label: "Véhicules suivis", value: data.vehicles.length, tint: "rgba(167,139,250,0.18)" },
  ];
  const statsGrid = h("div", { class: "stats-grid" });
  kpis.forEach((k, i) => {
    statsGrid.appendChild(h("div", { class: "stat-card glass reveal reveal-" + (i % 5 + 1), style: `--tint:${k.tint};--glow:${k.tint}` }, [
      h("div", { class: "stat-value", text: k.value }), h("div", { class: "stat-label", text: k.label }),
    ]));
  });
  root.appendChild(statsGrid);

  const palette = ["#6366f1", "#22d3ee", "#a78bfa", "#f472b6", "#34d399", "#fbbf24", "#f87171", "#38bdf8", "#fb923c", "#10b981", "#eab308", "#94a3b8"];
  const catEntries = Object.entries(data.category_totals || {}).sort((a, b) => b[1] - a[1]);

  const chartsGrid = h("div", { class: "dash-grid" }, [
    h("div", { class: "panel glass reveal reveal-1" }, [
      h("div", { class: "panel-title", text: "Répartition des coûts par catégorie" }),
      catEntries.length
        ? h("div", null, [
            h("div", { class: "chart-wrap", style: "height:220px" }, [h("canvas", { id: "tco-donut" })]),
            h("div", { class: "legend" }, catEntries.map(([k, v], i) => h("span", { class: "legend-item" }, [
              h("span", { class: "legend-dot", style: `background:${palette[i % palette.length]}` }),
              h("span", { text: `${k} · ${fmtMoney(v)}` }),
            ]))),
          ])
        : h("div", { class: "empty" }, [h("p", { text: "Aucune dépense enregistrée pour l'instant." })]),
    ]),
    h("div", { class: "panel glass reveal reveal-2" }, [
      h("div", { class: "panel-title", text: "Tendance mensuelle (12 derniers mois)" }),
      h("div", { class: "chart-wrap", style: "height:220px" }, [h("canvas", { id: "tco-bars" })]),
    ]),
  ]);
  root.appendChild(chartsGrid);

  if (catEntries.length) {
    requestAnimationFrame(() => drawDonut(document.getElementById("tco-donut"), catEntries.map((e) => e[1]), palette));
  }
  const months = (data.monthly_trend || []).map((m) => m.month);
  const costs = (data.monthly_trend || []).map((m) => m.cost);
  requestAnimationFrame(() => drawBars(document.getElementById("tco-bars"), months, costs, (v) => fmtFcfaShort(v)));

  const card = h("div", { class: "table-card glass reveal reveal-3" }, [h("div", { class: "table-scroll" }, [h("table", { class: "data" })])]);
  const tbl = card.querySelector("table");
  tbl.appendChild(h("thead", null, [h("tr", null, [
    h("th", { text: "#" }), h("th", { text: "Véhicule" }), h("th", { text: "Coût total" }),
    h("th", { text: "Coût / km" }), h("th", { text: "Coût / mois" }), h("th", { text: "Interventions" }),
  ])]));
  root.appendChild(h("div", { class: "panel-title", text: "Classement par coût cumulé", style: "margin:22px 0 10px" }));
  root.appendChild(card);

  if (!data.vehicles.length) {
    tbl.appendChild(emptyRow(6, "🚗", "Aucune donnée de coût pour l'instant."));
    return;
  }
  const tbody = h("tbody", null, []);
  data.vehicles.forEach((v, i) => {
    const rankCls = i === 0 ? "top1" : i === 1 ? "top2" : i === 2 ? "top3" : "";
    tbody.appendChild(h("tr", null, [
      h("td", null, [h("span", { class: "tco-rank " + rankCls, text: String(i + 1) })]),
      h("td", { class: "td-strong", text: `${v.marque} ${v.modele} · ${v.immatriculation}` }),
      h("td", { class: "td-mono", text: fmtMoney(v.total_cost) }),
      h("td", { class: "td-dim", text: fmtMoney(v.cost_per_km) }),
      h("td", { class: "td-dim", text: fmtMoney(v.cost_per_month) }),
      h("td", { text: v.interventions }),
    ]));
  });
  tbl.appendChild(tbody);
}

/* ==========================================================================
   VUE : CALENDRIER
   ========================================================================== */
const CAL_EVENT_META = {
  assurance_exp: { label: "Assurance", color: "#f87171" },
  vignette_exp: { label: "Vignette", color: "#fbbf24" },
  ctrl_tech_exp: { label: "Contrôle technique", color: "#34d399" },
  carte_grise_exp: { label: "Carte grise", color: "#e879f9" },
  permis: { label: "Permis", color: "#a78bfa" },
  cni: { label: "Carte identité", color: "#fb923c" },
  vidange: { label: "Vidange", color: "#38bdf8" },
};

async function viewCalendar(root) {
  const res = await api("/api/calendar/events");
  const events = res.events || [];
  const cursor = new Date();
  cursor.setDate(1);

  const grid = h("div", { class: "calendar-wrap" });
  const legend = h("div", { class: "calendar-legend" }, Object.entries(CAL_EVENT_META).map(([k, m]) =>
    h("span", { class: "cal-legend-item" }, [h("span", { class: "cal-legend-dot", style: `background:${m.color}` }), h("small", { text: m.label })])));

  const render = () => {
    grid.innerHTML = "";
    const y = cursor.getFullYear(), m = cursor.getMonth();
    const firstDow = new Date(y, m, 1).getDay();
    const daysInMonth = new Date(y, m + 1, 0).getDate();
    const todayStr = new Date().toISOString().slice(0, 10);
    const curMonth = `${y}-${String(m + 1).padStart(2, "0")}`;
    const byDay = {};
    events.forEach((e) => { if ((e.date || "").startsWith(curMonth)) (byDay[e.date] = byDay[e.date] || []).push(e); });

    grid.appendChild(h("div", { class: "calendar-head" }, [
      h("button", { class: "mini-btn", text: "◀", title: "Mois précédent", onclick: () => { cursor.setMonth(m - 1); render(); } }),
      h("strong", { text: cursor.toLocaleDateString("fr-FR", { month: "long", year: "numeric" }) }),
      h("div", { class: "cal-head-actions" }, [
        h("button", { class: "mini-btn", text: "Aujourd'hui", onclick: () => { cursor.setDate(1); render(); } }),
        h("button", { class: "mini-btn", text: "▶", title: "Mois suivant", onclick: () => { cursor.setMonth(m + 1); render(); } }),
      ]),
    ]));

    grid.appendChild(h("div", { class: "calendar-days" },
      ["Lu", "Ma", "Me", "Je", "Ve", "Sa", "Di"].map((d) => h("div", { class: "cal-dow", text: d }))));

    const cells = h("div", { class: "calendar-cells" });
    const offset = (firstDow + 6) % 7;
    for (let i = 0; i < offset; i++) cells.appendChild(h("div", { class: "cal-cell empty" }));
    for (let d = 1; d <= daysInMonth; d++) {
      const iso = `${curMonth}-${String(d).padStart(2, "0")}`;
      const dayEvents = byDay[iso] || [];
      cells.appendChild(h("div", { class: "cal-cell" + (iso === todayStr ? " today" : "") }, [
        h("span", { class: "cal-num", text: d }),
        ...dayEvents.map((e) => h("button", {
          class: "cal-event " + e.type,
          style: `--evcolor:${CAL_EVENT_META[e.type] ? CAL_EVENT_META[e.type].color : "#94a3b8"}`,
          title: `${e.label} — ${e.vehicle} ${e.immatriculation}`,
          onclick: () => showCalEvent(e),
          text: e.label,
        })),
      ]));
    }
    grid.appendChild(cells);
  };
  render();

  const evBadge = document.getElementById("badge-events");
  if (evBadge) {
    const curMonth = new Date().toISOString().slice(0, 7);
    const n = events.filter((e) => (e.date || "").startsWith(curMonth)).length;
    evBadge.hidden = n === 0;
    evBadge.textContent = n;
  }

  root.innerHTML = "";
  root.append(
    h("div", { class: "toolbar" }, [
      h("div", { class: "panel-sub", style: "margin:0", text: `${events.length} échéance(s) enregistrée(s)` }),
      h("div", { class: "spacer" }),
      h("button", { class: "btn btn-ghost btn-sm", onclick: () => navigate("vehicles"), html: svg("car") + " Gérer les échéances" }),
    ]),
    legend,
    h("div", { class: "table-card glass reveal reveal-1" }, [grid]),
  );
}

function showCalEvent(e) {
  const meta = CAL_EVENT_META[e.type] || { label: e.label || "Échéance" };
  openModal(`
    <div class="modal-head"><h4>${esc(meta.label)}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <div class="cal-event-modal">
      <div class="drawer-kv"><small>Date</small><strong>${esc(fmtDate(e.date))}</strong></div>
      <div class="drawer-kv"><small>${e.kind === "driver" ? "Conducteur" : "Véhicule"}</small><strong>${esc(e.vehicle)}</strong></div>
      <div class="drawer-kv"><small>Référence</small><strong>${esc(e.immatriculation || "—")}</strong></div>
      ${e.km ? `<div class="drawer-kv"><small>Kilométrage</small><strong>${fmtKm(e.km)}</strong></div>` : ""}
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
      <button class="btn btn-ghost" data-close>Fermer</button>
    </div>`);
}

/* ==========================================================================
   VUE : CARTES — Leaflet / OpenStreetMap (gratuit, sans clé API)
   ========================================================================== */
async function viewMaps(root) {
  root.innerHTML = "";
  const wrap = h("div", { class: "maps-wrap" });
  const toolbar = h("div", { class: "toolbar" }, [
    h("div", { class: "spacer" }),
    h("button", { class: "btn btn-ghost btn-sm", id: "maps-refresh", html: svg("refresh") + " Rafraîchir" }),
    h("button", { class: "btn btn-ghost btn-sm", id: "maps-center", html: svg("target") + " Centrer sur tous" }),
  ]);
  const mapEl = h("div", { id: "leaflet-map", class: "gmap-container" });
  const infoPanel = h("div", { id: "maps-info", class: "maps-info-panel glass" });
  wrap.appendChild(toolbar);
  wrap.appendChild(h("div", { class: "maps-layout" }, [mapEl, infoPanel]));
  root.appendChild(wrap);

  let res;
  try {
    res = await api("/api/vehicles/locations");
  } catch (e) {
    infoPanel.innerHTML = `<p style="padding:20px;color:var(--text-dim)">Erreur chargement localisations.</p>`;
    return;
  }
  const allVehicles = res.vehicles || [];
  const vehicles = allVehicles.filter((v) => v.lat && v.lng);
  const withoutGps = allVehicles.filter((v) => !v.lat || !v.lng);

  if (typeof L === "undefined") {
    infoPanel.innerHTML = `<p style="padding:20px;color:var(--text-dim)">Leaflet non chargé. Vérifiez votre connexion Internet.</p>`;
    return;
  }

  const defaultCenter = vehicles.length
    ? [vehicles.reduce((s, v) => s + v.lat, 0) / vehicles.length, vehicles.reduce((s, v) => s + v.lng, 0) / vehicles.length]
    : [3.848, 11.502];

  const map = L.map("leaflet-map").setView(defaultCenter, vehicles.length > 1 ? 6 : 12);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map);

  const statutColors = { "En service": "#34d399", "En maintenance": "#fbbf24", "En panne": "#f87171", "Hors service": "#94a3b8" };
  const markers = [];

  vehicles.forEach((v) => {
    const color = statutColors[v.statut] || "#6366f1";
    const icon = L.divIcon({
      className: "leaflet-marker-custom",
      html: `<div style="width:28px;height:28px;border-radius:50% 50% 50% 0;background:${color};transform:rotate(-45deg);border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.35)"></div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 28],
      popupAnchor: [0, -30],
    });

    const marker = L.marker([v.lat, v.lng], { icon }).addTo(map);

    const popupHtml = `<div style="font-family:Inter,sans-serif;min-width:160px;padding:4px">
      <strong style="font-size:14px">${esc(v.marque)} ${esc(v.modele)}</strong><br/>
      <span style="color:#666;font-size:12px">${esc(v.immatriculation)}</span><br/>
      <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:4px"></span>
      <span style="font-size:12px">${esc(v.statut || "—")}</span><br/>
      ${v.affectation ? `<span style="font-size:11px;color:#888">${esc(v.affectation)}</span>` : ""}
      ${v.direction ? `<span style="font-size:11px;color:#888">${esc(v.direction)}</span>` : ""}
    </div>`;
    marker.bindPopup(popupHtml);
    markers.push({ marker, vehicle: v });
  });

  window._fleetCenterMap = (lat, lng) => map.setView([lat, lng], 15);

  renderMapsInfo(infoPanel, markers, withoutGps);

  document.getElementById("maps-refresh")?.addEventListener("click", () => viewMaps(root));
  document.getElementById("maps-center")?.addEventListener("click", () => {
    if (markers.length) {
      const group = L.featureGroup(markers.map((m) => m.marker));
      map.fitBounds(group.getBounds().pad(0.15));
    }
  });

  setTimeout(() => map.invalidateSize(), 100);
}

function renderMapsInfo(panel, markers, withoutGps) {
  panel.innerHTML = "";
  const title = h("h4", { text: `Véhicules localisés (${markers.length})`, style: "margin:0 0 12px;font-size:15px" });
  panel.appendChild(title);

  const statutColors = { "En service": "#34d399", "En maintenance": "#fbbf24", "En panne": "#f87171", "Hors service": "#94a3b8" };
  markers.forEach(({ vehicle: v, marker }) => {
    const dot = statutColors[v.statut] || "#6366f1";
    const card = h("div", { class: "maps-vehicle-card", onclick: () => {
      marker._map.setView(marker.getLatLng(), 15);
      marker.openPopup();
    }}, [
      h("div", { class: "maps-vehicle-dot", style: `background:${dot}` }),
      h("div", { class: "maps-vehicle-info" }, [
        h("strong", { text: `${v.marque} ${v.modele}` }),
        h("small", { text: `${v.immatriculation} · ${v.statut || "—"}` }),
        v.affectation ? h("small", { text: v.affectation, style: "color:var(--text-dim)" }) : null,
      ]),
    ]);
    panel.appendChild(card);
  });

  const noGps = withoutGps || [];
  if (noGps.length) {
    const sec = h("div", { style: "margin-top:16px" });
    sec.appendChild(h("h5", { text: `Sans position GPS (${noGps.length})`, style: "font-size:13px;color:var(--text-dim);margin-bottom:8px" }));
    noGps.forEach((v) => {
      const card = h("div", { class: "maps-vehicle-card", style: "opacity:0.6" }, [
        h("div", { class: "maps-vehicle-dot", style: "background:#94a3b8" }),
        h("div", { class: "maps-vehicle-info" }, [
          h("strong", { text: `${v.marque} ${v.modele}` }),
          h("small", { text: v.immatriculation }),
        ]),
      ]);
      sec.appendChild(card);
    });
    panel.appendChild(sec);
  }

  if (!markers.length && !noGps.length) {
    panel.appendChild(h("p", { text: "Aucun véhicule trouvé.", style: "color:var(--text-dim);font-size:13px;padding:10px 0" }));
  }
}

/* ==========================================================================
   VUE : RAPPORTS & PDF
   ========================================================================== */
async function viewReports(root) {
  const res = await Promise.all([api("/api/stats"), api("/api/vehicles")]);
  const stats = res[0];
  const vehicles = res[1].vehicles || [];

  const sections = h("div", null, [
    h("div", { class: "page-head" }, [
      h("div", null, [h("h3", { text: "Documents exportables" }),
        h("p", { text: "Fiches de contrôle et rapport de parc générés en PDF professionnel." })]),
    ]),
    h("div", { class: "setting-card glass reveal reveal-1" }, [
      h("div", { class: "setting-ico", text: "🚛" }),
      h("div", { class: "setting-body" }, [
        h("strong", { text: "Rapport complet du parc" }),
        h("small", { text: `${vehicles.length} véhicules · synthèse, état, échéances, contrôles par mois.` }),
      ]),
      h("button", { class: "btn btn-primary btn-sm", onclick: () => parcPdf(), html: svg("file") + " Télécharger" }),
    ]),
    h("div", { class: "setting-card glass reveal reveal-2" }, [
      h("div", { class: "setting-ico", text: "📅" }),
      h("div", { class: "setting-body" }, [
        h("strong", { text: "Rapport comparatif mensuel" }),
        h("small", { text: "12 derniers mois : immatriculations, contrôles et coût de maintenance." }),
      ]),
      h("button", { class: "btn btn-primary btn-sm", onclick: () => monthlyPdf(), html: svg("file") + " Télécharger" }),
    ]),
    h("div", { class: "setting-card glass reveal reveal-3" }, [
      h("div", { class: "setting-ico", text: "🛢️" }),
      h("div", { class: "setting-body" }, [
        h("strong", { text: "Rapport des vidanges" }),
        h("small", { text: "Synthèse, coût par véhicule et détail des vidanges du parc." }),
      ]),
      h("button", { class: "btn btn-primary btn-sm", onclick: () => vidangesPdf(), html: svg("file") + " Télécharger" }),
    ]),
    h("div", { class: "setting-card glass reveal reveal-4" }, [
      h("div", { class: "setting-ico", text: "📊" }),
      h("div", { class: "setting-body" }, [
        h("strong", { text: "Rapport budget maintenance" }),
        h("small", { text: "Comparatif prévu vs réalisé par catégorie, à partir du plan importé." }),
      ]),
      h("button", { class: "btn btn-primary btn-sm", onclick: () => navigate("budget"), html: svg("file") + " Voir le budget" }),
    ]),
    h("div", { class: "panel glass reveal reveal-4" }, [
      h("div", { class: "panel-title", html: "Export des données" }),
      h("div", { class: "panel-sub", text: "Extrayez votre parc (véhicules, conducteurs, contrôles, maintenance, vidanges) au format Excel ou CSV." }),
      h("div", { class: "toolbar", style: "margin-top:14px" }, [
        h("button", { class: "btn btn-ghost btn-sm", onclick: () => exportExcel(), html: svg("download") + " Excel (.xlsx)" }),
        h("button", { class: "btn btn-ghost btn-sm", onclick: () => exportCSV(), html: svg("download") + " CSV (.csv)" }),
        h("button", { class: "btn btn-ghost btn-sm", onclick: () => downloadTemplate(), html: svg("download") + " Modèle d'import" }),
        h("button", { class: "btn btn-success btn-sm", onclick: () => importModal(), html: svg("upload") + " Importer" }),
      ]),
    ]),
    h("div", { class: "panel glass reveal reveal-5" }, [
      h("div", { class: "panel-title", html: "Fiches de contrôle individuelles" }),
      h("div", { class: "panel-sub", text: "Sélectionnez un véhicule pour générer sa dernière fiche de contrôle." }),
      h("div", { class: "toolbar", style: "margin-top:14px" }, [
        h("select", { class: "select", id: "pdf-vehicle", style: "flex:1;min-width:220px" }, [
          ...vehicles.map((v) => h("option", { value: v.id, text: `${v.marque} ${v.modele} · ${v.immatriculation}` })),
        ]),
        h("button", { class: "btn btn-success btn-sm", onclick: () => singlePdf(vehicles), html: svg("file") + " Générer la fiche" }),
      ]),
    ]),
    h("div", { class: "panel glass reveal reveal-6" }, [
      h("div", { class: "panel-title", html: "Aperçu du parc" }),
      h("div", { class: "panel-sub", text: "Indicateurs clés au moment de la génération." }),
      h("div", { class: "stats-grid", style: "margin:14px 0 0" }, [
        statMini(stats.total, "Véhicules", "🚗"),
        statMini(stats.en_service, "En service", "✅"),
        statMini(stats.en_maintenance, "Maintenance", "🔧"),
        statMini(stats.en_panne, "En panne", "⚠️"),
      ]),
    ]),
  ]);

  root.innerHTML = "";
  root.appendChild(sections);
}

function statMini(value, label, icon) {
  return h("div", { class: "stat-card glass" }, [
    h("div", { class: "stat-icon", text: icon }),
    h("div", { class: "stat-value", text: value }),
    h("div", { class: "stat-label", text: label }),
  ]);
}

async function parcPdf() {
  toast("Génération du rapport PDF…", "info");
  try {
    await downloadPdf("/api/parc/pdf", "Rapport_du_parc_automobile.pdf");
    toast("Rapport PDF téléchargé.", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function monthlyPdf() {
  toast("Génération du rapport mensuel…", "info");
  try {
    await downloadPdf("/api/reports/monthly/pdf", "Rapport_mensuel.pdf");
    toast("Rapport mensuel téléchargé.", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function singlePdf(vehicles) {
  const sel = document.getElementById("pdf-vehicle");
  const id = Number(sel.value);
  const v = vehicles.find((x) => x.id === id);
  if (!v) { toast("Véhicule introuvable.", "error"); return; }
  toast(`Génération de la fiche de ${v.immatriculation}…`, "info");
  try {
    await downloadPdf(`/api/vehicles/${id}/pdf`, `Fiche_controle_${v.immatriculation}.pdf`);
    toast("Fiche PDF téléchargée.", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

/* ==========================================================================
   VUE : PARAMÈTRES
   ========================================================================== */
async function viewSettings(root) {
  const u = state.user;
  const isAdmin = u.role === "admin";

  const usersPanel = isAdmin ? h("div", { class: "panel glass reveal reveal-5", style: "margin-top:18px" }, [
    h("div", { class: "panel-title", html: "👥 Utilisateurs" }),
    h("div", { class: "panel-sub", text: "Gérez les comptes de la plateforme : rôles, mots de passe et suppressions." }),
    h("div", { style: "margin-bottom:14px" }, [
      h("button", { class: "btn btn-primary btn-sm", onclick: () => userModal(null), html: svg("plus") + " Ajouter un utilisateur" }),
    ]),
    h("div", { class: "table-scroll" }, [h("table", { class: "data", id: "users-table" })]),
  ]) : null;

  const sections = h("div", null, [
    h("div", { class: "page-head" }, [
      h("div", null, [h("h3", { text: "Paramètres" }), h("p", { text: "Votre compte et la sécurité de la plateforme." })]),
    ]),

    h("div", { class: "setting-card glass reveal reveal-1" }, [
      h("div", { class: "setting-ico", text: "👤" }),
      h("div", { class: "setting-body" }, [
        h("strong", { text: u.username }),
        h("small", { text: `${u.email} · ${isAdmin ? "Administrateur" : "Utilisateur"}` }),
      ]),
      h("span", { class: isAdmin ? "badge badge-info" : "badge badge-muted", text: isAdmin ? "Admin" : "User" }),
    ]),

    h("div", { class: "panel glass reveal reveal-2" }, [
      h("div", { class: "panel-title", html: "🔒 Changer mon mot de passe" }),
      h("div", { class: "panel-sub", text: "Haché en PBKDF2-SHA256, jamais stocké en clair." }),
      h("form", { id: "form-pwd" }, [
        h("div", { class: "form-grid" }, [
          h("div", { class: "field" }, [h("label", { text: "Ancien mot de passe" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "p-old", type: "password", required: true }), h("button", { class: "eye", type: "button", dataset: { eye: "p-old" }, html: svg("eye") }),
          ])]),
          h("div", { class: "field" }, [h("label", { text: "Nouveau mot de passe" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "p-new", type: "password", required: true, minlength: 8 }), h("button", { class: "eye", type: "button", dataset: { eye: "p-new" }, html: svg("eye") }),
          ])]),
        ]),
        h("button", { type: "submit", class: "btn btn-primary btn-sm", html: "Mettre à jour" }),
      ]),
    ]),

    h("div", { class: "panel glass reveal reveal-3" }, [
      h("div", { class: "panel-title", html: "⚙️ Préférences du parc" }),
      h("div", { class: "panel-sub", text: isAdmin ? "Seuils d'alerte et intervalles de prévision de maintenance." : "Seuils d'alerte et prévisions actuels (modification réservée aux administrateurs)." }),
      h("form", { id: "form-prefs" }, [
        h("div", { class: "form-grid" }, [
          h("div", { class: "field" }, [h("label", { text: "Seuil d'alerte d'échéance (jours)" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "pref-alert", type: "number", min: "1", max: "365" }),
            h("span", { class: "field-unit", text: "j" }),
          ]), h("small", { class: "field-help", text: "Déclenche les alertes assurance / vignette / CT avant expiration." })]),
          h("div", { class: "field" }, [h("label", { text: "Intervalle de prévision maintenance (km)" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "pref-km", type: "number", min: "500", max: "100000" }),
            h("span", { class: "field-unit", text: "km" }),
          ]), h("small", { class: "field-help", text: "Utilisé pour estimer la prochaine révision par véhicule." })]),
          h("div", { class: "field" }, [h("label", { text: "Alerte vidange (km restants)" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "pref-vidange-km", type: "number", min: "100", max: "10000" }),
            h("span", { class: "field-unit", text: "km" }),
          ]), h("small", { class: "field-help", text: "Notifie quand la prochaine vidange est à moins de ce kilométrage." })]),
        ]),
        h("button", { type: "submit", class: "btn btn-primary btn-sm", html: "Enregistrer les préférences" }),
      ]),
    ]),

    h("div", { class: "panel glass reveal reveal-4", style: "margin-top:18px" }, [
      h("div", { class: "panel-title", html: "📧 Notifications automatiques" }),
      h("div", { class: "panel-sub", text: isAdmin ? "Digest quotidien par e-mail : échéances, budget et maintenance prédictive." : "Configuration réservée aux administrateurs." }),
      h("form", { id: "form-notify" }, [
        h("div", { class: "form-grid" }, [
          h("div", { class: "field-check full" }, [h("label", null, [
            h("input", { id: "ntf-enabled", type: "checkbox" }), h("span", { text: "Activer l'envoi automatique du digest quotidien" }),
          ])]),
          h("div", { class: "field full" }, [h("label", { text: "Destinataires" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "ntf-emails", type: "text", placeholder: "direction@entreprise.fr, flotte@entreprise.fr" }),
          ]), h("small", { class: "field-help", text: "Séparez les adresses par des virgules." })]),
          h("div", { class: "field" }, [h("label", { text: "Heure d'envoi" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "ntf-hour", type: "number", min: "0", max: "23" }), h("span", { class: "field-unit", text: "h" }),
          ])]),
          h("div", { class: "field" }, [h("label", { text: "Hôte SMTP" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "ntf-host", type: "text", placeholder: "smtp.office365.com" }),
          ])]),
          h("div", { class: "field" }, [h("label", { text: "Port SMTP" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "ntf-port", type: "number", min: "1", max: "65535" }),
          ])]),
          h("div", { class: "field-check" }, [h("label", null, [
            h("input", { id: "ntf-tls", type: "checkbox" }), h("span", { text: "Utiliser STARTTLS" }),
          ])]),
          h("div", { class: "field" }, [h("label", { text: "Utilisateur SMTP" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "ntf-user", type: "text", placeholder: "flotte@entreprise.fr" }),
          ])]),
          h("div", { class: "field" }, [h("label", { text: "Mot de passe SMTP" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "ntf-pass", type: "password", placeholder: "••••••••" }),
          ]), h("small", { class: "field-help", id: "ntf-pass-help", text: "" })]),
          h("div", { class: "field" }, [h("label", { text: "Adresse expéditrice" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "ntf-from", type: "text", placeholder: "flotte@entreprise.fr" }),
          ])]),
        ]),
        h("div", { style: "display:flex;gap:10px;flex-wrap:wrap" }, [
          h("button", { type: "submit", class: "btn btn-primary btn-sm", html: "Enregistrer" }),
          h("button", { type: "button", id: "ntf-test", class: "btn btn-ghost btn-sm", html: "Envoyer un digest maintenant" }),
        ]),
      ]),
    ]),

    h("div", { class: "panel glass reveal reveal-5", style: "margin-top:18px" }, [
      h("div", { class: "panel-title", html: "🤖 Assistant IA (OpenRouter)" }),
      h("div", { class: "panel-sub", text: "Les questions courantes (échéances, budget, coûts…) fonctionnent déjà sans configuration. Ajoutez une clé API OpenRouter pour des réponses en langage libre sur toute question." }),
      h("div", { id: "ai-status", class: "setting-card glass", style: "margin-bottom:14px" }),
      isAdmin ? h("form", { id: "form-ai" }, [
        h("div", { class: "field" }, [h("label", { text: "Clé API OpenRouter" }), h("div", { class: "input-wrap" }, [
          h("input", { id: "ai-key", type: "password", placeholder: "sk-or-v1-…" }), h("button", { class: "eye", type: "button", dataset: { eye: "ai-key" }, html: svg("eye") }),
        ]), h("small", { class: "field-help", text: "Inscrivez-vous sur openrouter.ai pour obtenir une clé API gratuite ou payante. La clé est stockée localement dans la base." })]),
        h("div", { class: "field" }, [h("label", { text: "Modèle IA" }), h("div", { class: "input-wrap" }, [
          h("input", { id: "ai-model", type: "text", placeholder: "deepseek/deepseek-chat-v3-0324:free" }),
        ]), h("small", { class: "field-help", text: "Modèle OpenRouter par défaut : deepseek/deepseek-chat-v3-0324:free. Vous pouvez changer pour gpt-4o, claude-3.5-sonnet, etc." })]),
        h("button", { type: "submit", class: "btn btn-primary btn-sm", html: "Enregistrer" }),
      ]) : null,
    ]),

    h("div", { class: "panel glass reveal reveal-5", style: "margin-top:18px" }, [
      h("div", { class: "panel-title", html: "🗺️ Cartes & GPS" }),
      h("div", { class: "panel-sub", text: "OpenStreetMap/Leaflet est utilisé automatiquement — aucune clé API requise." }),
    ]),

    h("div", { class: "panel glass reveal reveal-4", style: "margin-top:18px" }, [
      h("div", { class: "panel-title", html: "🗄️ Données de démonstration" }),
      h("div", { class: "panel-sub", text: "Chargez un jeu de données réaliste (véhicules, conducteurs, contrôles, maintenance)." }),
      h("button", { class: "btn btn-ghost btn-sm", onclick: () => loadDemo(), html: "Charger les données de démo" }),
    ]),

    h("div", { class: "panel glass reveal reveal-5", style: "margin-top:18px" }, [
      h("div", { class: "panel-title", html: "💾 Sauvegarde et apparence" }),
      h("div", { class: "panel-sub", text: isAdmin ? "Exportez une copie complète de la base et ajustez le thème de l'interface." : "Ajustez le thème de l'interface." }),
      h("div", { class: "toolbar", style: "margin-top:12px" }, [
        isAdmin ? h("button", { class: "btn btn-ghost btn-sm", onclick: () => downloadBackup(), html: svg("download") + " Sauvegarder la base (SQLite)" }) : null,
        h("button", { class: "btn btn-ghost btn-sm", onclick: () => applyTheme(currentTheme() === "light" ? "dark" : "light"), html: svg("gear") + " Basculer le thème" }),
      ]),
    ]),

    h("div", { class: "panel glass reveal reveal-6", style: "margin-top:18px" }, [
      h("div", { class: "panel-title", html: "🛡️ Sécurité de la plateforme" }),
      h("div", { class: "panel-sub" }, [
        h("ul", { style: "color:var(--text-dim);font-size:13px;line-height:2;padding-left:18px" }, [
          h("li", { text: "Authentification par jeton JWT signé (HS256) avec expiration 7 jours." }),
          h("li", { text: "Mots de passe hachés avec PBKDF2-SHA256 (sel aléatoire)." }),
          h("li", { text: "Requêtes SQL paramétrées — protection contre les injections SQL." }),
          h("li", { text: "Validation et échappement des entrées côté serveur et client." }),
          h("li", { text: "Rôles : administrateur (suppression) vs utilisateur (consultation / édition)." }),
          h("li", { text: "Clé de signature générée automatiquement et stockée hors du code." }),
        ]),
      ]),
    ]),
    usersPanel,
  ]);

  root.innerHTML = "";
  root.appendChild(sections);

  const savePrefs = document.getElementById("form-prefs").querySelector("button[type=submit]");
  if (savePrefs && !isAdmin) savePrefs.disabled = true;

  document.getElementById("form-pwd").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/api/auth/password", "PUT", {
        old_password: document.getElementById("p-old").value,
        new_password: document.getElementById("p-new").value,
      });
      toast("Mot de passe mis à jour.", "success");
      document.getElementById("p-old").value = "";
      document.getElementById("p-new").value = "";
    } catch (err) {
      toast(err.message, "error");
    }
  });

  document.getElementById("form-prefs").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!isAdmin) return;
    try {
      await api("/api/settings", "PUT", {
        alert_threshold: Number(document.getElementById("pref-alert").value),
        forecast_km: Number(document.getElementById("pref-km").value),
        vidange_alert_km: Number(document.getElementById("pref-vidange-km").value),
      });
      toast("Préférences enregistrées.", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  const notifForm = document.getElementById("form-notify");
  if (notifForm) {
    const saveBtn = notifForm.querySelector("button[type=submit]");
    const testBtn = document.getElementById("ntf-test");
    if (!isAdmin) { $$("input", notifForm).forEach((i) => (i.disabled = true)); if (saveBtn) saveBtn.disabled = true; if (testBtn) testBtn.disabled = true; }
    notifForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!isAdmin) return;
      try {
        const body = {
          notify_enabled: document.getElementById("ntf-enabled").checked,
          notify_emails: document.getElementById("ntf-emails").value,
          notify_hour: Number(document.getElementById("ntf-hour").value) || 7,
          smtp_host: document.getElementById("ntf-host").value,
          smtp_port: Number(document.getElementById("ntf-port").value) || 587,
          smtp_tls: document.getElementById("ntf-tls").checked,
          smtp_user: document.getElementById("ntf-user").value,
          smtp_from: document.getElementById("ntf-from").value,
        };
        const pass = document.getElementById("ntf-pass").value;
        if (pass) body.smtp_pass = pass;
        await api("/api/settings", "PUT", body);
        toast("Notifications enregistrées.", "success");
        document.getElementById("ntf-pass").value = "";
        loadNotifySettings();
      } catch (err) {
        toast(err.message, "error");
      }
    });
    if (testBtn) testBtn.addEventListener("click", async () => {
      testBtn.disabled = true; const orig = testBtn.textContent; testBtn.textContent = "Envoi en cours…";
      try {
        const res = await api("/api/notify/send-digest", "POST");
        toast(`Digest envoyé à ${res.recipients} destinataire(s).`, "success");
      } catch (err) {
        toast(err.message, "error");
      } finally {
        testBtn.disabled = false; testBtn.textContent = orig;
      }
    });
  }

  const aiForm = document.getElementById("form-ai");
  if (aiForm) {
    aiForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const key = document.getElementById("ai-key").value.trim();
      const model = document.getElementById("ai-model").value.trim();
      if (!key) { toast("Saisissez une clé API OpenRouter.", "warning"); return; }
      try {
        const body = { openrouter_api_key: key };
        if (model) body.assistant_model = model;
        await api("/api/settings", "PUT", body);
        toast("Clé API OpenRouter enregistrée. L'assistant IA avancé est actif.", "success");
        document.getElementById("ai-key").value = "";
        document.getElementById("ai-model").value = "";
        loadNotifySettings();
      } catch (err) {
        toast(err.message, "error");
      }
    });
  }

  loadPrefs();
  loadNotifySettings();

  if (isAdmin) loadUsers();
}

async function loadNotifySettings() {
  const el = document.getElementById("ntf-enabled");
  const statusEl = document.getElementById("ai-status");
  if (!el && !statusEl) return;
  try {
    const res = await api("/api/settings");
    const s = res.settings || {};
    if (el) {
      document.getElementById("ntf-enabled").checked = !!s.notify_enabled;
      document.getElementById("ntf-emails").value = s.notify_emails || "";
      document.getElementById("ntf-hour").value = s.notify_hour;
      document.getElementById("ntf-host").value = s.smtp_host || "";
      document.getElementById("ntf-port").value = s.smtp_port;
      document.getElementById("ntf-tls").checked = !!s.smtp_tls;
      document.getElementById("ntf-user").value = s.smtp_user || "";
      document.getElementById("ntf-from").value = s.smtp_from || "";
      const passHelp = document.getElementById("ntf-pass-help");
      if (passHelp) passHelp.textContent = s.smtp_pass_set ? "Un mot de passe est déjà enregistré — laissez vide pour le conserver." : "Aucun mot de passe enregistré.";
    }
    if (statusEl) {
      const active = s.assistant_ai_enabled;
      const via = s.assistant_env_key_set ? "variable d'environnement du serveur" : s.assistant_api_key_set ? "clé enregistrée dans les paramètres" : null;
      statusEl.innerHTML = "";
      statusEl.appendChild(h("div", { class: "setting-ico", text: active ? "✅" : "💤" }));
      statusEl.appendChild(h("div", { class: "setting-body" }, [
        h("strong", { text: active ? "Assistant IA avancé actif" : "Assistant IA avancé inactif" }),
        h("small", { text: active ? `Via ${via}. Les questions ouvertes sont répondues par l'IA.` : "Seules les questions courantes (règles locales) sont couvertes pour l'instant." }),
      ]));
    }
  } catch (_) { /* ignore */ }
}

async function loadPrefs() {
  const el1 = document.getElementById("pref-alert");
  const el2 = document.getElementById("pref-km");
  const el3 = document.getElementById("pref-vidange-km");
  if (!el1 || !el2 || !el3) return;
  try {
    const res = await api("/api/settings");
    const s = res.settings || {};
    el1.value = s.alert_threshold;
    el2.value = s.forecast_km;
    el3.value = s.vidange_alert_km;
  } catch (_) { /* ignore */ }
}

/* ------------------------------------------------------------- utilisateurs */
async function loadUsers() {
  const table = document.getElementById("users-table");
  if (!table) return;
  const res = await api("/api/users");
  const users = res.users || [];
  const meId = (state.user || {}).id;
  table.innerHTML = "";
  table.appendChild(h("thead", null, [h("tr", null, [
    h("th", { text: "Utilisateur" }), h("th", { text: "Email" }), h("th", { text: "Rôle" }),
    h("th", { text: "", style: "text-align:right" }),
  ])]));
  if (!users.length) {
    table.appendChild(emptyRow(4, "👥", "Aucun utilisateur."));
    return;
  }
  const tbody = h("tbody", null, []);
  users.forEach((u) => {
    const isAdmin = u.role === "admin";
    const self = u.id === meId;
    tbody.appendChild(h("tr", null, [
      h("td", null, [h("div", { class: "td-strong", text: u.username }), h("small", { class: "td-dim", text: self ? "Vous" : "#" + u.id })]),
      h("td", { class: "td-dim", text: u.email }),
      h("td", null, [h("span", { class: isAdmin ? "badge badge-info" : "badge badge-muted", text: isAdmin ? "Admin" : "User" })]),
      h("td", null, [h("div", { class: "row-actions" }, [
        self ? null : h("button", {
          class: "mini-btn", title: isAdmin ? "Rétrograder en utilisateur" : "Promouvoir administrateur",
          onclick: () => changeUserRole(u, isAdmin ? "user" : "admin"),
          html: isAdmin ? svg("user") : svg("check"),
        }),
        h("button", { class: "mini-btn", title: "Réinitialiser le mot de passe", onclick: () => resetUserPassword(u), html: svg("pencil") }),
        self ? null : h("button", {
          class: "mini-btn danger", title: "Supprimer",
          onclick: () => confirmBox("Supprimer l'utilisateur", `Supprimer le compte « ${u.username} » ?`, () => delUser(u)),
          html: svg("trash"),
        }),
      ])]),
    ]));
  });
  table.appendChild(tbody);
}

async function changeUserRole(u, role) {
  try {
    await api(`/api/users/${u.id}/role`, "PUT", { role });
    toast(`Rôle de ${u.username} mis à jour.`, "success");
    loadUsers();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function delUser(u) {
  try {
    await api(`/api/users/${u.id}`, "DELETE");
    toast("Utilisateur supprimé.", "success");
    loadUsers();
  } catch (err) {
    toast(err.message, "error");
  }
}

function resetUserPassword(u) {
  const box = openModal(`
    <div class="modal-head"><h4>Réinitialiser le mot de passe</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="user-pass">
      <p style="color:var(--text-dim);margin-bottom:14px">Nouveau mot de passe pour <strong>${esc(u.username)}</strong> (8 caractères min, avec un chiffre).</p>
      <div class="field"><label>Mot de passe</label>
        <div class="input-wrap"><input id="up-pass" type="password" required minlength="8" autocomplete="new-password" /></div></div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:18px">
        <button type="button" class="btn btn-ghost" data-close>Annuler</button>
        <button type="button" class="btn btn-primary" id="up-save">Enregistrer <span class="btn-shine"></span></button>
      </div>
    </form>`);
  document.getElementById("up-save").addEventListener("click", async () => {
    const pw = document.getElementById("up-pass").value;
    if (pw.length < 8 || !/\d/.test(pw)) { toast("8 caractères min avec un chiffre.", "error"); return; }
    try {
      await api(`/api/users/${u.id}/password`, "PUT", { password: pw });
      closeModal();
      toast("Mot de passe réinitialisé.", "success");
    } catch (err) { toast(err.message, "error"); }
  });
}

function userModal() {
  if ((state.user || {}).role !== "admin") {
    toast("Action réservée aux administrateurs.", "error");
    return;
  }
  const box = openModal(`
    <div class="modal-head"><h4>Nouvel utilisateur</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="user">
      <div class="form-grid">
        <div class="field"><label>Nom d'utilisateur *</label>
          <div class="input-wrap"><input id="u-name" type="text" required minlength="4" maxlength="32" /></div></div>
        <div class="field"><label>Rôle</label>
          <select class="select" id="u-role" style="width:100%">
            <option value="user">Utilisateur</option>
            <option value="admin">Administrateur</option>
          </select></div>
        <div class="field"><label>Email *</label>
          <div class="input-wrap"><input id="u-email" type="email" required /></div></div>
        <div class="field"><label>Mot de passe *</label>
          <div class="input-wrap"><input id="u-pass" type="password" required minlength="8" autocomplete="new-password" /></div></div>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button type="button" class="btn btn-ghost" data-close>Annuler</button>
        <button type="button" class="btn btn-primary" id="u-save">Créer <span class="btn-shine"></span></button>
      </div>
    </form>`);
  document.getElementById("u-save").addEventListener("click", async () => {
    const body = {
      username: document.getElementById("u-name").value.trim(),
      email: document.getElementById("u-email").value.trim(),
      password: document.getElementById("u-pass").value,
      role: document.getElementById("u-role").value,
    };
    try {
      await api("/api/users", "POST", body);
      closeModal();
      toast("Utilisateur créé.", "success");
      loadUsers();
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

async function loadDemo() {
  try {
    await api("/api/demo", "POST");
    toast("Données de démonstration chargées !", "success");
    navigate("dashboard");
  } catch (err) {
    toast(err.message, "error");
  }
}

/* ------------------------------------------------------------------ divers */
function debounce(fn, ms) {
  let t;
  return function (...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), ms);
  };
}

function tickClock() {
  const now = new Date();
  const clock = document.getElementById("clock");
  const chip = document.getElementById("date-chip");
  if (clock) clock.textContent = now.toLocaleTimeString("fr-FR");
  if (chip) chip.textContent = now.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "long", year: "numeric" });
}

function initAuthForms() {
  $$(".auth-tab").forEach((tab) => tab.addEventListener("click", () => {
    $$(".auth-tab").forEach((t) => t.classList.toggle("active", t === tab));
    document.getElementById("form-login").hidden = tab.dataset.tab !== "login";
    document.getElementById("form-register").hidden = tab.dataset.tab !== "register";
  }));
  document.getElementById("form-login").addEventListener("submit", doLogin);
  document.getElementById("form-register").addEventListener("submit", doRegister);

  const strengthFill = document.getElementById("strength-fill");
  const strengthLabel = document.getElementById("strength-label");
  document.getElementById("reg-pass").addEventListener("input", (e) => {
    const v = e.target.value;
    let score = 0;
    if (v.length >= 8) score++;
    if (v.length >= 12) score++;
    if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score++;
    if (/\d/.test(v)) score++;
    if (/[^A-Za-z0-9]/.test(v)) score++;
    const pct = Math.min(100, score * 20);
    strengthFill.style.width = pct + "%";
    strengthFill.style.background = score <= 1 ? "var(--red)" : score <= 3 ? "var(--amber)" : "var(--green)";
    strengthLabel.textContent = score <= 1 ? "Faible" : score <= 3 ? "Correct" : "Excellent";
  });
}

function initUI() {
  const preloader = document.getElementById("preloader");
  setTimeout(() => preloader.classList.add("done"), 1300);
  applyTheme();

  document.getElementById("btn-logout").addEventListener("click", logout);
  document.getElementById("btn-hamburger").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("open");
  });
  $$("#sidebar-nav .nav-item").forEach((n) =>
    n.addEventListener("click", () => {
      navigate(n.dataset.route);
      document.getElementById("sidebar").classList.remove("open");
    }));

  const btnTheme = document.getElementById("btn-theme");
  if (btnTheme) btnTheme.addEventListener("click", () => applyTheme(currentTheme() === "light" ? "dark" : "light"));

  const btnNotif = document.getElementById("btn-notif");
  if (btnNotif) btnNotif.addEventListener("click", (e) => { e.stopPropagation(); toggleNotif(); });
  const btnNotifAll = document.getElementById("btn-notif-all");
  if (btnNotifAll) btnNotifAll.addEventListener("click", () => { toggleNotif(false); navigate("activity"); });

  const btnAssistant = document.getElementById("btn-assistant");
  if (btnAssistant) btnAssistant.addEventListener("click", (e) => { e.stopPropagation(); toggleAssistant(); });
  const btnAssistantClose = document.getElementById("btn-assistant-close");
  if (btnAssistantClose) btnAssistantClose.addEventListener("click", () => toggleAssistant(false));
  const btnAssistantClear = document.getElementById("btn-assistant-clear");
  if (btnAssistantClear) btnAssistantClear.addEventListener("click", () => { if (confirm("Effacer tout l'historique ?")) clearAssistantHistory(); });
  const assistantInput = document.getElementById("assistant-input");
  if (assistantInput) assistantInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); sendAssistantMessage(assistantInput.value); }
  });
  const assistantSend = document.getElementById("assistant-send");
  if (assistantSend) assistantSend.addEventListener("click", () => sendAssistantMessage(document.getElementById("assistant-input").value));

  document.addEventListener("click", (e) => {
    const panel = document.getElementById("assistant-panel");
    if (panel && !panel.hidden && !e.target.closest("#assistant-panel") && !e.target.closest("#btn-assistant")) toggleAssistant(false);
  });

  document.addEventListener("click", (e) => {
    const panel = document.getElementById("notif-panel");
    if (panel && !panel.hidden && !e.target.closest("#notif-panel")) toggleNotif(false);
  });

  window.addEventListener("hashchange", renderRoute);
  setInterval(tickClock, 1000);
  setInterval(loadNotifications, 90000);
  tickClock();

  buildPalette();
  document.getElementById("btn-search").addEventListener("click", () => togglePalette(true));
  document.getElementById("palette-backdrop").addEventListener("click", () => togglePalette(false));
  const pInput = document.getElementById("palette-input");
  pInput.addEventListener("input", () => { paletteIdx = 0; renderPalette(); });
  pInput.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); paletteIdx = Math.min(paletteIdx + 1, paletteResults.length - 1); renderPalette(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); paletteIdx = Math.max(paletteIdx - 1, 0); renderPalette(); }
    else if (e.key === "Enter") { e.preventDefault(); runPalette(paletteIdx); }
    else if (e.key === "Escape") { e.preventDefault(); togglePalette(false); }
  });
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      togglePalette();
    }
  });

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".eye");
    if (!btn) return;
    const inp = document.getElementById(btn.dataset.eye);
    if (inp) inp.type = inp.type === "password" ? "text" : "password";
  });
}

/* --------------------------------------------------------------- thème clair / sombre */
function currentTheme() {
  const saved = localStorage.getItem("nf_theme");
  return saved === "light" ? "light" : "dark";
}

function applyTheme(next) {
  const theme = next || currentTheme();
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("nf_theme", theme);
  const sun = document.getElementById("icon-theme");
  const moon = document.getElementById("icon-theme-moon");
  if (sun && moon) {
    sun.style.display = theme === "dark" ? "block" : "none";
    moon.style.display = theme === "dark" ? "none" : "block";
  }
}

/* --------------------------------------------------------------- notifications */
const ACTION_LABEL = {
  create: "Création",
  update: "Modification",
  delete: "Suppression",
  login: "Connexion",
  logout: "Déconnexion",
  export: "Export",
  import: "Import",
};

function badgeForAction(action) {
  const map = { delete: "danger", create: "success", import: "success", export: "info", login: "info", update: "warning" };
  return h("span", { class: `badge badge-${map[action] || "default"}`, text: ACTION_LABEL[action] || action || "—" });
}

function notifItem(n, kind) {
  const icon = kind === "danger" || kind === "warning" ? "alert" : "history";
  const title = kind === "danger" ? (n.label || n.type || "Alerte")
    : kind === "warning" ? (n.label || n.type || "Avertissement")
    : (n.action || n.entity || "Événement");
  const desc = kind === "danger" || kind === "warning"
    ? `${n.msg || ""} ${n.vehicle || ""}${n.immatriculation ? " · " + n.immatriculation : ""}`
    : `${n.username || ""}${n.action ? " · " + (ACTION_LABEL[n.action] || n.action) : ""}`;
  return h("button", { class: `notif-item ${kind}`, onclick: () => toggleNotif(false) }, [
    h("span", { class: `notif-dot-ico ${kind}`, html: svg(icon) }),
    h("span", { class: "notif-text" }, [
      h("strong", { text: title }),
      h("small", { text: desc }),
    ]),
  ]);
}

async function loadNotifications() {
  if (!state.token) return;
  try {
    const res = await api("/api/notifications");
    const count = (res.danger_count || 0) + (res.warning_count || 0);
    const dot = document.getElementById("notif-dot");
    if (dot) {
      dot.hidden = count === 0;
      dot.textContent = count > 99 ? "99+" : String(count);
      dot.classList.toggle("pulse", (res.danger_count || 0) > 0);
    }
    const body = document.getElementById("notif-body");
    if (!body) return;
    body.innerHTML = "";
    const groups = [["alerts", "danger"], ["warnings", "warning"], ["events", "info"]];
    let any = false;
    for (const [key, kind] of groups) {
      const items = (res[key] || []).slice(0, 12);
      if (!items.length) continue;
      any = true;
      body.appendChild(h("div", { class: "notif-group" }, [
        h("div", { class: "notif-group-label", text: key === "alerts" ? "Alertes" : key === "warnings" ? "Avertissements" : "Événements récents" }),
        ...items.map((n) => notifItem(n, kind)),
      ]));
    }
    if (!any) {
      body.appendChild(h("div", { class: "notif-empty" }, [h("span", { text: "🔔" }), h("p", { text: "Aucune notification pour le moment." })]));
    }
  } catch (_) { /* silencieux */ }
}

function toggleNotif(force) {
  const panel = document.getElementById("notif-panel");
  if (!panel) return;
  const open = force != null ? force : panel.hidden;
  panel.hidden = !open;
  if (open) loadNotifications();
}

/* --------------------------------------------------------------- assistant intelligent */
const ASSISTANT_SUGGESTIONS = [
  "Quelles échéances arrivent bientôt ?",
  "Où en est le budget maintenance ?",
  "Quel véhicule coûte le plus cher ?",
  "Quelle est la prochaine vidange ?",
  "Combien de véhicules en panne ?",
  "Quels véhicules sont en direction générale ?",
  "Quels véhicules Toyota avons-nous ?",
  "Les permis sont-ils à jour ?",
];
let assistantHistory = [];
let assistantBusy = false;

async function loadAssistantHistory() {
  try {
    const hist = await api("/api/assistant/history");
    if (hist && hist.length) {
      assistantHistory = hist.map((m) => ({ role: m.role === "assistant" ? "bot" : "user", text: m.content }));
      const body = document.getElementById("assistant-body");
      if (!body) return;
      body.innerHTML = "";
      assistantHistory.forEach((m) => appendAssistantMsg(m.text, m.role, m.role === "bot" ? "local" : null));
    }
  } catch (_) { /* ignore */ }
}

function assistantWelcome() {
  const body = document.getElementById("assistant-body");
  if (!body) return;
  body.innerHTML = "";
  body.appendChild(h("div", { class: "assistant-msg bot" }, [
    h("div", { text: "Bonjour ! Je suis l'assistant NexFleet. Posez-moi une question sur votre parc, votre budget ou vos échéances. J'ai mémoire de nos précédents échanges." }),
  ]));
  const chips = document.getElementById("assistant-panel").querySelector(".assistant-suggestions");
  if (chips) chips.remove();
  const wrap = h("div", { class: "assistant-suggestions" },
    ASSISTANT_SUGGESTIONS.map((s) => h("button", { class: "assistant-chip", type: "button", onclick: () => sendAssistantMessage(s), text: s })));
  document.getElementById("assistant-panel").insertBefore(wrap, document.querySelector(".assistant-composer"));
}

async function toggleAssistant(force) {
  const panel = document.getElementById("assistant-panel");
  if (!panel) return;
  const open = force != null ? force : panel.hidden;
  panel.hidden = !open;
  if (open && !assistantHistory.length) {
    await loadAssistantHistory();
    if (!assistantHistory.length) assistantWelcome();
  }
  if (open) setTimeout(() => document.getElementById("assistant-input").focus(), 80);
}

function appendAssistantMsg(text, who, sourceTag) {
  const body = document.getElementById("assistant-body");
  if (!body) return;
  const label = sourceTag === "openrouter" ? "IA avancée" : sourceTag === "local" ? "Réponse locale" : null;
  const msg = h("div", { class: `assistant-msg ${who}` }, [
    h("div", { text: text }),
    label ? h("span", { class: "assistant-source-tag", text: label }) : null,
  ]);
  body.appendChild(msg);
  body.scrollTop = body.scrollHeight;
}

async function clearAssistantHistory() {
  try { await api("/api/assistant/history", "DELETE"); } catch (_) { /* ignore */ }
  assistantHistory = [];
  const body = document.getElementById("assistant-body");
  if (body) body.innerHTML = "";
  assistantWelcome();
}

async function sendAssistantMessage(text) {
  text = (text || "").trim();
  if (!text || assistantBusy) return;
  const input = document.getElementById("assistant-input");
  if (input) input.value = "";
  const chips = document.querySelector("#assistant-panel .assistant-suggestions");
  if (chips) chips.remove();

  appendAssistantMsg(text, "user");
  assistantHistory.push({ role: "user", text });
  assistantBusy = true;

  const body = document.getElementById("assistant-body");
  const typing = h("div", { class: "assistant-typing" }, [h("span"), h("span"), h("span")]);
  body.appendChild(typing);
  body.scrollTop = body.scrollHeight;

  try {
    const res = await api("/api/assistant/ask", "POST", { question: text });
    typing.remove();
    appendAssistantMsg(res.answer, "bot", res.source);
    assistantHistory.push({ role: "bot", text: res.answer });
  } catch (err) {
    typing.remove();
    appendAssistantMsg(err.message || "Une erreur est survenue.", "bot");
  } finally {
    assistantBusy = false;
  }
}

/* --------------------------------------------------------------- activité (audit) */
let activityState = { page: 1, per_page: 50, action: "", username: "", search: "" };
let activityUsers = [];

async function viewActivity(root) {
  root.innerHTML = "";
  root.appendChild(h("div", { class: "page-head" }, [
    h("div", null, [
      h("h3", { text: "Journal des actions" }),
      h("p", { text: "Toutes les traces d'activité du parc, filtrables et paginées." }),
    ]),
    h("div", { class: "page-actions" }, [
      h("button", { class: "btn btn-ghost btn-sm", id: "act-refresh", html: svg("history") + " Actualiser" }),
      h("button", { class: "btn btn-primary btn-sm", id: "act-export", html: svg("download") + " Exporter CSV" }),
    ]),
  ]));

  const card = h("div", { class: "table-card glass reveal reveal-1" }, [
    h("div", { class: "toolbar", style: "padding:0 0 12px" }, [
      h("div", { class: "search-wrap" }, [h("input", {
        id: "act-search", type: "text", placeholder: "Rechercher (entité, détails, utilisateur)…",
        value: activityState.search,
        oninput: () => { const q = document.getElementById("act-search"); clearTimeout(activityState._t); activityState._t = setTimeout(() => { activityState.search = q.value; activityState.page = 1; renderActivity(); }, 350); },
      })]),
      h("select", { class: "select", id: "act-action", onchange: (e) => { activityState.action = e.target.value; activityState.page = 1; renderActivity(); } }, []),
      h("select", { class: "select", id: "act-user", onchange: (e) => { activityState.username = e.target.value; activityState.page = 1; renderActivity(); } }, []),
      h("div", { class: "spacer" }),
      h("div", { class: "panel-sub", style: "margin:0", id: "act-total", text: "…" }),
    ]),
    h("div", { class: "table-scroll" }, [h("table", { class: "data" })]),
    h("div", { class: "pager", id: "act-pager" }, []),
  ]);
  root.appendChild(card);

  const res = await api("/api/audit?per_page=1&page=1");
  activityUsers = res.users || [];
  await renderActivity();

  document.getElementById("act-refresh").onclick = () => { activityState.page = 1; renderActivity(); };
  document.getElementById("act-export").onclick = () => exportAuditCsv();
}

async function renderActivity() {
  const actionSel = document.getElementById("act-action");
  const userSel = document.getElementById("act-user");
  if (actionSel && actionSel.options.length === 0) {
    const opts = [["", "Toutes les actions"], ["create", "Créations"], ["update", "Modifications"],
                  ["delete", "Suppressions"], ["login", "Connexions"], ["export", "Exports"],
                  ["import", "Imports"], ["logout", "Déconnexions"]];
    opts.forEach(([v, l]) => { const o = h("option", { value: v, text: l }); o.selected = activityState.action === v; actionSel.appendChild(o); });
  }
  if (userSel && userSel.options.length === 0) {
    const u0 = h("option", { value: "", text: "Tous les utilisateurs" });
    u0.selected = !activityState.username;
    userSel.appendChild(u0);
    activityUsers.forEach((u) => userSel.appendChild(h("option", { value: u, text: u })));
  }

  const qs = new URLSearchParams({ page: activityState.page, per_page: activityState.per_page });
  if (activityState.action) qs.set("action", activityState.action);
  if (activityState.username) qs.set("username", activityState.username);
  if (activityState.search) qs.set("search", activityState.search);

  let res;
  try { res = await api("/api/audit?" + qs.toString()); } catch (e) { toast(e.message, "error"); return; }
  const events = res.events || [];
  activityState.page = res.page || 1;

  const total = document.getElementById("act-total");
  if (total) total.textContent = `${res.total || 0} événement(s) · page ${res.page} / ${res.pages || 1}`;

  renderSummary(res.summary || {});
  const card = document.getElementById("content");
  const old = card.querySelector("table.data tbody");
  if (old) old.remove();
  const nt = h("tbody", null, []);
  card.querySelector("table.data").appendChild(nt);

  if (!events.length) {
    nt.appendChild(emptyRow(5, "📜", "Aucun événement ne correspond aux critères."));
  } else {
    events.forEach((e) => {
      const details = e.details;
      const detailTxt = details == null ? "—" : typeof details === "string" ? details : JSON.stringify(details);
      nt.appendChild(h("tr", null, [
        h("td", { class: "td-dim", text: fmtDateTime(e.created_at) }),
        h("td", { class: "td-strong", text: e.username || "—" }),
        h("td", null, [badgeForAction(e.action)]),
        h("td", { text: e.entity || "—" }),
        h("td", { class: "td-dim", text: detailTxt }),
      ]));
    });
  }
  renderPager(res.pages || 1, res.page || 1, res.total || 0);
}

function renderSummary(summary) {
  const root = document.getElementById("content");
  let wrap = root.querySelector(".act-summary");
  if (!wrap) {
    wrap = h("div", { class: "act-summary" });
    root.querySelector(".toolbar").after(wrap);
  }
  wrap.innerHTML = "";
  const order = [["create", "Créations", "success"], ["update", "Modifications", "warning"],
                 ["delete", "Suppressions", "danger"], ["login", "Connexions", "info"],
                 ["export", "Exports", "info"], ["import", "Imports", "success"]];
  let shown = 0;
  order.forEach(([k, label, cls]) => {
    if (!summary[k]) return;
    shown++;
    wrap.appendChild(h("span", { class: `badge badge-${cls}`, text: `${label} : ${summary[k]}` }));
  });
  const other = Object.entries(summary).filter(([k]) => !order.some(([o]) => o === k));
  other.forEach(([k, n]) => { shown++; wrap.appendChild(h("span", { class: "badge badge-default", text: `${k} : ${n}` })); });
  if (!shown) wrap.appendChild(h("span", { class: "badge badge-muted", text: "Aucune action" }));
}

function renderPager(pages, page, total) {
  const pager = document.getElementById("content").querySelector("#act-pager");
  if (!pager) return;
  pager.innerHTML = "";
  const mk = (label, disabled, fn, cls) => h("button", { class: "btn btn-ghost btn-sm" + (cls ? " " + cls : ""), disabled: disabled, onclick: fn, text: label });
  pager.append(
    mk("← Précédent", page <= 1, () => { activityState.page--; renderActivity(); }),
    h("span", { class: "panel-sub", style: "margin:0 6px", text: `${total} événement(s) · ${pages} page(s)` }),
    mk("Suivant →", page >= pages, () => { activityState.page++; renderActivity(); }),
  );
}

async function exportAuditCsv() {
  toast("Préparation de l'export…", "info");
  const qs = new URLSearchParams({ per_page: 500 });
  if (activityState.action) qs.set("action", activityState.action);
  if (activityState.username) qs.set("username", activityState.username);
  if (activityState.search) qs.set("search", activityState.search);
  let all = [];
  let page = 1, pages = 1;
  do {
    qs.set("page", String(page));
    let res;
    try { res = await api("/api/audit?" + qs.toString()); } catch (e) { toast(e.message, "error"); return; }
    all = all.concat(res.events || []);
    pages = res.pages || 1;
    page++;
  } while (page <= pages && all.length < 2000);
  const head = ["date", "utilisateur", "action", "entite", "details"];
  const rows = all.map((e) => [
    e.created_at || "", e.username || "", e.action || "", e.entity || "",
    typeof e.details === "string" ? e.details : JSON.stringify(e.details || ""),
  ]);
  const csv = [head, ...rows]
    .map((r) => r.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(";"))
    .join("\r\n");
  downloadBlob(new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" }), "journal_activite.csv");
  toast(`Export : ${all.length} événement(s).`, "success");
}

/* --------------------------------------------------------------- tiroir (drawer) */
function openDrawer() {
  closeDrawer();
  let root = document.getElementById("drawer-root");
  if (!root) {
    root = h("div", { id: "drawer-root", class: "drawer-root" });
    document.body.appendChild(root);
  }
  root.innerHTML = "";
  const drawer = h("div", { class: "drawer glass" });
  root.append(h("div", { class: "drawer-backdrop", onclick: closeDrawer }), drawer);
  requestAnimationFrame(() => root.classList.add("open"));
  return drawer;
}

function closeDrawer() {
  const root = document.getElementById("drawer-root");
  if (!root) return;
  root.classList.remove("open");
  setTimeout(() => root.remove(), 320);
}

function drawerKv(label, value) {
  return h("div", { class: "drawer-kv" }, [h("small", { text: label }), h("strong", { text: value })]);
}

async function vehicleDetailDrawer(v) {
  const drawer = openDrawer();
  drawer.appendChild(h("div", { class: "drawer-head" }, [
    h("div", { class: "drawer-hero" }, [
      vehicleThumb(v, 54),
      h("div", null, [
        h("h3", { text: `${v.marque} ${v.modele}` }),
        h("p", { class: "drawer-immat", text: v.immatriculation }),
      ]),
    ]),
    h("button", { class: "modal-x", onclick: closeDrawer, style: "position:static;flex:none", text: "✕" }),
  ]));
  const body = h("div", { class: "drawer-body" });
  const foot = h("div", { class: "drawer-actions" }, [
    h("button", { class: "btn btn-primary btn-sm", id: "drawer-pdf", html: svg("file") + " Fiche PDF" }),
    h("button", { class: "btn btn-ghost btn-sm", id: "drawer-edit", html: svg("pencil") + " Modifier" }),
    h("button", { class: "btn btn-danger btn-sm", id: "drawer-del", html: svg("trash") + " Supprimer" }),
  ]);
  drawer.append(body, foot);

  let costs = [];
  try { costs = (await api("/api/stats")).cost_per_km || []; } catch (_) {}

  try {
    const res = await api(`/api/vehicles/${v.id}/detail`);
    const veh = res.vehicle || v;
    const ck = costs.find((c) => c.immatriculation === veh.immatriculation);
    body.appendChild(h("div", { class: "drawer-grid" }, [
      drawerKv("Statut", veh.statut || "—"),
      drawerKv("Direction", veh.direction || "—"),
      drawerKv("Année", veh.annee || "—"),
      drawerKv("Carburant", veh.carburant || "—"),
      drawerKv("Affectation", veh.affectation || "—"),
      drawerKv("Kilométrage", fmtKm(veh.kilometrage)),
      drawerKv("Coût / km", ck ? `${ck.value.toLocaleString("fr-FR")} FCFA` : "—"),
      drawerKv("Assurance", fmtDate(veh.assurance_exp)),
      drawerKv("Contrôle technique", fmtDate(veh.ctrl_tech_exp)),
      drawerKv("Vignette", fmtDate(veh.vignette_exp)),
      drawerKv("Note vignette", veh.vignette_note || "—"),
      drawerKv("Note CT", veh.ct_note || "—"),
      drawerKv("N° Châssis", veh.num_chassis || "—"),
      drawerKv("N° Moteur", veh.num_moteur || "—"),
      drawerKv("Carte grise", veh.carte_grise || "—"),
      drawerKv("Expiration carte grise", fmtDate(veh.carte_grise_exp)),
      drawerKv("Note carte grise", veh.carte_grise_note || "—"),
      drawerKv("Chevaux (CV)", veh.cv || "—"),
      drawerKv("Latitude", veh.lat || "—"),
      drawerKv("Longitude", veh.lng || "—"),
    ]));

    const alerts = (veh.alerts || []).filter((a) => a);
    if (alerts.length) {
      body.appendChild(h("div", { class: "drawer-section" }, [
        h("h5", { text: "Alertes" }),
        ...alerts.map((a) => h("div", { class: `drawer-alert ${a.level === "danger" ? "danger" : "warning"}` }, [
          h("strong", { text: a.label || a.type || "Alerte" }),
          h("small", { text: `${a.msg || ""}${a.days != null ? " (J-" + a.days + ")" : ""}` }),
        ])),
      ]));
    }

    const controls = res.controls || [];
    if (controls.length) {
      body.appendChild(h("div", { class: "drawer-section" }, [
        h("h5", { text: `Contrôles (${controls.length})` }),
        ...controls.map((c) => h("div", { class: "drawer-row" }, [
          h("strong", { text: `${c.type || "Contrôle"} · ${fmtDate(c.date)}` }),
          h("small", { text: `${c.resultat || ""}${c.d_nom ? " — " + c.d_prenom + " " + c.d_nom : ""}${c.notes ? " · " + c.notes : ""}` }),
        ])),
      ]));
    }

    const maintenance = res.maintenance || [];
    if (maintenance.length) {
      body.appendChild(h("div", { class: "drawer-section" }, [
        h("h5", { text: `Maintenance (${maintenance.length})` }),
        ...maintenance.map((m) => h("div", { class: "drawer-row" }, [
          h("strong", { text: `${m.type || "Intervention"} · ${fmtDate(m.date)}` }),
          h("small", { text: `${m.notes || ""}${m.garage ? " — " + m.garage : ""}${m.cout ? " — " + fmtMoney(m.cout) : ""}` }),
        ])),
      ]));
    }

    renderOdo(body, veh);
    renderDocs(body, veh);
    renderTires(body, veh);

    if (!alerts.length && !controls.length && !maintenance.length) {
      body.appendChild(h("p", { class: "drawer-empty", text: "Aucune alerte, contrôle ou intervention à afficher." }));
    }
  } catch (err) {
    body.appendChild(h("p", { class: "drawer-empty", text: err.message }));
  }

  foot.querySelector("#drawer-pdf").addEventListener("click", () => getVehiclePdf(v));
  foot.querySelector("#drawer-edit").addEventListener("click", () => { closeDrawer(); vehicleModal(v); });
  const delBtn = foot.querySelector("#drawer-del");
  if ((state.user || {}).role !== "admin") {
    delBtn.hidden = true;
  } else {
    delBtn.addEventListener("click", () => {
      closeDrawer();
      confirmBox("Supprimer le véhicule", `Supprimer ${v.marque} ${v.modele} (${v.immatriculation}) ? Cette action est irréversible.`, () => delVehicle(v));
    });
  }
}

/* --------------------------------------------------------------- section odomètre */
async function renderOdo(body, veh) {
  const sec = h("div", { class: "drawer-section" }, [
    h("h5", { text: "Historique kilométrique" }),
  ]);
  const wrap = h("div", null);
  sec.appendChild(wrap);
  body.appendChild(sec);

  const load = async () => {
    wrap.innerHTML = "";
    const res = await api(`/api/vehicles/${veh.id}/odometer`);
    const rows = (res.odometer || []).slice().sort((a, b) => (a.date < b.date ? -1 : 1));
    const isAdmin = (state.user || {}).role === "admin";

    const form = h("div", { class: "odo-form" }, [
      h("input", { class: "select", id: "odo-date", type: "date", value: new Date().toISOString().slice(0, 10) }),
      h("input", { class: "odo-input", id: "odo-km", type: "number", min: "0", placeholder: "Km actuel" }),
      h("button", { class: "mini-btn", id: "odo-add", title: "Ajouter un relevé", text: "+" }),
    ]);
    form.querySelector("#odo-add").addEventListener("click", async () => {
      const km = Number(form.querySelector("#odo-km").value || 0);
      const date = form.querySelector("#odo-date").value;
      if (km <= 0) { toast("Indiquez un kilométrage.", "error"); return; }
      try {
        await api(`/api/vehicles/${veh.id}/odometer`, "POST", { date, kilometres: km });
        toast("Relevé ajouté.", "success");
        load();
      } catch (err) { toast(err.message, "error"); }
    });
    wrap.appendChild(form);

    if (rows.length >= 2) {
      wrap.appendChild(h("div", { class: "chart-wrap", style: "height:120px;margin-bottom:10px" }, [h("canvas", { id: "odo-chart" })]));
    }

    if (!rows.length) {
      wrap.appendChild(h("p", { class: "drawer-empty", text: "Aucun relevé. Ajoutez le kilométrage actuel." }));
      return;
    }

    const list = h("div", null);
    [...rows].reverse().slice(0, 8).forEach((r) => {
      list.appendChild(h("div", { class: "drawer-row odo-row" }, [
        h("strong", { text: fmtKm(r.kilometres) }),
        h("small", { text: `${fmtDate(r.date)}${r.note ? " · " + r.note : ""}` }),
        isAdmin ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer le relevé", "Supprimer ce relevé kilométrique ?", async () => {
          try { await api(`/api/odometer/${r.id}`, "DELETE"); toast("Relevé supprimé.", "success"); load(); }
          catch (err) { toast(err.message, "error"); }
        }), html: svg("trash") }) : null,
      ]));
    });
    wrap.appendChild(list);

    requestAnimationFrame(() => {
      const cv = document.getElementById("odo-chart");
      if (cv && rows.length >= 2) {
        drawLine(cv, rows.map((r) => fmtDate(r.date)), rows.map((r) => Number(r.kilometres)));
      }
    });
  };
  load();
}

/* --------------------------------------------------------------- section documents */
async function renderDocs(body, veh) {
  const sec = h("div", { class: "drawer-section" }, [h("h5", { text: "Documents" })]);
  const wrap = h("div", null);
  sec.appendChild(wrap);
  body.appendChild(sec);

  const isAdmin = (state.user || {}).role === "admin";
  const load = async () => {
    wrap.innerHTML = "";
    const res = await api(`/api/vehicles/${veh.id}/documents`);
    const docs = res.documents || [];

    if (isAdmin) {
      const up = h("div", { class: "doc-upload" }, [
        h("input", { class: "doc-label", id: "doc-label", type: "text", placeholder: "Libellé (ex. Carte grise)" }),
        h("input", { class: "doc-file", id: "doc-file", type: "file", title: "Choisir un fichier" }),
        h("button", { class: "mini-btn", id: "doc-add", html: svg("upload") + " Ajouter" }),
      ]);
      up.querySelector("#doc-add").addEventListener("click", async () => {
        const f = up.querySelector("#doc-file").files[0];
        if (!f) { toast("Choisissez un fichier.", "error"); return; }
        const fd = new FormData();
        fd.append("file", f);
        fd.append("label", up.querySelector("#doc-label").value.trim());
        const resf = await fetch(`/api/vehicles/${veh.id}/documents`, {
          method: "POST",
          headers: { Authorization: "Bearer " + state.token },
          body: fd,
        });
        let data = null;
        try { data = await resf.json(); } catch (_) {}
        if (!resf.ok) { toast((data && data.error) || "Impossible d'ajouter le document.", "error"); return; }
        toast("Document ajouté.", "success");
        load();
      });
      wrap.appendChild(up);
    }

    if (!docs.length) {
      wrap.appendChild(h("p", { class: "drawer-empty", text: "Aucun document (carte grise, assurance…)." }));
      return;
    }
    docs.forEach((d) => {
      const ext = (d.filename || "").split(".").pop().toUpperCase();
      wrap.appendChild(h("div", { class: "doc-item" }, [
        h("span", { class: "doc-ico", text: ext }),
        h("div", { class: "doc-body" }, [
          h("strong", { text: d.label || d.filename }),
          h("small", { text: d.filename }),
        ]),
        h("a", { class: "mini-btn", href: d.stored, target: "_blank", rel: "noopener", title: "Ouvrir", html: svg("download") }),
        isAdmin ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer le document", `Supprimer « ${d.label || d.filename} » ?`, async () => {
          try { await api(`/api/documents/${d.id}`, "DELETE"); toast("Document supprimé.", "success"); load(); }
          catch (err) { toast(err.message, "error"); }
        }), html: svg("trash") }) : null,
      ]));
    });
  };
  load();
}

/* --------------------------------------------------------------- section pneumatiques */
async function renderTires(body, veh) {
  const sec = h("div", { class: "drawer-section" }, [h("h5", { text: "Pneumatiques" })]);
  const wrap = h("div", null);
  sec.appendChild(wrap);
  body.appendChild(sec);

  const isAdmin = (state.user || {}).role === "admin";
  const load = async () => {
    wrap.innerHTML = "";
    const res = await api(`/api/vehicles/${veh.id}/tires`);
    const tires = res.tires || [];
    const byPos = { AVG: null, AVD: null, ARG: null, ARD: null };
    tires.forEach((t) => { if (byPos[t.position] === undefined) byPos[t.position] = t; else byPos[t.position] = t; });

    const grid = h("div", { class: "tire-grid" });
    Object.entries(byPos).forEach(([pos, t]) => {
      const cell = h("div", { class: "tire-card" + (t ? "" : " empty") }, [
        h("div", { class: "tire-pos", text: pos }),
        t ? h("div", { class: "tire-info" }, [
          h("strong", { text: `${t.marque || "Pneu"} ${t.taille || ""}`.trim() }),
          h("small", { class: "tire-etat " + (t.etat || "").toLowerCase().replace(" ", "-"), text: t.etat || "—" }),
          t.date_montage ? h("small", { text: `Monté le ${fmtDate(t.date_montage)}` }) : null,
        ]) : h("small", { class: "tire-info-empty", text: "Non renseigné" }),
        h("div", { class: "tire-actions" }, [
          isAdmin ? h("button", { class: "mini-btn", title: t ? "Modifier" : "Ajouter", onclick: () => tireModal(t, veh, load), html: svg(t ? "pencil" : "plus") }) : null,
          isAdmin && t ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer le pneu", `Supprimer le pneu ${pos} ?`, async () => {
            try { await api(`/api/tires/${t.id}`, "DELETE"); toast("Pneu supprimé.", "success"); load(); }
            catch (err) { toast(err.message, "error"); }
          }), html: svg("trash") }) : null,
        ]),
      ]);
      grid.appendChild(cell);
    });
    wrap.appendChild(grid);
    wrap.appendChild(h("p", { class: "drawer-hint", text: "AVG / AVD : train avant · ARG / ARD : train arrière" }));
  };
  load();
}

function tireModal(t, veh, after) {
  const editing = !!t;
  const val = (f, d) => t ? esc(t[f] || "") : d;
  openModal(`
    <div class="modal-head"><h4>${editing ? "Modifier le pneu " + esc(t.position) : "Nouveau pneu"}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="tire">
      <div class="form-grid">
        <div class="field"><label>Position *</label>
          <select class="select" id="t-pos" style="width:100%">
            ${["AVG", "AVD", "ARG", "ARD"].map((p) => `<option ${t && t.position === p ? "selected" : ""}>${p}</option>`).join("")}
          </select></div>
        <div class="field"><label>État *</label>
          <select class="select" id="t-etat" style="width:100%">
            ${["Bon", "À surveiller", "À remplacer", "Usé"].map((s) => `<option ${t && t.etat === s ? "selected" : ""}>${s}</option>`).join("")}
          </select></div>
        <div class="field"><label>Marque</label>
          <div class="input-wrap"><input id="t-marque" type="text" value="${val("marque")}" placeholder="Michelin" /></div></div>
        <div class="field"><label>Taille</label>
          <div class="input-wrap"><input id="t-taille" type="text" value="${val("taille")}" placeholder="225/70 R16" /></div></div>
        <div class="field"><label>Date de montage</label>
          <div class="input-wrap"><input id="t-montage" type="date" value="${val("date_montage")}" /></div></div>
        <div class="field"><label>Date de remplacement</label>
          <div class="input-wrap"><input id="t-rempl" type="date" value="${val("date_remplacement")}" /></div></div>
        <div class="field full"><label>Notes</label>
          <div class="input-wrap"><input id="t-note" type="text" value="${val("note")}" placeholder="Usure, permutation…" /></div></div>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button type="button" class="btn btn-ghost" data-close>Annuler</button>
        <button type="button" class="btn btn-primary" id="tire-save">${editing ? "Enregistrer" : "Ajouter"} <span class="btn-shine"></span></button>
      </div>
    </form>`);

  document.getElementById("tire-save").addEventListener("click", async () => {
    const body = {
      position: document.getElementById("t-pos").value,
      etat: document.getElementById("t-etat").value,
      marque: document.getElementById("t-marque").value,
      taille: document.getElementById("t-taille").value,
      date_montage: document.getElementById("t-montage").value || null,
      date_remplacement: document.getElementById("t-rempl").value || null,
      note: document.getElementById("t-note").value,
    };
    try {
      if (editing) await api(`/api/tires/${t.id}`, "PUT", body);
      else await api(`/api/vehicles/${veh.id}/tires`, "POST", body);
      closeModal();
      toast(editing ? "Pneu mis à jour." : "Pneu ajouté.", "success");
      after();
    } catch (err) { toast(err.message, "error"); }
  });
}

function drawLine(canvas, labels, values) {
  const { ctx, w, h } = prepCanvas(canvas);
  const pad = 10;
  const t0 = performance.now(), dur = 800;
  (function step(t) {
    const p = Math.min(1, (t - t0) / dur), ease = 1 - Math.pow(1 - p, 3);
    ctx.clearRect(0, 0, w, h);
    const min = Math.min(...values), max = Math.max(...values);
    const span = Math.max(max - min, 1);
    const px = (i) => values.length === 1 ? w / 2 : pad + (w - pad * 2) * i / (values.length - 1);
    const py = (v) => h - pad - (h - pad * 2) * (v - min) / span;
    ctx.strokeStyle = "rgba(255,255,255,0.07)"; ctx.lineWidth = 1;
    [0.25, 0.5, 0.75].forEach((f) => {
      const y = pad + (h - pad * 2) * f;
      ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(w - pad, y); ctx.stroke();
    });
    ctx.beginPath();
    values.forEach((v, i) => {
      const x = px(i), y = py(v) * ease + (h - pad) * (1 - ease);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    const grad = ctx.createLinearGradient(0, 0, w, 0);
    grad.addColorStop(0, "#6366f1"); grad.addColorStop(1, "#22d3ee");
    ctx.strokeStyle = grad; ctx.lineWidth = 2.5; ctx.lineJoin = "round"; ctx.stroke();
    values.forEach((v, i) => {
      const x = px(i), y = py(v) * ease + (h - pad) * (1 - ease);
      ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle = "#22d3ee"; ctx.fill();
    });
    ctx.fillStyle = "rgba(255,255,255,0.45)"; ctx.font = "600 9px Inter, sans-serif";
    ctx.textAlign = "center";
    const stepi = Math.max(1, Math.floor(values.length / 5));
    labels.forEach((lbl, i) => { if (i % stepi === 0) ctx.fillText(lbl, px(i), h - 3); });
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}

/* --------------------------------------------------------------- téléchargements */
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = h("a", { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

async function downloadApi(path, filename) {
  const res = await fetch(path, {
    headers: { Authorization: "Bearer " + state.token },
  });
  if (!res.ok) {
    let data = null;
    try { data = await res.json(); } catch (_) {}
    throw new Error((data && data.error) || "Téléchargement impossible.");
  }
  downloadBlob(await res.blob(), filename);
}

async function downloadBackup() {
  toast("Préparation de la sauvegarde…", "info");
  try {
    await downloadApi("/api/backup", `nexfleet_sauvegarde_${new Date().toISOString().slice(0, 10)}.db`);
    toast("Sauvegarde téléchargée.", "success");
  } catch (err) { toast(err.message, "error"); }
}

/* --------------------------------------------------------------- export Excel / CSV */
async function exportExcel() {
  toast("Génération de l'export Excel…", "info");
  try {
    await downloadApi("/api/export?format=xlsx", `nexfleet_parc_${new Date().toISOString().slice(0, 10)}.xlsx`);
    toast("Export Excel téléchargé.", "success");
  } catch (err) { toast(err.message, "error"); }
}

async function exportCSV() {
  toast("Génération de l'export CSV…", "info");
  try {
    await downloadApi("/api/export?format=csv&entity=vidanges", `vidanges_nexfleet_${new Date().toISOString().slice(0, 10)}.csv`);
    toast("Export CSV téléchargé.", "success");
  } catch (err) { toast(err.message, "error"); }
}

async function downloadTemplate() {
  toast("Téléchargement du modèle d'import…", "info");
  try {
    await downloadApi("/api/import/template", "modele_import_nexfleet.xlsx");
    toast("Modèle téléchargé.", "success");
  } catch (err) { toast(err.message, "error"); }
}

/* --------------------------------------------------------------- import de données */
const IMP_TYPE_META = {
  vehicles: { label: "Véhicules", color: "#6366f1", icon: "car" },
  drivers: { label: "Conducteurs", color: "#8b5cf6", icon: "users" },
  controls: { label: "Contrôles", color: "#34d399", icon: "check" },
  maintenance: { label: "Maintenance", color: "#f59e0b", icon: "wrench" },
  vidanges: { label: "Vidanges", color: "#38bdf8", icon: "wrench" },
  vignettes: { label: "Vignettes", color: "#fbbf24", icon: "file" },
  controles_tech: { label: "Contrôles techniques", color: "#34d399", icon: "check" },
  cartes_grise: { label: "Cartes grises", color: "#e879f9", icon: "file" },
  permis: { label: "Permis", color: "#22d3ee", icon: "user" },
  cni: { label: "Cartes d'identité", color: "#a3e635", icon: "user" },
};

function importModal() {
  let analysisData = null;
  let pendingFile = null;

  const box = openModal(`
    <div class="modal-head"><h4>Import intelligent</h4>
      <button class="modal-x" data-close>✕</button></div>
    <div style="padding:0 4px">
      <p style="color:var(--text-dim);font-size:13px;line-height:1.6;margin:0 0 14px">
        Glissez un fichier <b>.xlsx</b> ou <b>.csv</b> — le système détecte automatiquement les véhicules, conducteurs, maintenances, contrôles, vidanges et les documents d'échéance (vignettes, contrôles techniques, cartes grises, permis, cartes d'identité) avec leurs notes.
      </p>
      <div id="imp-drop" class="dropzone" style="margin-top:8px">
        <span class="dz-ico">📄</span>
        <p><b>Glissez votre fichier ici</b><br/><small>ou cliquez pour parcourir — .xlsx / .csv</small></p>
        <input id="imp-file" type="file" accept=".xlsx,.csv" style="display:none" />
      </div>
      <div id="imp-analyzing" style="display:none;text-align:center;padding:20px">
        <div class="assistant-typing"><span></span><span></span><span></span></div>
        <small style="color:var(--text-dim);margin-top:8px;display:block">Analyse en cours…</small>
      </div>
      <div id="imp-preview" style="display:none"></div>
      <div id="imp-result" class="import-result" hidden></div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:16px">
        <button type="button" class="mini-btn" id="imp-template" style="width:auto;padding:6px 12px;margin-right:auto">📥 Modèle</button>
        <button type="button" class="btn btn-ghost" data-close>Fermer</button>
        <button type="button" class="btn btn-primary" id="imp-import-btn" disabled>Importer <span class="btn-shine"></span></button>
      </div>
    </div>`, true);

  const input = box.querySelector("#imp-file");
  const drop = box.querySelector("#imp-drop");
  const analyzing = box.querySelector("#imp-analyzing");
  const preview = box.querySelector("#imp-preview");
  const result = box.querySelector("#imp-result");
  const importBtn = box.querySelector("#imp-import-btn");
  box.querySelector("#imp-template").addEventListener("click", downloadTemplate);

  drop.addEventListener("click", () => input.click());
  ["dragenter", "dragover"].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) handleFileSelect(e.dataTransfer.files[0]);
  });
  input.addEventListener("change", () => {
    if (input.files.length) handleFileSelect(input.files[0]);
  });

  async function handleFileSelect(file) {
    const name = file.name.toLowerCase();
    if (!name.endsWith(".xlsx") && !name.endsWith(".csv")) {
      toast("Format non supporté. Utilisez .xlsx ou .csv.", "error");
      return;
    }
    pendingFile = file;
    drop.querySelector("p").innerHTML = `<b>${esc(file.name)}</b><br/><small>${(file.size / 1024).toFixed(1)} Ko</small>`;
    drop.style.display = "none";
    analyzing.style.display = "";
    preview.style.display = "none";
    result.hidden = true;
    importBtn.disabled = true;

    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch("/api/import/analyze", {
        method: "POST",
        headers: { Authorization: "Bearer " + state.token },
        body: fd,
      });
      let data = null;
      try { data = await res.json(); } catch (_) {}
      if (!res.ok) throw new Error((data && data.error) || "Analyse échouée.");
      analysisData = data;
      renderPreview(data);
      importBtn.disabled = false;
    } catch (err) {
      toast(err.message, "error");
      drop.style.display = "";
      analyzing.style.display = "none";
    }
  }

  function renderPreview(data) {
    analyzing.style.display = "none";
    preview.style.display = "";
    preview.innerHTML = "";
    const sheets = data.sheets || [];

    const header = h("div", { style: "margin-bottom:12px" }, [
      h("div", { style: "display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px" },
        sheets.map((s) => {
          const meta = IMP_TYPE_META[s.detected_type] || { label: s.type_label, color: "#94a3b8" };
          return h("span", {
            style: `display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:600;background:${meta.color}22;color:${meta.color};border:1px solid ${meta.color}44`
          }, [
            h("span", { html: svg(meta.icon || "file"), style: "width:14px;height:14px" }),
            h("span", { text: `${meta.label} — ${s.total_rows} ligne${s.total_rows > 1 ? "s" : ""}` }),
          ]);
        })
      ),
      h("small", { text: sheets.map((s) => `${s.sheet} (${s.columns.length} colonnes)`).join(" · "), style: "color:var(--text-dim)" }),
    ]);
    preview.appendChild(header);

    sheets.forEach((s) => {
      const meta = IMP_TYPE_META[s.detected_type] || { label: s.type_label, color: "#94a3b8" };
      const card = h("div", { style: `background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:10px` });

      const mappedFields = Object.entries(s.mapped_fields || {});
      if (mappedFields.length) {
        card.appendChild(h("div", { style: "margin-bottom:8px" }, [
          h("small", { text: "Colonnes reconnues :", style: "font-weight:600;color:var(--text-dim);display:block;margin-bottom:4px" }),
          h("div", { style: "display:flex;flex-wrap:wrap;gap:4px" },
            mappedFields.map(([col, field]) =>
              h("span", { style: "padding:2px 7px;border-radius:4px;font-size:11px;background:#34d39922;color:#34d399;border:1px solid #34d39944", text: `${col} → ${field}` })
            )
          ),
        ]));
      }

      if (s.unmapped_columns && s.unmapped_columns.length) {
        card.appendChild(h("div", { style: "margin-bottom:8px" }, [
          h("small", { text: "Colonnes ignorées :", style: "font-weight:600;color:var(--text-dim);display:block;margin-bottom:4px" }),
          h("div", { style: "display:flex;flex-wrap:wrap;gap:4px" },
            s.unmapped_columns.map((col) =>
              h("span", { style: "padding:2px 7px;border-radius:4px;font-size:11px;background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b44", text: col })
            )
          ),
        ]));
      }

      if (s.sample_rows && s.sample_rows.length) {
        const table = h("table", { style: "width:100%;border-collapse:collapse;font-size:11px;margin-top:6px" });
        const thead = h("tr", {},
          s.columns.slice(0, 8).map((c) => h("th", { style: "text-align:left;padding:3px 6px;border-bottom:1px solid var(--border);color:var(--text-dim);font-weight:600", text: c }))
        );
        table.appendChild(thead);
        s.sample_rows.slice(0, 3).forEach((row) => {
          const tr = h("tr", {},
            s.columns.slice(0, 8).map((c) => h("td", { style: "padding:3px 6px;border-bottom:1px solid var(--border);color:var(--text-main);max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap", text: row[c] || "" }))
          );
          table.appendChild(tr);
        });
        card.appendChild(h("small", { text: "Aperçu :", style: "font-weight:600;color:var(--text-dim);display:block;margin-top:6px;margin-bottom:2px" }));
        card.appendChild(table);
      }

      preview.appendChild(card);
    });
  }

  importBtn.addEventListener("click", async () => {
    if (!pendingFile) { toast("Sélectionnez un fichier.", "warning"); return; }
    importBtn.disabled = true;
    importBtn.textContent = "Import en cours…";
    const fd = new FormData();
    fd.append("file", pendingFile);
    try {
      const res = await fetch("/api/import", {
        method: "POST",
        headers: { Authorization: "Bearer " + state.token },
        body: fd,
      });
      let data = null;
      try { data = await res.json(); } catch (_) {}
      if (!res.ok) throw new Error((data && data.error) || "Import échoué.");
      const d = (data && data.data) || data || {};
      const created = d.total_created || 0;
      const updated = d.total_updated || 0;
      const errors = d.total_errors || 0;
      result.hidden = false;
      result.innerHTML = "";
      result.appendChild(h("div", { class: "import-summary" }, [
        importKind("Créés", created, "success"),
        importKind("Mis à jour", updated, "info"),
        importKind("Erreurs", errors, "danger"),
      ]));
      const errs = d.summary ? Object.entries(d.summary).flatMap(([k, v]) => (v.errors || []).map((e) => `${k}: ${e}`)) : (d.errors || []);
      if (errs.length) {
        result.appendChild(h("div", { class: "import-errors" }, [
          ...errs.slice(0, 8).map((e) => h("small", { text: typeof e === "string" ? e : JSON.stringify(e) })),
        ]));
      }
      toast(`Import terminé : ${created} créé(s), ${updated} mis à jour.`, "success");
      if (state.view === "vehicles") loadVehicles();
      loadNotifications();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      importBtn.disabled = false;
      importBtn.textContent = "Importer";
    }
  });
}

function importKind(label, value, cls) {
  return h("div", { class: `import-kind ${cls}` }, [h("strong", { text: String(value) }), h("small", { text: label })]);
}

/* ------------------------------------------------------------------ boot */
function boot() {
  initUI();
  initAuthForms();
  renderRoute();
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();

/* ==========================================================================
   NexFleet — Source TypeScript de l'application.
   Compilation :  cd frontend/ts && tsc
   Le JS compilé (js/app.js) est fourni et fonctionne sans compilation.
   ========================================================================== */

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
}

interface Vehicle {
  id: number;
  immatriculation: string;
  marque: string;
  modele: string;
  annee: number | null;
  type: string;
  carburant: string;
  kilometrage: number;
  vignette_exp: string | null;
  assurance_exp: string | null;
  ctrl_tech_exp: string | null;
  statut: string;
  alerts?: AlertInfo[];
}

interface Driver {
  id: number;
  nom: string;
  prenom: string;
  email: string | null;
  telephone: string | null;
  permis: string | null;
  permis_exp: string | null;
}

interface Control {
  id: number;
  vehicle_id: number;
  driver_id: number | null;
  date: string;
  type: string;
  resultat: string;
  notes: string | null;
  items: string | Record<string, string> | null;
  immatriculation?: string;
  marque?: string;
  modele?: string;
  d_prenom?: string;
  d_nom?: string;
}

interface Maintenance {
  id: number;
  vehicle_id: number;
  type: string;
  date: string;
  cout: number;
  garage: string | null;
  notes: string | null;
  immatriculation?: string;
  marque?: string;
  modele?: string;
}

interface AlertInfo {
  type: string;
  label: string;
  days: number;
  level: string;
  msg: string;
  vehicle?: string;
  immatriculation?: string;
}

interface Stats {
  total: number;
  en_service: number;
  en_maintenance: number;
  en_panne: number;
  drivers: number;
  controls_month: number;
  controls_total: number;
  carburant: Record<string, number>;
  marques: Record<string, number>;
  controls_by_month: Array<{ month: string; count: number }>;
  alerts: AlertInfo[];
}

interface State {
  token: string;
  user: User | null;
  view: string;
  cache: Record<string, any>;
}

const state: State = {
  token: localStorage.getItem("nf_token") || "",
  user: JSON.parse(localStorage.getItem("nf_user") || "null"),
  view: "dashboard",
  cache: {},
};

const TITLES: Record<string, [string, string]> = {
  dashboard: ["Tableau de bord", "Vue d'ensemble de votre parc"],
  vehicles: ["Véhicules", "Gérez votre flotte et les échéances"],
  drivers: ["Conducteurs", "Permis, affectations et coordonnées"],
  controls: ["Contrôles", "Fiches de contrôle et conformité"],
  maintenance: ["Maintenance", "Interventions et historique"],
  reports: ["Rapports & PDF", "Documents professionnels exportables"],
  settings: ["Paramètres", "Compte, sécurité et données"],
};

const CARBURANTS: string[] = ["Diesel", "Essence", "Hybride", "Électrique", "GPL", "Bioéthanol"];
const TYPES_VEH: string[] = ["Utilitaire", "Camion", "Berline", "4x4", "Moto", "Remorque"];
const STATUTS: string[] = ["En service", "En maintenance", "En panne", "Hors service"];
const CHECKLIST: string[] = [
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
function $$(s: string, r?: ParentNode): HTMLElement[] {
  return [...(r || document).querySelectorAll<HTMLElement>(s)];
}

function h(tag: string, attrs?: any, children?: any[]): HTMLElement {
  const node = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs) as Array<[string, any]>) {
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

function esc(s: any): string {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c: string) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function skeleton(lines: number): HTMLElement {
  const items: HTMLElement[] = [];
  for (let i = 0; i < (lines || 4); i++) items.push(h("div", { class: "skeleton", style: `height:64px;margin-bottom:10px` }));
  return h("div", { class: "content" }, items);
}

function emptyRow(colspan: number, icon: string, text: string): HTMLElement {
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
function toast(msg: string, type: string = "success"): void {
  const root = document.getElementById("toast-root")!;
  const icons: Record<string, string> = { success: "✓", error: "✕", warning: "⚠", info: "ℹ" };
  const node = h("div", {
    class: `toast ${type}`,
    style: `--tcolor:${type === "error" ? "#f87171" : type === "warning" ? "#fbbf24" : "#34d399"}`,
  }, [
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
function openModal(html: string, wide?: boolean): HTMLElement {
  closeModal();
  const root = document.getElementById("modal-root")!;
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

function closeModal(): void {
  document.getElementById("modal-root")!.innerHTML = "";
}

function bindModal(root: HTMLElement): void {
  $$("[data-close]", root).forEach((b) => b.addEventListener("click", closeModal));
  $$("form[data-modal]", root).forEach((f) => f.addEventListener("submit", (e) => e.preventDefault()));
  $$("[data-set-date]", root).forEach((b) => {
    b.addEventListener("click", () => {
      const input = document.getElementById(b.dataset.setDate!) as HTMLInputElement;
      if (input) input.value = new Date().toISOString().slice(0, 10);
    });
  });
}

function confirmBox(title: string, msg: string, onYes: () => void): void {
  const box = openModal(`
    <div class="modal-head"><h4>${esc(title)}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <p style="color:var(--text-dim);margin-bottom:22px">${esc(msg)}</p>
    <div style="display:flex;gap:10px;justify-content:flex-end">
      <button class="btn btn-ghost" data-close>Annuler</button>
      <button class="btn btn-danger" id="confirm-yes">Confirmer</button>
    </div>`);
  box.querySelector("#confirm-yes")!.addEventListener("click", () => {
    closeModal();
    onYes();
  });
}

/* ------------------------------------------------------------------ API client */
async function api(path: string, method?: string, body?: any): Promise<any> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  const res = await fetch(path, {
    method: method || "GET",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data: any = null;
  try { data = await res.json(); } catch (_) { /* réponse vide */ }
  if (res.status === 401 && !path.startsWith("/api/auth/login") && !path.startsWith("/api/auth/register")) {
    logout();
    throw new Error("Session expirée.");
  }
  if (!res.ok) throw new Error((data && data.error) || "Erreur serveur.");
  return data;
}

async function downloadPdf(path: string, filename: string): Promise<void> {
  const res = await fetch(path, {
    headers: { Authorization: "Bearer " + state.token },
  });
  if (!res.ok) {
    let data: any = null;
    try { data = await res.json(); } catch (_) { }
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
function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function fmtKm(n: any): string {
  n = Number(n) || 0;
  return n.toLocaleString("fr-FR") + " km";
}

function fmtMoney(n: any): string {
  n = Number(n) || 0;
  return n.toLocaleString("fr-FR", { style: "currency", currency: "EUR" });
}

function daysLeft(iso: string | null): number | null {
  if (!iso) return null;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const d = new Date(iso + "T00:00:00");
  return Math.round((d.getTime() - today.getTime()) / 86400000);
}

function daysChip(iso: string | null): HTMLElement {
  const dl = daysLeft(iso);
  if (dl == null) return h("span", { class: "days-chip days-ok", text: "—" });
  if (dl < 0) return h("span", { class: "days-chip days-danger", text: `expiré -${Math.abs(dl)}j` });
  if (dl <= 15) return h("span", { class: "days-chip days-warn", text: `${dl} j` });
  return h("span", { class: "days-chip days-ok", text: `${dl} j` });
}

function badgeForStatut(s: string): HTMLElement {
  const t = (s || "").toLowerCase();
  let cls = "badge badge-service", label = s;
  if (t.includes("maintenance")) cls = "badge badge-maintenance";
  else if (t.includes("panne")) cls = "badge badge-panne";
  else if (t.includes("hors")) cls = "badge badge-muted";
  return h("span", { class: cls, text: label });
}

function badgeResultat(r: string): HTMLElement {
  const t = (r || "").toLowerCase();
  const cls = t.includes("non") || t.includes("refus") ? "badge badge-danger"
    : t.includes("surveill") ? "badge badge-warn" : "badge badge-ok";
  return h("span", { class: cls, text: r || "En cours" });
}

/* ------------------------------------------------------------------ graphiques */
interface CtxBox { ctx: CanvasRenderingContext2D; w: number; h: number; }

function prepCanvas(canvas: HTMLCanvasElement): CtxBox {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 260;
  const hgt = canvas.clientHeight || 200;
  canvas.width = w * dpr;
  canvas.height = hgt * dpr;
  const ctx = canvas.getContext("2d")!;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, hgt);
  return { ctx, w, h: hgt };
}

function drawDonut(canvas: HTMLCanvasElement, entries: number[], colors: string[]): void {
  const { ctx, w, h: hgt } = prepCanvas(canvas);
  const cx = w / 2, cy = hgt / 2, r = Math.min(w, hgt) / 2 - 6, lw = 20;
  const total = entries.reduce((a, b) => a + b, 0) || 1;
  const t0 = performance.now(), dur = 900;
  (function step(t: number) {
    const p = Math.min(1, (t - t0) / dur), ease = 1 - Math.pow(1 - p, 3);
    ctx.clearRect(0, 0, w, hgt);
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

function drawBars(canvas: HTMLCanvasElement, labels: string[], values: number[]): void {
  const { ctx, w, h: hgt } = prepCanvas(canvas);
  const t0 = performance.now(), dur = 850;
  const pad = 30;
  (function step(t: number) {
    const p = Math.min(1, (t - t0) / dur), ease = 1 - Math.pow(1 - p, 3);
    ctx.clearRect(0, 0, w, hgt);
    const max = Math.max(...values, 1);
    const bw = (w - pad * 1.6) / labels.length;
    values.forEach((v, i) => {
      const bh = ((hgt - 34) * v / max) * ease;
      const x = pad + i * bw + bw * 0.22;
      const y = hgt - 26 - bh;
      const grad = ctx.createLinearGradient(0, y, 0, hgt);
      grad.addColorStop(0, "#6366f1"); grad.addColorStop(1, "#22d3ee");
      ctx.fillStyle = grad;
      roundRect(ctx, x, y, bw * 0.56, bh, 7);
      ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,0.6)"; ctx.font = "600 10px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(String(v), x + bw * 0.28, y - 5);
      ctx.fillStyle = "rgba(255,255,255,0.4)"; ctx.font = "600 10px Inter, sans-serif";
      ctx.fillText(labels[i].slice(0, 4), x + bw * 0.28, hgt - 8);
    });
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}

function drawRing(canvas: HTMLCanvasElement, ratio: number, color: string): void {
  const { ctx, w, h: hgt } = prepCanvas(canvas);
  const cx = w / 2, cy = hgt / 2, r = Math.min(w, hgt) / 2 - 6, lw = 12;
  const t0 = performance.now(), dur = 900;
  (function step(t: number) {
    const p = Math.min(1, (t - t0) / dur), ease = 1 - Math.pow(1 - p, 3);
    ctx.clearRect(0, 0, w, hgt);
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(255,255,255,0.07)"; ctx.lineWidth = lw; ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * ratio * ease);
    ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = "round"; ctx.stroke();
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, hgt: number, r: number): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + hgt, r);
  ctx.arcTo(x + w, y + hgt, x, y + hgt, r);
  ctx.arcTo(x, y + hgt, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function animateCounter(node: HTMLElement, target: number, suffix?: string): void {
  const t0 = performance.now(), dur = 900;
  (function step(t: number) {
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    node.textContent = Math.round(target * e).toLocaleString("fr-FR") + (suffix || "");
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}

/* ------------------------------------------------------------------ auth */
function showLogin(): void {
  document.getElementById("app-screen")!.hidden = true;
  document.getElementById("login-screen")!.hidden = false;
}

function showApp(): void {
  document.getElementById("login-screen")!.hidden = true;
  document.getElementById("app-screen")!.hidden = false;
  applyUser();
}

function applyUser(): void {
  const u = state.user;
  if (!u) return;
  document.getElementById("sidebar-username")!.textContent = u.username;
  document.getElementById("sidebar-role")!.textContent = u.role === "admin" ? "Administrateur" : "Utilisateur";
  document.getElementById("sidebar-avatar")!.textContent = (u.username || "U")[0].toUpperCase();
}

function logout(): void {
  state.token = "";
  state.user = null;
  localStorage.removeItem("nf_token");
  localStorage.removeItem("nf_user");
  showLogin();
  location.hash = "#/login";
}

async function doLogin(e: Event): Promise<void> {
  e.preventDefault();
  const btn = document.getElementById("login-submit") as HTMLButtonElement;
  const ident = (document.getElementById("login-ident") as HTMLInputElement).value.trim();
  const pass = (document.getElementById("login-pass") as HTMLInputElement).value;
  btn.disabled = true; btn.querySelector(".btn-label")!.textContent = "Connexion…";
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
    toast((err as Error).message, "error");
    btn.disabled = false; btn.querySelector(".btn-label")!.textContent = "Entrer dans NexFleet";
  }
}

async function doRegister(e: Event): Promise<void> {
  e.preventDefault();
  const btn = document.getElementById("register-submit") as HTMLButtonElement;
  const body = {
    username: (document.getElementById("reg-name") as HTMLInputElement).value.trim(),
    email: (document.getElementById("reg-email") as HTMLInputElement).value.trim(),
    password: (document.getElementById("reg-pass") as HTMLInputElement).value,
  };
  btn.disabled = true; btn.querySelector(".btn-label")!.textContent = "Création…";
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
    toast((err as Error).message, "error");
    btn.disabled = false; btn.querySelector(".btn-label")!.textContent = "Créer mon compte";
  }
}

/* ------------------------------------------------------------------ routeur */
function currentRoute(): string {
  const m = location.hash.match(/^#\/(\w+)/);
  return m && TITLES[m[1]] ? m[1] : (state.token ? "dashboard" : "login");
}

function navigate(route: string): void {
  location.hash = "#/" + route;
}

function renderRoute(): void {
  const route = currentRoute();
  if (route === "login") { showLogin(); return; }
  if (!state.token) { location.hash = "#/login"; return; }
  state.view = route;
  showApp();
  const t = TITLES[route];
  document.getElementById("page-title")!.textContent = t[0];
  document.getElementById("page-sub")!.textContent = t[1];
  $$("#sidebar-nav .nav-item").forEach((n) =>
    n.classList.toggle("active", n.dataset.route === route));

  const content = document.getElementById("content")!;
  content.innerHTML = "";
  content.appendChild(skeleton(3));

  const views: Record<string, (c: HTMLElement) => Promise<void> | void> = {
    dashboard: viewDashboard,
    vehicles: viewVehicles,
    drivers: viewDrivers,
    controls: viewControls,
    maintenance: viewMaintenance,
    reports: viewReports,
    settings: viewSettings,
  };
  (views[route] || viewDashboard)(content);
}

/* ==========================================================================
   VUE : TABLEAU DE BORD
   ========================================================================== */
async function viewDashboard(root: HTMLElement): Promise<void> {
  const data: Stats = await api("/api/stats");
  const palette = ["#6366f1", "#22d3ee", "#a78bfa", "#f472b6", "#34d399", "#fbbf24"];

  const carbEntries = Object.entries(data.carburant || {});
  const carbVals = carbEntries.map((c) => c[1]);
  const kpis = [
    { icon: "🚗", label: "Véhicules au total", value: data.total, tint: "rgba(99,102,241,0.18)", glow: "rgba(99,102,241,0.4)", trend: null },
    { icon: "✅", label: "En service", value: data.en_service, tint: "rgba(52,211,153,0.16)", glow: "rgba(52,211,153,0.35)", trend: "disponibilité" },
    { icon: "🔧", label: "En maintenance", value: data.en_maintenance, tint: "rgba(251,191,36,0.16)", glow: "rgba(251,191,36,0.35)", trend: null },
    { icon: "⚠️", label: "En panne", value: data.en_panne, tint: "rgba(248,113,113,0.16)", glow: "rgba(248,113,113,0.35)", trend: data.en_panne > 0 ? "bad" : null },
    { icon: "🪪", label: "Conducteurs", value: data.drivers, tint: "rgba(34,211,238,0.16)", glow: "rgba(34,211,238,0.35)", trend: null },
    { icon: "📋", label: "Contrôles ce mois", value: data.controls_month, tint: "rgba(167,139,250,0.16)", glow: "rgba(167,139,250,0.35)", trend: null },
  ];

  const statsGrid = h("div", { class: "stats-grid" });
  kpis.forEach((k: any, i: number) => {
    const card = h("div", {
      class: "stat-card glass reveal reveal-" + (i % 5 + 1),
      style: `--tint:${k.tint};--glow:${k.glow}`,
    }, [
      h("div", { class: "stat-icon", text: k.icon }),
      h("div", { class: "stat-value", id: "kpi-" + i }),
      h("div", { class: "stat-label", text: k.label }),
      k.trend ? h("span", { class: "stat-trend" + (k.trend === "bad" ? " bad" : ""), text: k.trend === "bad" ? "▼ à traiter" : "▲ " + k.trend }) : null,
    ]);
    statsGrid.appendChild(card);
  });

  const serviceRatio = data.total ? data.en_service / data.total : 0;

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
  ]);

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
    h("div", { class: "panel-title", style: "margin-top:24px", html: "Alertes d'échéances" }),
    h("div", { class: "panel-sub", text: "Assurance · Vignette · Contrôle technique" }),
  ]);

  const alertList = h("div", { class: "alert-list" });
  if ((data.alerts || []).length === 0) {
    alertList.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-ico", text: "🎉" }),
      h("p", { text: "Aucune échéance critique. Parc en ordre !" }),
    ]));
  } else {
    data.alerts.forEach((a) => {
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

  const top3 = h("div", { class: "panel glass reveal reveal-4" }, [
    h("div", { class: "panel-title", html: "Flotte récente" }),
    h("div", { class: "panel-sub", text: "Derniers véhicules ajoutés" }),
  ]);
  try {
    const vres = await api("/api/vehicles");
    (vres.vehicles as Vehicle[] || []).slice(0, 5).forEach((v) => {
      top3.appendChild(h("div", { class: "v-mini" }, [
        h("div", { class: "avatar", text: v.immatriculation[0] }),
        h("div", { class: "v-mini-body" }, [
          h("strong", { text: `${v.marque} ${v.modele} · ${v.immatriculation}` }),
          h("small", { text: `${v.carburant} · ${fmtKm(v.kilometrage)}` }),
        ]),
        badgeForStatut(v.statut),
      ]));
    });
  } catch (_) { }

  root.innerHTML = "";
  root.append(statsGrid, h("div", { class: "dash-grid" }, [left, right]), top3);

  requestAnimationFrame(() => {
    kpis.forEach((k: any, i: number) => {
      const node = document.getElementById("kpi-" + i);
      if (node) animateCounter(node, k.value);
    });
    drawBars(document.getElementById("chart-bars") as HTMLCanvasElement,
      data.controls_by_month.map((m) => m.month), data.controls_by_month.map((m) => m.count));
    drawDonut(document.getElementById("chart-donut") as HTMLCanvasElement, carbVals, palette);
    drawRing(document.getElementById("chart-ring") as HTMLCanvasElement, serviceRatio, "#34d399");
    const rv = document.getElementById("ring-value");
    if (rv) animateCounter(rv, Math.round(serviceRatio * 100), "%");
  });

  updateAlertBadge(data.alerts ? data.alerts.filter((a) => a.level === "danger").length : 0);
}

function updateAlertBadge(n: number): void {
  const b = document.getElementById("badge-alerts")!;
  b.hidden = n === 0;
  b.textContent = String(n);
}

/* ==========================================================================
   VUE : VÉHICULES
   ========================================================================== */
async function viewVehicles(root: HTMLElement): Promise<void> {
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
    h("div", { class: "spacer" }),
    h("button", { class: "btn btn-primary btn-sm", onclick: () => vehicleModal(null), html: "＋ <span class='btn-shine'></span> Ajouter" }),
  ]);

  const tableCard = h("div", { class: "table-card glass reveal reveal-1" }, [
    h("div", { class: "table-scroll" }, [h("table", { class: "data", id: "veh-table" })]),
  ]);

  root.innerHTML = "";
  root.append(toolbar, tableCard);
  loadVehicles();
}

async function loadVehicles(): Promise<void> {
  const table = document.getElementById("veh-table") as HTMLTableElement;
  const search = (document.getElementById("veh-search") as HTMLInputElement || {}).value || "";
  const statut = (document.getElementById("veh-statut") as HTMLSelectElement || {}).value || "";
  const carburant = (document.getElementById("veh-carburant") as HTMLSelectElement || {}).value || "";
  const qs = new URLSearchParams();
  if (search) qs.set("search", search);
  if (statut) qs.set("statut", statut);
  if (carburant) qs.set("carburant", carburant);
  const res = await api("/api/vehicles?" + qs.toString());
  const vehs: Vehicle[] = res.vehicles || [];

  const isAdmin = (state.user || {}).role === "admin";
  table.innerHTML = "";
  table.appendChild(h("thead", null, [h("tr", null, [
    h("th", { text: "Immatriculation" }), h("th", { text: "Véhicule" }),
    h("th", { text: "Année" }), h("th", { text: "Carburant" }),
    h("th", { text: "Kilométrage" }), h("th", { text: "Statut" }),
    h("th", { text: "Assurance" }), h("th", { text: "CT" }),
    h("th", { text: "", style: "text-align:right" }),
  ])]));

  if (!vehs.length) {
    table.appendChild(emptyRow(9, "🚗", search ? "Aucun résultat pour cette recherche." : "Aucun véhicule. Ajoutez votre premier véhicule !"));
    return;
  }

  const tbody = h("tbody", null, []);
  vehs.forEach((v) => {
    tbody.appendChild(h("tr", null, [
      h("td", { class: "td-mono", text: v.immatriculation }),
      h("td", null, [h("div", { class: "td-strong", text: `${v.marque} ${v.modele}` }), h("small", { class: "td-dim", text: v.type })]),
      h("td", { class: "td-dim", text: v.annee || "—" }),
      h("td", { text: v.carburant }),
      h("td", { class: "td-dim", text: fmtKm(v.kilometrage) }),
      h("td", null, [badgeForStatut(v.statut)]),
      h("td", null, [daysChip(v.assurance_exp)]),
      h("td", null, [daysChip(v.ctrl_tech_exp)]),
      h("td", null, [h("div", { class: "row-actions" }, [
        h("button", { class: "mini-btn success", title: "Fiche de contrôle PDF", onclick: () => getVehiclePdf(v), text: "📄" }),
        h("button", { class: "mini-btn", title: "Modifier", onclick: () => vehicleModal(v), text: "✎" }),
        isAdmin ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer le véhicule", `Supprimer ${v.marque} ${v.modele} (${v.immatriculation}) ? Cette action est irréversible.`, () => delVehicle(v)), text: "🗑" }) : null,
      ])]),
    ]));
  });
  table.appendChild(tbody);
}

async function getVehiclePdf(v: Vehicle): Promise<void> {
  toast("Génération de la fiche PDF…", "info");
  try {
    await downloadPdf(`/api/vehicles/${v.id}/pdf`, `Fiche_controle_${v.immatriculation}.pdf`);
    toast("Fiche PDF téléchargée.", "success");
  } catch (err) {
    toast((err as Error).message, "error");
  }
}

async function delVehicle(v: Vehicle): Promise<void> {
  try {
    await api(`/api/vehicles/${v.id}`, "DELETE");
    toast("Véhicule supprimé.", "success");
    loadVehicles();
  } catch (err) {
    toast((err as Error).message, "error");
  }
}

function vehicleModal(v: Vehicle | null): void {
  const editing = !!v;
  const val = (f: string) => v ? esc((v as any)[f] || "") : "";
  openModal(`
    <div class="modal-head"><h4>${editing ? "Modifier le véhicule" : "Nouveau véhicule"}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="vehicle">
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
        <div class="field"><label>Échéance vignette <button type="button" class="mini-btn" data-set-date="v-vig" style="width:22px;height:22px;font-size:10px">auj.</button></label>
          <div class="input-wrap"><input id="v-vig" type="date" value="${val("vignette_exp")}" /></div></div>
        <div class="field"><label>Échéance assurance <button type="button" class="mini-btn" data-set-date="v-ass" style="width:22px;height:22px;font-size:10px">auj.</button></label>
          <div class="input-wrap"><input id="v-ass" type="date" value="${val("assurance_exp")}" /></div></div>
        <div class="field full"><label>Échéance contrôle technique <button type="button" class="mini-btn" data-set-date="v-ct" style="width:22px;height:22px;font-size:10px">auj.</button></label>
          <div class="input-wrap"><input id="v-ct" type="date" value="${val("ctrl_tech_exp")}" /></div></div>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button type="button" class="btn btn-ghost" data-close>Annuler</button>
        <button type="submit" class="btn btn-primary" id="veh-save">${editing ? "Enregistrer" : "Ajouter"} <span class="btn-shine"></span></button>
      </div>
    </form>`, false);

  document.getElementById("veh-save")!.addEventListener("click", async () => {
    const body = {
      immatriculation: (document.getElementById("v-imm") as HTMLInputElement).value,
      marque: (document.getElementById("v-marque") as HTMLInputElement).value,
      modele: (document.getElementById("v-modele") as HTMLInputElement).value,
      annee: (document.getElementById("v-annee") as HTMLInputElement).value || null,
      kilometrage: (document.getElementById("v-km") as HTMLInputElement).value || 0,
      type: (document.getElementById("v-type") as HTMLSelectElement).value,
      carburant: (document.getElementById("v-carburant") as HTMLSelectElement).value,
      statut: (document.getElementById("v-statut") as HTMLSelectElement).value,
      vignette_exp: (document.getElementById("v-vig") as HTMLInputElement).value || null,
      assurance_exp: (document.getElementById("v-ass") as HTMLInputElement).value || null,
      ctrl_tech_exp: (document.getElementById("v-ct") as HTMLInputElement).value || null,
    };
    try {
      if (editing) await api(`/api/vehicles/${(v as Vehicle).id}`, "PUT", body);
      else await api("/api/vehicles", "POST", body);
      closeModal();
      toast(editing ? "Véhicule mis à jour." : "Véhicule ajouté !", "success");
      loadVehicles();
    } catch (err) {
      toast((err as Error).message, "error");
    }
  });
}

/* ==========================================================================
   VUE : CONDUCTEURS
   ========================================================================== */
async function viewDrivers(root: HTMLElement): Promise<void> {
  root.innerHTML = "";
  root.appendChild(h("div", { class: "toolbar" }, [
    h("div", { class: "spacer" }),
    h("button", { class: "btn btn-primary btn-sm", onclick: () => driverModal(null), html: "＋ <span class='btn-shine'></span> Ajouter" }),
  ]));
  const card = h("div", { class: "table-card glass reveal reveal-1" }, [
    h("div", { class: "table-scroll" }, [h("table", { class: "data", id: "drv-table" })]),
  ]);
  root.appendChild(card);
  loadDrivers();
}

async function loadDrivers(): Promise<void> {
  const table = document.getElementById("drv-table") as HTMLTableElement;
  const res = await api("/api/drivers");
  const drv: Driver[] = res.drivers || [];
  const isAdmin = (state.user || {}).role === "admin";
  table.innerHTML = "";
  table.appendChild(h("thead", null, [h("tr", null, [
    h("th", { text: "Conducteur" }), h("th", { text: "Email" }), h("th", { text: "Téléphone" }),
    h("th", { text: "Permis" }), h("th", { text: "Validité permis" }), h("th", { text: "", style: "text-align:right" }),
  ])]));
  if (!drv.length) {
    table.appendChild(emptyRow(6, "🪪", "Aucun conducteur enregistré."));
    return;
  }
  const tbody = h("tbody", null, []);
  drv.forEach((d) => {
    tbody.appendChild(h("tr", null, [
      h("td", null, [h("div", { class: "td-strong", text: `${d.prenom} ${d.nom}` }), h("small", { class: "td-dim", text: "#" + d.id })]),
      h("td", { class: "td-dim", text: d.email || "—" }),
      h("td", { class: "td-dim", text: d.telephone || "—" }),
      h("td", { class: "td-mono", text: d.permis || "—" }),
      h("td", null, [daysChip(d.permis_exp)]),
      h("td", null, [h("div", { class: "row-actions" }, [
        h("button", { class: "mini-btn", title: "Modifier", onclick: () => driverModal(d), text: "✎" }),
        isAdmin ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer le conducteur", `Supprimer ${d.prenom} ${d.nom} ?`, () => delDriver(d)), text: "🗑" }) : null,
      ])]),
    ]));
  });
  table.appendChild(tbody);
}

async function delDriver(d: Driver): Promise<void> {
  try {
    await api(`/api/drivers/${d.id}`, "DELETE");
    toast("Conducteur supprimé.", "success");
    loadDrivers();
  } catch (err) {
    toast((err as Error).message, "error");
  }
}

function driverModal(d: Driver | null): void {
  const editing = !!d;
  const val = (f: string) => d ? esc((d as any)[f] || "") : "";
  openModal(`
    <div class="modal-head"><h4>${editing ? "Modifier le conducteur" : "Nouveau conducteur"}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="driver">
      <div class="form-grid">
        <div class="field"><label>Prénom *</label>
          <div class="input-wrap"><input id="d-prenom" type="text" value="${val("prenom")}" required /></div></div>
        <div class="field"><label>Nom *</label>
          <div class="input-wrap"><input id="d-nom" type="text" value="${val("nom")}" required /></div></div>
        <div class="field"><label>Email</label>
          <div class="input-wrap"><input id="d-email" type="email" value="${val("email")}" /></div></div>
        <div class="field"><label>Téléphone</label>
          <div class="input-wrap"><input id="d-tel" type="tel" value="${val("telephone")}" placeholder="06 12 34 56 78" /></div></div>
        <div class="field"><label>N° permis</label>
          <div class="input-wrap"><input id="d-permis" type="text" value="${val("permis")}" /></div></div>
        <div class="field"><label>Validité du permis <button type="button" class="mini-btn" data-set-date="d-permis-exp" style="width:22px;height:22px;font-size:10px">auj.</button></label>
          <div class="input-wrap"><input id="d-permis-exp" type="date" value="${val("permis_exp")}" /></div></div>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button type="button" class="btn btn-ghost" data-close>Annuler</button>
        <button type="submit" class="btn btn-primary" id="drv-save">${editing ? "Enregistrer" : "Ajouter"} <span class="btn-shine"></span></button>
      </div>
    </form>`);

  document.getElementById("drv-save")!.addEventListener("click", async () => {
    const body = {
      prenom: (document.getElementById("d-prenom") as HTMLInputElement).value,
      nom: (document.getElementById("d-nom") as HTMLInputElement).value,
      email: (document.getElementById("d-email") as HTMLInputElement).value,
      telephone: (document.getElementById("d-tel") as HTMLInputElement).value,
      permis: (document.getElementById("d-permis") as HTMLInputElement).value,
      permis_exp: (document.getElementById("d-permis-exp") as HTMLInputElement).value || null,
    };
    try {
      if (editing) await api(`/api/drivers/${(d as Driver).id}`, "PUT", body);
      else await api("/api/drivers", "POST", body);
      closeModal();
      toast(editing ? "Conducteur mis à jour." : "Conducteur ajouté !", "success");
      loadDrivers();
    } catch (err) {
      toast((err as Error).message, "error");
    }
  });
}

/* ==========================================================================
   VUE : CONTRÔLES
   ========================================================================== */
async function viewControls(root: HTMLElement): Promise<void> {
  const res = await Promise.all([api("/api/controls"), api("/api/vehicles"), api("/api/drivers")]);
  const controls: Control[] = res[0].controls || [];
  const vehicles: Vehicle[] = res[1].vehicles || [];
  const drivers: Driver[] = res[2].drivers || [];
  state.cache.controls = { vehicles, drivers };

  const isAdmin = (state.user || {}).role === "admin";
  const card = h("div", { class: "table-card glass reveal reveal-1" }, [h("div", { class: "table-scroll" }, [h("table", { class: "data" })] )]);
  const tbl = card.querySelector("table")!;
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
      h("button", { class: "btn btn-primary btn-sm", onclick: () => controlModal(null, vehicles, drivers), html: "＋ <span class='btn-shine'></span> Nouveau contrôle" }),
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
        h("button", { class: "mini-btn", title: "Modifier", onclick: () => controlModal(c, vehicles, drivers), text: "✎" }),
        isAdmin ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer le contrôle", "Supprimer ce contrôle ?", () => delControl(c)), text: "🗑" }) : null,
      ])]),
    ]));
  });
  tbl.appendChild(tbody);
}

async function delControl(c: Control): Promise<void> {
  try {
    await api(`/api/controls/${c.id}`, "DELETE");
    toast("Contrôle supprimé.", "success");
    navigate("controls");
  } catch (err) {
    toast((err as Error).message, "error");
  }
}

function safeParse(s: string): any {
  try { return JSON.parse(s); } catch (_) { return {}; }
}

function controlModal(c: Control | null, vehicles: Vehicle[], drivers: Driver[]): void {
  const editing = !!c;
  let items: Record<string, string> = c ? (typeof c.items === "string" ? safeParse(c.items) : c.items || {}) : {};
  const val = (f: string, dft: string) => c ? esc((c as any)[f] || dft) : dft;

  openModal(`
    <div class="modal-head"><h4>${editing ? "Modifier le contrôle" : "Nouveau contrôle"}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="control">
      <div class="form-grid">
        <div class="field"><label>Véhicule *</label>
          <select class="select" id="c-veh" style="width:100%">
            ${vehicles.map((v) => `<option value="${v.id}" ${c && c.vehicle_id === v.id ? "selected" : ""}>${v.marque} ${v.modele} · ${v.immatriculation}</option>`).join("")}
          </select></div>
        <div class="field"><label>Conducteur</label>
          <select class="select" id="c-drv" style="width:100%">
            <option value="">— Non affecté —</option>
            ${drivers.map((d) => `<option value="${d.id}" ${c && c.driver_id === d.id ? "selected" : ""}>${d.prenom} ${d.nom}</option>`).join("")}
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
        <button type="submit" class="btn btn-primary" id="ctl-save">${editing ? "Enregistrer" : "Créer"} <span class="btn-shine"></span></button>
      </div>
    </form>`, true);

  $$("#check-group .check-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      if ((e.target as HTMLElement).tagName === "INPUT") return;
      e.preventDefault();
      const cur = item.classList.contains("no") ? "bad" : item.classList.contains("watch") ? "warn" : "ok";
      const cycle: Record<string, string> = { ok: "watch", watch: "no", no: "ok" };
      const next = cycle[cur];
      item.classList.remove("ok", "watch", "no");
      if (next === "watch") item.classList.add("watch");
      if (next === "no") item.classList.add("no");
      if (next === "ok") item.classList.add("ok");
      const cb = item.querySelector("input") as HTMLInputElement;
      if (cb) cb.checked = next === "no";
    });
  });

  document.getElementById("ctl-save")!.addEventListener("click", async () => {
    const itemsObj: Record<string, string> = {};
    $$("#check-group .check-item").forEach((item) => {
      const name = item.dataset.name!;
      itemsObj[name] = item.classList.contains("no") ? "Non conforme"
        : item.classList.contains("watch") ? "À surveiller" : "Conforme";
    });
    const body = {
      vehicle_id: Number((document.getElementById("c-veh") as HTMLSelectElement).value),
      driver_id: (document.getElementById("c-drv") as HTMLSelectElement).value ? Number((document.getElementById("c-drv") as HTMLSelectElement).value) : null,
      date: (document.getElementById("c-date") as HTMLInputElement).value,
      type: (document.getElementById("c-type") as HTMLSelectElement).value,
      resultat: (document.getElementById("c-result") as HTMLSelectElement).value,
      notes: (document.getElementById("c-notes") as HTMLTextAreaElement).value,
      items: itemsObj,
    };
    try {
      if (editing) await api(`/api/controls/${(c as Control).id}`, "PUT", body);
      else await api("/api/controls", "POST", body);
      closeModal();
      toast("Contrôle enregistré.", "success");
      navigate("controls");
    } catch (err) {
      toast((err as Error).message, "error");
    }
  });
}

/* ==========================================================================
   VUE : MAINTENANCE
   ========================================================================== */
async function viewMaintenance(root: HTMLElement): Promise<void> {
  const res = await Promise.all([api("/api/maintenance"), api("/api/vehicles")]);
  const items: Maintenance[] = res[0].maintenance || [];
  const vehicles: Vehicle[] = res[1].vehicles || [];
  const isAdmin = (state.user || {}).role === "admin";
  let totalCost = 0;
  items.forEach((m) => (totalCost += Number(m.cout) || 0));

  const card = h("div", { class: "table-card glass reveal reveal-1" }, [h("div", { class: "table-scroll" }, [h("table", { class: "data" })] )]);
  const tbl = card.querySelector("table")!;
  tbl.appendChild(h("thead", null, [h("tr", null, [
    h("th", { text: "Date" }), h("th", { text: "Véhicule" }), h("th", { text: "Intervention" }),
    h("th", { text: "Coût" }), h("th", { text: "Garage" }), h("th", { text: "", style: "text-align:right" }),
  ])]));

  root.innerHTML = "";
  root.append(
    h("div", { class: "toolbar" }, [
      h("div", { class: "panel-sub", style: "margin:0", text: `${items.length} intervention(s) · coût total ${fmtMoney(totalCost)}` }),
      h("div", { class: "spacer" }),
      h("button", { class: "btn btn-primary btn-sm", onclick: () => maintenanceModal(null, vehicles), html: "＋ <span class='btn-shine'></span> Intervention" }),
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
        h("button", { class: "mini-btn", title: "Modifier", onclick: () => maintenanceModal(m, vehicles), text: "✎" }),
        isAdmin ? h("button", { class: "mini-btn danger", title: "Supprimer", onclick: () => confirmBox("Supprimer l'intervention", "Supprimer cette intervention ?", () => delMaintenance(m)), text: "🗑" }) : null,
      ])]),
    ]));
  });
  tbl.appendChild(tbody);
}

async function delMaintenance(m: Maintenance): Promise<void> {
  try {
    await api(`/api/maintenance/${m.id}`, "DELETE");
    toast("Intervention supprimée.", "success");
    navigate("maintenance");
  } catch (err) {
    toast((err as Error).message, "error");
  }
}

function maintenanceModal(m: Maintenance | null, vehicles: Vehicle[]): void {
  const editing = !!m;
  const val = (f: string, dft?: any) => m ? esc((m as any)[f] || dft) : dft;
  openModal(`
    <div class="modal-head"><h4>${editing ? "Modifier l'intervention" : "Nouvelle intervention"}</h4>
      <button class="modal-x" data-close>✕</button></div>
    <form data-modal="maintenance">
      <div class="form-grid">
        <div class="field full"><label>Véhicule *</label>
          <select class="select" id="m-veh" style="width:100%">
            ${vehicles.map((v) => `<option value="${v.id}" ${m && m.vehicle_id === v.id ? "selected" : ""}>${v.marque} ${v.modele} · ${v.immatriculation}</option>`).join("")}
          </select></div>
        <div class="field"><label>Type d'intervention</label>
          <select class="select" id="m-type" style="width:100%">
            ${["Révision", "Vidange", "Freins", "Pneus", "Électronique", "Carrosserie", "Climatisation", "Autre"].map((t) => `<option ${m && m.type === t ? "selected" : ""}>${t}</option>`).join("")}
          </select></div>
        <div class="field"><label>Date</label>
          <div class="input-wrap"><input id="m-date" type="date" value="${val("date", new Date().toISOString().slice(0, 10))}" /></div></div>
        <div class="field"><label>Coût (XFA)</label>
          <div class="input-wrap"><input id="m-cout" type="number" min="0" step="0.01" value="${val("cout", 0)}" /></div></div>
        <div class="field"><label>Garage</label>
          <div class="input-wrap"><input id="m-garage" type="text" value="${val("garage")}" placeholder="Garage NexAUTO" /></div></div>
        <div class="field full"><label>Notes</label>
          <div class="input-wrap"><textarea id="m-notes" rows="2" style="width:100%;resize:vertical;background:rgba(255,255,255,0.04);border:1px solid var(--border-strong);border-radius:12px;padding:12px;color:var(--text);font-family:var(--font);outline:none">${val("notes", "")}</textarea></div></div>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button type="button" class="btn btn-ghost" data-close>Annuler</button>
        <button type="submit" class="btn btn-primary" id="mnt-save">${editing ? "Enregistrer" : "Ajouter"} <span class="btn-shine"></span></button>
      </div>
    </form>`);

  document.getElementById("mnt-save")!.addEventListener("click", async () => {
    const body = {
      vehicle_id: Number((document.getElementById("m-veh") as HTMLSelectElement).value),
      type: (document.getElementById("m-type") as HTMLSelectElement).value,
      date: (document.getElementById("m-date") as HTMLInputElement).value,
      cout: Number((document.getElementById("m-cout") as HTMLInputElement).value) || 0,
      garage: (document.getElementById("m-garage") as HTMLInputElement).value,
      notes: (document.getElementById("m-notes") as HTMLTextAreaElement).value,
    };
    try {
      if (editing) await api(`/api/maintenance/${(m as Maintenance).id}`, "PUT", body);
      else await api("/api/maintenance", "POST", body);
      closeModal();
      toast("Intervention enregistrée.", "success");
      navigate("maintenance");
    } catch (err) {
      toast((err as Error).message, "error");
    }
  });
}

/* ==========================================================================
   VUE : RAPPORTS & PDF
   ========================================================================== */
async function viewReports(root: HTMLElement): Promise<void> {
  const res = await Promise.all([api("/api/stats"), api("/api/vehicles")]);
  const stats: Stats = res[0];
  const vehicles: Vehicle[] = res[1].vehicles || [];

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
      h("button", { class: "btn btn-primary btn-sm", onclick: () => parcPdf(), html: "📄 Télécharger" }),
    ]),
    h("div", { class: "panel glass reveal reveal-2" }, [
      h("div", { class: "panel-title", html: "Fiches de contrôle individuelles" }),
      h("div", { class: "panel-sub", text: "Sélectionnez un véhicule pour générer sa dernière fiche de contrôle." }),
      h("div", { class: "toolbar", style: "margin-top:14px" }, [
        h("select", { class: "select", id: "pdf-vehicle", style: "flex:1;min-width:220px" }, [
          ...vehicles.map((v) => h("option", { value: v.id, text: `${v.marque} ${v.modele} · ${v.immatriculation}` })),
        ]),
        h("button", { class: "btn btn-success btn-sm", onclick: () => singlePdf(vehicles), html: "📄 Générer la fiche" }),
      ]),
    ]),
    h("div", { class: "panel glass reveal reveal-3" }, [
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

function statMini(value: number, label: string, icon: string): HTMLElement {
  return h("div", { class: "stat-card glass" }, [
    h("div", { class: "stat-icon", text: icon }),
    h("div", { class: "stat-value", text: String(value) }),
    h("div", { class: "stat-label", text: label }),
  ]);
}

async function parcPdf(): Promise<void> {
  toast("Génération du rapport PDF…", "info");
  try {
    await downloadPdf("/api/parc/pdf", "Rapport_du_parc_automobile.pdf");
    toast("Rapport PDF téléchargé.", "success");
  } catch (err) {
    toast((err as Error).message, "error");
  }
}

async function singlePdf(vehicles: Vehicle[]): Promise<void> {
  const sel = document.getElementById("pdf-vehicle") as HTMLSelectElement;
  const id = Number(sel.value);
  const v = vehicles.find((x) => x.id === id);
  if (!v) { toast("Véhicule introuvable.", "error"); return; }
  toast(`Génération de la fiche de ${v.immatriculation}…`, "info");
  try {
    await downloadPdf(`/api/vehicles/${id}/pdf`, `Fiche_controle_${v.immatriculation}.pdf`);
    toast("Fiche PDF téléchargée.", "success");
  } catch (err) {
    toast((err as Error).message, "error");
  }
}

/* ==========================================================================
   VUE : PARAMÈTRES
   ========================================================================== */
async function viewSettings(root: HTMLElement): Promise<void> {
  const u = state.user;
  const isAdmin = (u || {}).role === "admin";

  const sections = h("div", null, [
    h("div", { class: "page-head" }, [
      h("div", null, [h("h3", { text: "Paramètres" }), h("p", { text: "Votre compte et la sécurité de la plateforme." })]),
    ]),

    h("div", { class: "setting-card glass reveal reveal-1" }, [
      h("div", { class: "setting-ico", text: "👤" }),
      h("div", { class: "setting-body" }, [
        h("strong", { text: u ? u.username : "" }),
        h("small", { text: `${u ? u.email : ""} · ${isAdmin ? "Administrateur" : "Utilisateur"}` }),
      ]),
      h("span", { class: isAdmin ? "badge badge-info" : "badge badge-muted", text: isAdmin ? "Admin" : "User" }),
    ]),

    h("div", { class: "panel glass reveal reveal-2" }, [
      h("div", { class: "panel-title", html: "🔒 Changer mon mot de passe" }),
      h("div", { class: "panel-sub", text: "Haché en PBKDF2-SHA256, jamais stocké en clair." }),
      h("form", { id: "form-pwd" }, [
        h("div", { class: "form-grid" }, [
          h("div", { class: "field" }, [h("label", { text: "Ancien mot de passe" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "p-old", type: "password", required: true }), h("button", { class: "eye", type: "button", dataset: { eye: "p-old" }, text: "👁" }),
          ])]),
          h("div", { class: "field" }, [h("label", { text: "Nouveau mot de passe" }), h("div", { class: "input-wrap" }, [
            h("input", { id: "p-new", type: "password", required: true, minlength: 8 }), h("button", { class: "eye", type: "button", dataset: { eye: "p-new" }, text: "👁" }),
          ])]),
        ]),
        h("button", { type: "submit", class: "btn btn-primary btn-sm", html: "Mettre à jour" }),
      ]),
    ]),

    h("div", { class: "panel glass reveal reveal-3", style: "margin-top:18px" }, [
      h("div", { class: "panel-title", html: "🗄️ Données de démonstration" }),
      h("div", { class: "panel-sub", text: "Chargez un jeu de données réaliste (véhicules, conducteurs, contrôles, maintenance)." }),
      h("button", { class: "btn btn-ghost btn-sm", onclick: () => loadDemo(), html: "Charger les données de démo" }),
    ]),

    h("div", { class: "panel glass reveal reveal-4", style: "margin-top:18px" }, [
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
  ]);

  root.innerHTML = "";
  root.appendChild(sections);

  document.getElementById("form-pwd")!.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/api/auth/password", "PUT", {
        old_password: (document.getElementById("p-old") as HTMLInputElement).value,
        new_password: (document.getElementById("p-new") as HTMLInputElement).value,
      });
      toast("Mot de passe mis à jour.", "success");
      (document.getElementById("p-old") as HTMLInputElement).value = "";
      (document.getElementById("p-new") as HTMLInputElement).value = "";
    } catch (err) {
      toast((err as Error).message, "error");
    }
  });
}

async function loadDemo(): Promise<void> {
  try {
    await api("/api/demo", "POST");
    toast("Données de démonstration chargées !", "success");
    navigate("dashboard");
  } catch (err) {
    toast((err as Error).message, "error");
  }
}

/* ------------------------------------------------------------------ divers */
function debounce(fn: () => void, ms: number): () => void {
  let t: number;
  return function (...args: any[]) {
    clearTimeout(t);
    t = window.setTimeout(() => fn.apply(null, args), ms);
  };
}

function tickClock(): void {
  const now = new Date();
  const clock = document.getElementById("clock");
  const chip = document.getElementById("date-chip");
  if (clock) clock.textContent = now.toLocaleTimeString("fr-FR");
  if (chip) chip.textContent = now.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "long", year: "numeric" });
}

function initAuthForms(): void {
  $$(".auth-tab").forEach((tab) => tab.addEventListener("click", () => {
    $$(".auth-tab").forEach((t) => t.classList.toggle("active", t === tab));
    document.getElementById("form-login")!.hidden = tab.dataset.tab !== "login";
    document.getElementById("form-register")!.hidden = tab.dataset.tab !== "register";
  }));
  document.getElementById("form-login")!.addEventListener("submit", doLogin);
  document.getElementById("form-register")!.addEventListener("submit", doRegister);

  const strengthFill = document.getElementById("strength-fill") as HTMLElement;
  const strengthLabel = document.getElementById("strength-label") as HTMLElement;
  (document.getElementById("reg-pass") as HTMLInputElement).addEventListener("input", (e) => {
    const v = (e.target as HTMLInputElement).value;
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

function initUI(): void {
  const preloader = document.getElementById("preloader");
  setTimeout(() => preloader!.classList.add("done"), 1300);

  document.getElementById("btn-logout")!.addEventListener("click", logout);
  document.getElementById("btn-hamburger")!.addEventListener("click", () => {
    document.getElementById("sidebar")!.classList.toggle("open");
  });
  $$("#sidebar-nav .nav-item").forEach((n) =>
    n.addEventListener("click", () => {
      navigate(n.dataset.route!);
      document.getElementById("sidebar")!.classList.remove("open");
    }));

  window.addEventListener("hashchange", renderRoute);
  setInterval(tickClock, 1000);
  tickClock();

  document.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest(".eye") as HTMLElement | null;
    if (!btn) return;
    const inp = document.getElementById(btn.dataset.eye!) as HTMLInputElement;
    if (inp) inp.type = inp.type === "password" ? "text" : "password";
  });
}

/* ------------------------------------------------------------------ boot */
function boot(): void {
  initUI();
  initAuthForms();
  renderRoute();
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();

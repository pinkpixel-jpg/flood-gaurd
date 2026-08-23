/* FloodGuard — frontend API helper.
   Single place where the backend base URL lives. No credentials in this
   file: this API is public-facing; ViaSocket stays backend-only. */

const API_BASE = window.FG_API_BASE || "http://127.0.0.1:8000/api";

/* Shared dataset constants (single source of truth for the frontend). */
const FG_DATASET = {
  DATE_MIN: "2015-01-01",
  DATE_MAX: "2026-12-31",
  DEFAULT_DATE: "2024-07-15",
  FALLBACK_GRIDS: ["PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004"]
};

/* Zone ID -> human-readable place name (single source of truth). */
const ZONE_NAMES = {
  PUNE_G001: "West-Central Pune",
  PUNE_G002: "East Pune",
  PUNE_G003: "North-West Pune",
  PUNE_G004: "North-East Pune"
};

function zoneName(gid) {
  return ZONE_NAMES[gid] || gid;
}
function zoneShort(gid) {
  return (ZONE_NAMES[gid] || gid).replace(/\s*Pune\s*$/i, "");
}

let _gridCache = null;

async function loadGrids() {
  if (_gridCache) return _gridCache;
  try {
    const res = await fetch(API_BASE + "/zones?date=" + FG_DATASET.DEFAULT_DATE);
    const j = await res.json();
    const list = Array.isArray(j) ? j : j.zones;
    _gridCache = list.map(z => z.grid_id);
  } catch (e) {
    _gridCache = FG_DATASET.FALLBACK_GRIDS.slice();
  }
  return _gridCache;
}

async function apiGet(path, token, role) {
  const h = {};
  if (token) h["Authorization"] = "Bearer " + token;
  if (role) h["X-Role"] = role;
  const res = await fetch(API_BASE + path, {
    headers: h,
    signal: AbortSignal.timeout(10000)
  });
  if (!res.ok) throw new Error("HTTP " + res.status + " on " + path);
  return res.json();
}

async function apiPost(path, body, token) {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: Object.assign(
      { "Content-Type": "application/json" },
      token ? { "Authorization": "Bearer " + token } : {}),
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(15000)
  });
  if (!res.ok) {
    let detail = "HTTP " + res.status;
    try { detail = (await res.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  return res.json();
}

const FGApi = {
  getHealth: () => apiGet("/health"),
  getZones: (date) => apiGet("/zones" + (date ? "?date=" + date : "")),
  getZone: (gridId, date, citizenReports) =>
    apiGet("/zones/" + gridId +
      "?date=" + (date || "2024-07-15") +
      "&citizen_reports=" + (citizenReports || 0), null, "DISASTER"),
  getRisk: (gridId, date) => apiGet("/risk/" + gridId + "?date=" + (date || "2024-07-15")),
  getVulnerability: (gridId) => apiGet("/vulnerability/" + gridId),
  getPrevention: (gridId, date, citizenReports) =>
    apiGet("/prevention/" + gridId +
      "?date=" + (date || "2024-07-15") +
      "&citizen_reports=" + (citizenReports || 0)),
  getEnvironment: (gridId, date) =>
    apiGet("/environment/" + gridId + "?date=" + (date || "2024-07-15")),
  submitReport: (data) => apiPost("/reports", data),
  getReports: (gridId) => apiGet("/reports" + (gridId ? "?grid_id=" + gridId : "")),
  getHistoryEvents: () => apiGet("/history/events"),
  analyzeRisk: (payload) => apiPost("/risk/analyze", payload),
  getViaSocketEvent: (gridId, date) =>
    apiGet("/viasocket/event?grid_id=" + grid_id_fix(gridId) + "&date=" + (date || "2024-07-15")),

  /* ---- Phase 8: dual alert systems ---- */
  loginPublic: (username, password) =>
    apiPost("/auth/public/login", { username, password }),
  loginMunicipal: (username, password) =>
    apiPost("/auth/municipal/login", { username, password }),
  me: (token) => apiGet("/auth/me", token),
  getPublicAlerts: (date, gridId, token) =>
    apiGet("/alerts/public?date=" + (date || "2024-07-15") +
      (gridId ? "&grid_id=" + gridId : ""), token),
  getPublicHistory: (token, limit) =>
    apiGet("/alerts/public/history?limit=" + (limit || 20), token),
  setPublicPrefs: (gridId, minLevel, token) =>
    apiPost("/alerts/public/preferences",
            { grid_id: gridId, min_level: minLevel }, token),
  getMunicipalAlerts: (date, gridId, citizenReports, token) =>
    apiGet("/alerts/municipal?date=" + (date || "2024-07-15") +
      (gridId ? "&grid_id=" + gridId : "") +
      "&citizen_reports=" + (citizenReports || 0), token),
  getMunicipalHistory: (token, limit) =>
    apiGet("/alerts/municipal/history?limit=" + (limit || 20), token),
  setMunicipalPrefs: (gridId, minPriority, token) =>
    apiPost("/alerts/municipal/preferences",
            { grid_id: gridId, min_priority: minPriority }, token),
  generateAlerts: (date, channel) =>
    apiPost("/alerts/generate", { date: date, channel: channel || null })
};

function grid_id_fix(g) { return g; }

window.FGApi = FGApi;
window.FG_DATASET = FG_DATASET;
window.ZONE_NAMES = ZONE_NAMES;
window.zoneName = zoneName;
window.zoneShort = zoneShort;
window.loadGrids = loadGrids;

window.FGAuthStorage = {
  save(token, role, username) {
    localStorage.setItem("fg_token", token);
    localStorage.setItem("fg_role", role);
    localStorage.setItem("fg_user", username);
  },
  clear() {
    ["fg_token", "fg_role", "fg_user"].forEach(k => localStorage.removeItem(k));
  },
  get() {
    return { token: localStorage.getItem("fg_token"),
             role: localStorage.getItem("fg_role"),
             username: localStorage.getItem("fg_user") };
  }
};

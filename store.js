// Shared storage and login helpers for CampusSync and CampusSync Vision.
//
// Both pages are served by the same server (http://localhost:8000), so the browser gives
// them the SAME localStorage. Vision writes into these keys, the attendance app reads them.
// Nothing here is a new data model: each key holds the shape the app already used.
//
//   announcements : [ { msg, by, ...optional extras } ]          (data.js: announcements)
//   timetable     : { Monday: [ { time, subject, color } ] }     (data.js: timetable)
//   attendance    : { "2026-1-12-Hindi-07-08": "present" }       (app.js: attendance)
//                   one map PER COLLEGE ID: key "campussync.attendance.<ID>"
//   study         : [ { id, semester, subject, topic, date, ... } ]  (study.js)
//   chat          : { messages: [...], reads: {...} }            (chat.js)

const STORE_KEYS = {
  announcements: "campussync.announcements",
  timetable: "campussync.timetable",
  attendance: "campussync.attendance",
  timetableBackup: "campussync.timetable.backup",  // written by Vision so "Undo" can restore the old timetable
  study: "campussync.study",
  chat: "campussync.chat"
};

// Read a saved value. If nothing is saved (or localStorage is blocked) return the fallback.
// suffix (optional) makes a per-user key: loadStore("attendance", {}, "DEMO-CS-001") -> "campussync.attendance.DEMO-CS-001"
function loadStore(name, fallback, suffix) {
  try {
    const raw = localStorage.getItem(STORE_KEYS[name] + (suffix ? "." + suffix : ""));
    return raw === null ? fallback : JSON.parse(raw);
  } catch (e) {
    return fallback;
  }
}

// Save a value. Returns true if it was saved. Fails quietly (returns false) if localStorage is blocked or full.
function saveStore(name, value, suffix) {
  try {
    localStorage.setItem(STORE_KEYS[name] + (suffix ? "." + suffix : ""), JSON.stringify(value));
    return true;
  } catch (e) {
    console.warn("Could not save " + name, e);
    return false;
  }
}

// ---------------------------------------------------------------- login: college IDs
// DEMO accounts. These IDs are PLACEHOLDERS for the demo, not real people's college IDs.
// The role (student / cr / acr) belongs to the account. DEMO ONLY: these passwords sit in plain text in a file every
// visitor downloads, so they protect nothing. Do not reuse them anywhere, and do not treat the roles as security:
// a real deployment must check logins on a server. (The server's own protection for destructive calls is the
// CAMPUS_ADMIN_TOKEN environment variable, see vision/main.py; it is separate from these accounts.)
const DEMO_USERS = [
  { id: "DEMO-CS-001", name: "Zainab", role: "cr", password: "cr-demo" },
  { id: "DEMO-CS-002", name: "Aarav", role: "acr", password: "acr-demo" },
  { id: "DEMO-CS-003", name: "Meera", role: "student", password: "student-demo" },
  { id: "DEMO-CS-004", name: "Kabir", role: "student", password: "student-demo" }
];

const ID_PATTERN = /^[A-Z0-9][A-Z0-9-]{3,19}$/;       // 4-20 characters: capitals, digits, hyphens
const SESSION_KEY = "campussync.session";

function normalizeId(text) { return String(text || "").trim().toUpperCase(); }
function isValidId(id) { return ID_PATTERN.test(id); }

// The demo first name for a demo ID ("" for any other ID)
function demoName(id) {
  const u = DEMO_USERS.find(x => x.id === id);
  return u ? u.name : "";
}
// "Aarav (DEMO-CS-002)" for a demo ID, otherwise just the ID
function idLabel(id) { return demoName(id) ? `${demoName(id)} (${id})` : id; }

// Who is logged in. sessionStorage is per tab (so two tabs can be two people);
// localStorage keeps the last login so other pages (Vision) know whose data to use.
function getSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY)); } catch (e) { return null; }
}
function lastSession() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY)); } catch (e) { return null; }
}
function setSession(session) {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(session)); } catch (e) { /* private mode */ }
  try { localStorage.setItem(SESSION_KEY, JSON.stringify(session)); } catch (e) { /* private mode */ }
}
function clearSession() {
  try { sessionStorage.removeItem(SESSION_KEY); } catch (e) { /* ignore */ }
}

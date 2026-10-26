// Shared storage for CampusSync and CampusSync Vision.
//
// Both pages are served by the same server (http://localhost:8000), so the browser gives
// them the SAME localStorage. Vision writes into these keys, the attendance app reads them.
// Nothing here is a new data model: each key holds the shape the app already used.
//
//   announcements : [ { msg, by, ...optional extras } ]          (data.js: announcements)
//   timetable     : { Monday: [ { time, subject, color } ] }     (data.js: timetable)
//   attendance    : { "2026-1-12-Hindi-07-08": "present" }       (app.js: attendance)

const STORE_KEYS = {
  announcements: "campussync.announcements",
  timetable: "campussync.timetable",
  attendance: "campussync.attendance",
  timetableBackup: "campussync.timetable.backup",  // written by Vision so "Undo" can restore the old timetable
  chat: "campussync.chat"                          // chat.js: { messages: [...], reads: {...} }
};

// Read a saved value. If nothing is saved (or localStorage is blocked) return the fallback.
function loadStore(name, fallback) {
  try {
    const raw = localStorage.getItem(STORE_KEYS[name]);
    return raw === null ? fallback : JSON.parse(raw);
  } catch (e) {
    return fallback;
  }
}

// Save a value. Fails quietly if localStorage is blocked (the app still works, just without saving).
function saveStore(name, value) {
  try {
    localStorage.setItem(STORE_KEYS[name], JSON.stringify(value));
  } catch (e) {
    console.warn("Could not save " + name, e);
  }
}

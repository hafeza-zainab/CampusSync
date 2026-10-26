let user = {};
let attendance = {};   // loaded at login: each college ID has its own marks (key "attendance.<ID>")

// Load saved data (store.js). Vision writes to the same keys.
announcements = loadStore("announcements", []);

// timetable is a const in data.js, so we replace its CONTENTS instead of the variable.
// The data.js version is remembered so "Undo" in Vision can bring it back.
const defaultTimetable = JSON.parse(JSON.stringify(timetable));
function applySavedTimetable() {
  const source = loadStore("timetable", null) || defaultTimetable;
  Object.keys(timetable).forEach(day => delete timetable[day]);
  Object.assign(timetable, JSON.parse(JSON.stringify(source)));
}
applySavedTimetable();
let currentDate = new Date(new Date().getFullYear(), new Date().getMonth()); // the current month

// Per-subject numbers for the month on screen. renderCalendar() fills them; checkWarnings() and the stats read them.
// (They used to be declared inside renderCalendar, so checkWarnings could not see them: that was the broken 75% warning.)
let subjectCount = {};     // lectures already held this month (their end time has passed)
let subjectPresent = {};   // held lectures marked present
let subjectAbsent = {};    // held lectures marked absent
let subjectScheduled = {}; // all lectures in the timetable this month, held or not
let currentUser = null;
let currentRole = null;

function login() {
  const id = normalizeId(document.getElementById("username").value);   // college ID, e.g. DEMO-CS-001
  const role = document.getElementById("role").value;
  const error = document.getElementById("loginError");

  if (!isValidId(id)) {
    error.textContent = "Enter your college ID: 4 to 20 letters, digits or hyphens (for example DEMO-CS-001).";
    return;
  }
  error.textContent = "";

  currentUser = id;      // the college ID is the identity: attendance, announcements and chat all use it
  currentRole = role;
  setSession({ id, role });
  attendance = loadStore("attendance", {}, currentUser);

  document.getElementById("loginBox").style.display = "none";
  document.getElementById("dashboard").classList.remove("hidden");

  document.getElementById("welcome").innerText =
    `Welcome ${idLabel(currentUser)} (${currentRole.toUpperCase()})`;

  renderCalendar();
}

// Turns the end of a lecture time into [hour, minute].
// data.js writes times like "07-08" or "12-01" (no minutes), the old code expected "09:00".
// Accepts both. Hours below 7 are afternoon ("01" -> 13) because lectures don't start at 1am.
function parseEndTime(text) {
  const [h, m] = text.split(":").map(Number);
  const hour = h < 7 ? h + 12 : h;
  return [hour, m || 0];
}

/* UPDATED CALENDAR LOGIC */
function renderCalendar() {
  const grid = document.getElementById("calendarGrid");
  const title = document.getElementById("monthYear");
  const statsDiv = document.getElementById("stats");

  grid.innerHTML = "";
  statsDiv.innerHTML = "";

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const now = new Date(); // Real-time for comparison

  title.innerText = currentDate.toLocaleString("default", { month: "long", year: "numeric" });

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const offset = (firstDay + 6) % 7;

  for (let i = 0; i < offset; i++) {
    grid.appendChild(document.createElement("div"));
  }

  subjectCount = {};
  subjectPresent = {};
  subjectAbsent = {};
  subjectScheduled = {};

  for (let day = 1; day <= daysInMonth; day++) {
    const box = document.createElement("div");
    box.className = "day";
    box.innerHTML = `<strong>${day}</strong><br>`;

    const dateOfBox = new Date(year, month, day);
    const weekday = dateOfBox.toLocaleString("default", { weekday: "long" });

    if (timetable[weekday]) {
      timetable[weekday].forEach(lec => {
        if (lec.subject === "Break") return; // Skip breaks

        const key = `${year}-${month}-${day}-${lec.subject}-${lec.time}`;
        const status = attendance[key];

        // Parse Lecture End Time
        const endTimeStr = lec.time.split("-")[1]; // e.g., "09:00" or "08"
        const [endHour, endMin] = parseEndTime(endTimeStr);
        const lectureEndTime = new Date(year, month, day, endHour, endMin);

        const isOver = now > lectureEndTime;

        // Statistics Logic
        subjectScheduled[lec.subject] = (subjectScheduled[lec.subject] || 0) + 1;
        if (isOver) {
          subjectCount[lec.subject] = (subjectCount[lec.subject] || 0) + 1;
          if (status === "present") {
            subjectPresent[lec.subject] = (subjectPresent[lec.subject] || 0) + 1;
          }
          if (status === "absent") {
            subjectAbsent[lec.subject] = (subjectAbsent[lec.subject] || 0) + 1;
          }
        }

        // Create UI element
        const l = document.createElement("div");
        l.className = "lecture";
        l.style.background = isOver ? "#ccc" : (lec.color || "#4ea8de"); // Grey if over
        l.style.color = isOver ? "#666" : "white";
        l.style.cursor = isOver ? "pointer" : "not-allowed";

        if (status === "present") l.classList.add("present");
        if (status === "absent") l.classList.add("absent");

        l.innerText = `${lec.time} ${lec.subject}`;
        
        // Only allow marking if lecture is over (the menu says so when it is not)
        l.onclick = () => openAttendanceMenu(key, l, isOver, endTimeStr);

        box.appendChild(l);
      });
    }
    grid.appendChild(box);
  }

  renderStats(statsDiv);
  renderAttendanceTab();
  checkWarnings();
}

// One row of numbers per subject for the month on screen.
function monthRows() {
  return Object.keys(subjectScheduled).map(sub => {
    const held = subjectCount[sub] || 0;
    const present = subjectPresent[sub] || 0;
    const absent = subjectAbsent[sub] || 0;
    return { sub, scheduled: subjectScheduled[sub], held, present, absent,
             unmarked: held - present - absent,
             percent: held ? Math.round((present / held) * 100) : null };
  });
}

// small helper: <tag class="cls">text</tag> (text is added as text, never as HTML)
function h(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

// Side panel: per subject  attended / held (percent), lectures this month, absent, unmarked
function renderStats(statsDiv) {
  const rows = monthRows();
  if (!rows.length) statsDiv.append(h("p", "stat-empty", "No lectures in the timetable this month."));
  rows.forEach(r => {
    const low = r.percent !== null && r.percent < 75;
    const row = h("div", "stat-row" + (low ? " low" : ""));
    row.append(h("div", "stat-name", (low ? "⚠ " : "") + r.sub));
    row.append(h("div", "stat-main", r.held
      ? `${r.present} of ${r.held} held attended: ${r.percent}%`
      : "No lecture held yet"));
    row.append(h("div", "stat-sub", `${r.scheduled} this month · ${r.absent} absent · ${Math.max(r.unmarked, 0)} unmarked`));
    statsDiv.append(row);
  });
}

// The Attendance tab: the same numbers as a table, plus the overall figure
function renderAttendanceTab() {
  const list = document.getElementById("attendanceList");
  if (!list) return;
  list.replaceChildren();
  const rows = monthRows();
  const table = h("table", "attend-table");
  const head = h("tr");
  ["Subject", "This month", "Held", "Attended", "Absent", "Unmarked", "%"].forEach(t => head.append(h("th", "", t)));
  table.append(head);
  rows.forEach(r => {
    const tr = h("tr", r.percent !== null && r.percent < 75 ? "low" : "");
    [r.sub, r.scheduled, r.held, r.present, r.absent, Math.max(r.unmarked, 0), r.percent === null ? "–" : r.percent + "%"]
      .forEach(v => tr.append(h("td", "", String(v))));
    table.append(tr);
  });
  list.append(h("p", "attend-month", document.getElementById("monthYear").innerText));
  list.append(table);
  const held = rows.reduce((n, r) => n + r.held, 0), present = rows.reduce((n, r) => n + r.present, 0);
  document.getElementById("presentCount").textContent = held
    ? `Overall this month: ${present} of ${held} held lectures attended (${Math.round((present / held) * 100)}%)`
    : "No lectures held yet this month.";
}

/* STUDY MATERIAL: moved to study.js (the old uploadMaterial/renderMaterials here used undefined variables and a missing element) */

/* ANNOUNCEMENTS */
function postAnnouncement() {
  const text = msg.value.trim();
  if (!text) return;                       // ignore empty announcements
  announcements = loadStore("announcements", announcements);   // keep posts made from other tabs / Vision
  announcements.push({
    msg: text,
    by: currentUser,                       // the author is the college ID
    role: currentRole
  });
  saveStore("announcements", announcements);
  msg.value = "";
  renderAnnouncements();
}

function renderAnnouncements() {
  let div = document.getElementById("announceList");
  div.innerHTML = "";
  announcements.forEach(a => {
    // text is added with textContent, so text read from a screenshot can never inject HTML
    const p = document.createElement("p");
    p.textContent = `📢 ${a.msg} — ${a.by}` + (a.role ? ` (${String(a.role).toUpperCase()})` : "") + (a.via ? ` · via ${a.via}` : "");
    div.appendChild(p);
  });
}

// status: "present", "absent", or null to clear the mark. The stored shape is unchanged: attendance[key] = "present" | "absent".
function markAttendance(key, status) {
  if (status) attendance[key] = status;
  else delete attendance[key];
  saveStore("attendance", attendance, currentUser);
  closeAttendanceMenu();
  renderCalendar();
}

function closeAttendanceMenu() {
  const old = document.getElementById("attendMenu");
  if (old) old.remove();
  document.removeEventListener("keydown", attendanceMenuKey);
}
function attendanceMenuKey(e) { if (e.key === "Escape") closeAttendanceMenu(); }

// The little menu under a clicked lecture: Present / Absent / Clear (instead of the old prompt() popup)
function openAttendanceMenu(key, anchor, isOver, endTimeStr) {
  closeAttendanceMenu();
  const menu = h("div", "attend-menu");
  menu.id = "attendMenu";
  menu.setAttribute("role", "dialog");
  menu.setAttribute("aria-label", "Mark attendance");
  if (!isOver) {
    const [eh, em] = parseEndTime(endTimeStr);   // "08" -> 8:00, "01" -> 13:00
    menu.append(h("p", "", `This lecture hasn't finished yet. Attendance opens after ${eh}:${String(em).padStart(2, "0")}.`));
  } else {
    [["Present", "present"], ["Absent", "absent"], ["Clear", null]].forEach(([label, status]) => {
      const btn = h("button", "attend-" + (status || "clear"), label);
      btn.type = "button";
      btn.onclick = () => markAttendance(key, status);
      menu.append(btn);
    });
  }
  const close = h("button", "attend-close", "Close");
  close.type = "button";
  close.onclick = closeAttendanceMenu;
  menu.append(close);
  const r = anchor.getBoundingClientRect();
  menu.style.left = Math.round(r.left + window.scrollX) + "px";
  menu.style.top = Math.round(r.bottom + window.scrollY + 4) + "px";
  document.body.append(menu);
  menu.querySelector("button").focus();
  document.addEventListener("keydown", attendanceMenuKey);
}

// Fills the 75% warning (Attendance tab + top of the stats panel). No popup: it stays visible.
function checkWarnings() {
  const warnings = monthRows()
    .filter(r => r.percent !== null && r.percent < 75)
    .map(r => `${r.sub} below 75% (${r.percent}%)`);

  const tabWarning = document.getElementById("warning");
  if (tabWarning) tabWarning.textContent = warnings.length ? "⚠ Attendance warning: " + warnings.join(", ") : "All subjects are at or above 75% this month.";

  const statsDiv = document.getElementById("stats");
  if (warnings.length && statsDiv) {
    const banner = h("p", "stat-warning", "⚠ Below 75%: " + warnings.length + " subject" + (warnings.length > 1 ? "s" : ""));
    banner.setAttribute("role", "status");
    statsDiv.prepend(banner);
  }
  return warnings;
}

function showTab(id) {
  document.querySelectorAll(".tab").forEach(t =>
    t.classList.add("hidden")
  );
  document.getElementById(id).classList.remove("hidden");
  if (id === "announcements") {
    announcements = loadStore("announcements", announcements); // pick up posts made from Vision
    renderAnnouncements(); // show the list when the tab opens, not only after posting
  }
}

function logout() {
  clearSession();
  location.reload();     // back to the login screen with nothing left in memory
}

// Vision (in the Import tab, or another tab) saved a new timetable or announcement: show it without a reload
window.addEventListener("storage", e => {
  if (e.key === STORE_KEYS.timetable) {
    applySavedTimetable();
    if (currentUser) renderCalendar();
  }
  if (e.key === STORE_KEYS.announcements) {
    announcements = loadStore("announcements", announcements);
    if (currentUser) renderAnnouncements();
  }
});

function changeMonth(dir) {
  currentDate.setMonth(currentDate.getMonth() + dir);
  renderCalendar();
}

// index.html calls these two names; they just forward to changeMonth
function prevMonth() { changeMonth(-1); }
function nextMonth() { changeMonth(1); }




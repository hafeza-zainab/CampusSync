// DEMO DATA: gives each of the four demo accounts a different situation, so the app shows something
// different per login. Runs once per browser (flag below) and replaces the attendance of the four demo accounts only; announcements and study items are added only if empty ("Reset demo data" empties them first).
// To see it again: clear this site's localStorage. All names and IDs are placeholders.
//
//   DEMO-CS-001 Zainab (CR)      : excellent, about 90% in every subject, everything marked
//   DEMO-CS-002 Aarav  (ACR)     : fine overall, but DBMS is far below 75% (warning banner + red row)
//   DEMO-CS-003 Meera  (student) : struggling, ~70% overall, several subjects below 75%
//   DEMO-CS-004 Kabir  (student) : only the first weeks are marked (many "unmarked"), Networks borderline
(function () {
  "use strict";
  const FLAG = "campussync.demoseed.v2";
  // "Reset demo data" on the login screen: forget the flag, then the seed below runs again
  document.addEventListener("click", e => {
    if (e.target && e.target.id === "resetDemo") {
      // also forget test posts (announcements, study items), so the realistic seeded ones below come back
      try { [FLAG, STORE_KEYS.announcements, STORE_KEYS.study].forEach(k => localStorage.removeItem(k)); } catch (x) { /* ignore */ }
      location.reload();
    }
  });
  try { if (localStorage.getItem(FLAG)) return; } catch (e) { return; }

  // absent: share of held lectures missed (per subject, "*" = every other subject)
  // unmarkedDays: the most recent N days are left unmarked
  const PROFILES = {
    "DEMO-CS-001": { absent: { "*": 0.09 }, unmarkedDays: 1 },
    "DEMO-CS-002": { absent: { "*": 0.10, "DBMS": 0.42 }, unmarkedDays: 1 },
    "DEMO-CS-003": { absent: { "*": 0.30, "Java": 0.50, "Operating Systems": 0.06 }, unmarkedDays: 1 },
    "DEMO-CS-004": { absent: { "*": 0.18, "Computer Networks": 0.30 }, unmarkedDays: 9 }
  };

  const key = (d, lec) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}-${lec.subject}-${lec.time}`;

  // every semester that has started gets marks, using that semester's own subjects
  function buildAttendance(profile) {
    const marks = {}, rate = s => (s in profile.absent ? profile.absent[s] : profile.absent["*"]);
    const cutoff = new Date(); cutoff.setHours(0, 0, 0, 0); cutoff.setDate(cutoff.getDate() - profile.unmarkedDays);
    semesters.forEach(sem => {
      const seen = {}, table = sem === activeSemester ? defaultTimetable : sem.timetable, end = parseDay(sem.end);
      for (let d = parseDay(sem.start); d <= end && d <= cutoff; d.setDate(d.getDate() + 1)) {
        const day = d.toLocaleString("en-US", { weekday: "long" });
        (table[day] || []).forEach(lec => {
          const n = seen[lec.subject] = (seen[lec.subject] || 0) + 1;
          const r = rate(lec.subject);
          marks[key(d, lec)] = Math.floor(n * r) > Math.floor((n - 1) * r) ? "absent" : "present";   // evenly spread misses
        });
      }
    });
    return marks;
  }

  const daysAgo = n => { const d = new Date(); d.setDate(d.getDate() - n); return d.toISOString().slice(0, 10); };

  try {
    Object.keys(PROFILES).forEach(id => {
      saveStore("attendance", buildAttendance(PROFILES[id]), id);
    });

    if (!(loadStore("announcements", []) || []).length) {
      saveStore("announcements", [
        { msg: "Mid-semester exams start next Monday. Timetable is on the notice board.", by: "DEMO-CS-001", role: "cr" },
        { msg: "DBMS lab moved to Thursday 10-11 this week. Bring your record books.", by: "DEMO-CS-002", role: "acr" },
        { msg: "Attendance below 75% will block exam hall tickets. Check the Monthly Stats panel.", by: "DEMO-CS-001", role: "cr" },
        { msg: "Software Engineering project groups are final. Submit the topic by Friday.", by: "DEMO-CS-002", role: "acr" }
      ]);
    }

    if (!(loadStore("study", []) || []).length) {
      const item = (i, by, subject, topic, ago, extra) => Object.assign(
        { id: "demo" + i, source: "upload", semester: "sem5", subject, topic, date: daysAgo(ago), addedBy: by, addedAt: Date.now() - ago * 864e5 }, extra);
      saveStore("study", [
        item(1, "DEMO-CS-001", "DBMS", "Normalization: 1NF to BCNF", 3),
        item(2, "DEMO-CS-001", "Operating Systems", "CPU scheduling algorithms", 6),
        item(3, "DEMO-CS-002", "Java", "Collections framework notes", 9),
        item(4, "DEMO-CS-003", "Computer Networks", "OSI vs TCP/IP model", 12),
        item(5, "DEMO-CS-004", "Software Engineering", "SDLC models summary", 15),
        item(6, "DEMO-CS-002", "DBMS", "SQL joins practice sheet", 2,
          { source: "vision", via: "Vision", kind: "lecture", confidence: 0.64, needsCheck: true, semesterName: "Semester 5" })
      ]);
    }
    localStorage.setItem(FLAG, "1");
  } catch (e) { console.warn("Demo data not seeded", e); }
})();

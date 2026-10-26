// 60-second demo tour. The "Run 60-second demo" button on the login screen drives the real app:
// it types, clicks and switches tabs by itself while a caption bar explains each step.
//
//   Part 1 (as the CR, DEMO-CS-001): login, calendar + semesters, marking attendance, attendance tab,
//           typing an announcement, study panel, chat, import.
//   Part 2 (as a student, DEMO-CS-003): the page reloads, the student logs in and can only READ announcements.
//
// Everything the tour adds is tagged "(demo)" and removed when it ends or is stopped, and the CR's attendance
// is put back as it was. The page reloads at the end, back to the login screen.
(function () {
  "use strict";

  const TOTAL_MS = 60000;
  const PACE = 1.25;                              // stretches every pause so the whole tour fills about 60 seconds
  const KEY = "campussync.tour";                 // sessionStorage: { start, part }
  const TAG = "(demo)";
  let aborted = false;
  let bar = null;

  const $ = id => document.getElementById(id);
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  async function wait(ms) {                       // sleeps, but stops quickly when the tour is stopped
    const end = Date.now() + ms * PACE;
    while (Date.now() < end) { if (aborted) throw new Error("stopped"); await sleep(50); }
    if (aborted) throw new Error("stopped");
  }
  const state = () => { try { return JSON.parse(sessionStorage.getItem(KEY)); } catch (e) { return null; } };
  const setState = s => { try { sessionStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* ignore */ } };

  // ---------------------------------------------------------------- caption bar
  function showBar(start) {
    bar = document.createElement("div");
    bar.id = "tourBar";
    bar.setAttribute("role", "status");
    const row = document.createElement("div"); row.className = "tour-row";
    const text = document.createElement("span"); text.className = "tour-text";
    const time = document.createElement("span"); time.className = "tour-time";
    const stop = document.createElement("button"); stop.type = "button"; stop.textContent = "Stop demo";
    stop.addEventListener("click", () => { aborted = true; });
    row.append(text, time, stop);
    const track = document.createElement("div"); track.className = "tour-track";
    const fill = document.createElement("div"); fill.className = "tour-fill";
    track.append(fill);
    bar.append(row, track);
    document.body.append(bar);
    bar._text = text;
    setInterval(() => {
      const ms = Math.min(Date.now() - start, TOTAL_MS);
      fill.style.width = (ms / TOTAL_MS * 100) + "%";
      time.textContent = Math.floor(ms / 1000) + " / 60 s";
    }, 250);
  }
  const say = msg => { bar._text.textContent = msg; };

  // ---------------------------------------------------------------- acting on the page
  async function focusOn(node, ms) {
    if (!node) throw new Error("tour: element not found");
    node.scrollIntoView({ block: "center", behavior: "smooth" });
    node.classList.add("tour-focus");
    await wait(ms || 500);
    return node;
  }
  async function click(node, ms) {
    await focusOn(node, ms);
    node.click();
    node.classList.remove("tour-focus");
  }
  async function type(input, text, perChar) {
    await focusOn(input, 300);
    input.focus();
    input.value = "";
    for (const ch of text) {
      input.value += ch;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      await wait(perChar || 45);
    }
    input.classList.remove("tour-focus");
  }
  function choose(select, value) {
    if (![...select.options].some(o => o.value === value)) value = ([...select.options].find(o => o.value) || {}).value || "";   // first real option
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  }
  const tab = id => window.showTab(id);
  const todayIso = () => { const d = new Date(), p = n => String(n).padStart(2, "0"); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; };
  const pastLectures = () => [...document.querySelectorAll("#calendarGrid .lecture")].filter(l => l.style.cursor === "pointer");

  async function loginAs(id, password) {
    await type($("username"), id, 55);
    await type($("password"), password, 55);
    await click(document.querySelector(".login-container > button"), 300);
    await wait(500);
  }

  // ---------------------------------------------------------------- cleanup
  function cleanup(snapshot) {
    try {
      saveStore("announcements", (loadStore("announcements", []) || []).filter(a => !String(a.msg).includes(TAG)));
      saveStore("study", (loadStore("study", []) || []).filter(x => !String(x.topic).includes(TAG)));
      const chat = loadStore("chat", null);
      if (chat && Array.isArray(chat.messages)) {
        chat.messages = chat.messages.filter(m => !(m.card && String(m.card.topic).includes(TAG)));
        saveStore("chat", chat);
      }
      if (snapshot) saveStore("attendance", snapshot, "DEMO-CS-001");
    } catch (e) { /* storage blocked: nothing was added either */ }
  }
  function finish() {
    const att = attendanceBackup();
    try { sessionStorage.removeItem(KEY); sessionStorage.removeItem(KEY + ".att"); } catch (e) { /* ignore */ }
    cleanup(att);
    location.reload();
  }
  function attendanceBackup() { try { return JSON.parse(sessionStorage.getItem(KEY + ".att")); } catch (e) { return null; } }

  // ---------------------------------------------------------------- part 1: the CR
  async function partOne(start) {
    say("1/8  Login: your college ID and password decide your role (this is the CR)");
    await wait(900);
    await loginAs("DEMO-CS-001", "cr-demo");

    say("2/8  Calendar: lectures only appear inside a semester's dates");
    await wait(1800);
    await click(document.querySelector(".calendar-header button"), 300);          // previous month
    await wait(900);
    await click(document.querySelectorAll(".calendar-header button")[1], 300);    // back to this month
    await wait(500);

    say("3/8  Semester 6 has not started: greyed out, attendance and stats not applicable");
    for (let i = 0; i < 3; i++) { await click(document.querySelectorAll(".calendar-header button")[1], 150); await wait(550); }
    await wait(1800);
    for (let i = 0; i < 3; i++) { await click(document.querySelector(".calendar-header button"), 100); await wait(250); }
    await wait(300);

    say("4/8  Mark attendance: click a finished lecture, choose Absent. The stats update.");
    try { sessionStorage.setItem(KEY + ".att", JSON.stringify(attendance)); } catch (e) { /* ignore */ }
    const lectures = pastLectures();
    const idx = lectures.length - 1;
    if (idx >= 0) {
      await click(lectures[idx], 500);
      await click(document.querySelector(".attend-menu .attend-absent"), 700);
      await focusOn($("statsPanel"), 1600);
      $("statsPanel").classList.remove("tour-focus");
      say("Now change it back to Present");
      await click(pastLectures()[idx], 400);
      await click(document.querySelector(".attend-menu .attend-present"), 700);
      await wait(700);
    }

    say("5/8  Attendance tab: per-subject table and the 75% warning");
    tab("attendance");
    await focusOn($("attendanceList"), 3200);
    $("attendanceList").classList.remove("tour-focus");

    say("6/8  Announcements: the CR types one live and posts it");
    tab("announcements");
    await wait(500);
    await type($("msg"), "Class test on Friday: DBMS Unit 2. Revise normalization! " + TAG, 38);
    await click(document.querySelector(".announce-input button"), 300);
    await wait(1500);

    say("7/8  Study Panel: tag a material by semester, subject and topic");
    tab("study");
    await wait(500);
    choose($("study-semester"), "sem5");
    choose($("study-subject"), "DBMS");
    await type($("study-topic"), "Normalization notes " + TAG, 35);
    $("study-date").value = todayIso();
    await wait(300);
    document.querySelector(".study-form").requestSubmit();
    await wait(1600);

    say("8/8  Chat: request notes with a template (no free text, stays on topic)");
    tab("chat");
    await wait(600);
    await click($("chat-new-request"), 400);
    choose($("chat-req-subject"), "DBMS");
    await type($("chat-req-topic"), "Unit 2 notes " + TAG, 40);
    await wait(300);
    $("chat-req-topic").form.requestSubmit();
    await wait(1700);

    say("Vision: upload a timetable screenshot or notice and it fills the calendar and Study Panel");
    tab("study");
    $("import").open = true;
    await focusOn($("import"), 2300);
    $("import").classList.remove("tour-focus");

    // restore the CR's attendance now, then reload and continue as a student
    const att = attendanceBackup();
    if (att) saveStore("attendance", att, "DEMO-CS-001");
    setState({ start, part: 2 });
    location.reload();
  }

  // ---------------------------------------------------------------- part 2: a student
  async function partTwo() {
    say("A student logs in: same app, different rights");
    await wait(600);
    await loginAs("DEMO-CS-003", "student-demo");
    tab("announcements");
    say("Students can read announcements but cannot post: the box is gone");
    await focusOn($("announceNote"), 2000);
    $("announceNote").classList.remove("tour-focus");
    await wait(1500);
    say("That is CampusSync: calendar, attendance, announcements, study, chat, Vision. Thank you!");
    await wait(2500);
  }

  // ---------------------------------------------------------------- start
  async function run(part, start) {
    showBar(start);
    try {
      if (part === 2) await partTwo(); else await partOne(start);
      if (part === 2) finish();
    } catch (e) {
      if (e.message !== "stopped") console.warn(e);
      finish();
    }
  }

  function init() {
    const btn = $("tourStart");
    if (btn) btn.addEventListener("click", () => {
      const start = Date.now();
      setState({ start, part: 1 });
      btn.disabled = true;
      run(1, start);
    });
    const s = state();
    if (s && s.part === 2) run(2, s.start);       // continuing after the reload
    else if (s) { try { sessionStorage.removeItem(KEY); } catch (e) { /* ignore */ } }   // an interrupted run: forget it
  }
  init();
})();

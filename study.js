// Study Panel (front-end only), built into the existing "Study Panel" tab of the CampusSync app.
//
// WHAT IT DOES
//   * Upload a study material tagged by Semester, Subject, Topic and Date (the file is optional).
//   * Filter the list by Semester, Subject, Topic text and a Date range.
//   * Entries that Vision extracted from a screenshot appear here too, marked with their source,
//     and with an amber "check this" when Vision was not sure (below 80%).
//
// WHERE THE DATA LIVES
//   There is no server. Items are kept in localStorage through store.js (key "study"):
//     { id, source: "upload" | "vision", semester, subject, topic, date, addedBy, addedAt,
//       fileName?, fileType?, fileSize?, fileData? (the file as a data URL, only if it is <= 1 MB),
//       via?, kind?, teacher?, room?, confidence?, needsCheck?, courseName?, semesterName? }
//   Browsers allow only a few MB of localStorage in total, so files above 1 MB are refused with a clear message.
//
// Like chat.js, this file builds its own content inside the existing tab; index.html only loads the script.
// All text is added with textContent, never innerHTML.
(function () {
  "use strict";

  const MAX_FILE = 1024 * 1024;        // about 1 MB: bigger files do not fit in browser storage
  const MAX_TOPIC = 80;
  const SEMESTERS = [1, 2, 3, 4, 5, 6].map(n => ({ id: "sem" + n, name: "Semester " + n }));
  const LOW_CONFIDENCE = 0.80;         // same threshold as Vision: below this an entry is flagged "check this"

  let items = [];
  const ui = {};

  // ---------------------------------------------------------------- helpers
  function el(tag, props, ...children) {
    const node = document.createElement(tag);
    Object.entries(props || {}).forEach(([k, v]) => {
      if (k === "className") node.className = v;
      else if (k === "text") node.textContent = v;
      else node.setAttribute(k, v);
    });
    children.forEach(c => node.append(c));
    return node;
  }

  const pad = n => String(n).padStart(2, "0");
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
  const validDate = v => /^\d{4}-\d{2}-\d{2}$/.test(v) && !isNaN(new Date(v + "T12:00:00"));
  const prettyDate = v => new Date(v + "T12:00:00").toLocaleDateString([], { weekday: "short", day: "numeric", month: "short", year: "numeric" });
  const cleanTopic = v => String(v || "").replace(/\s+/g, " ").trim().slice(0, MAX_TOPIC);
  const uid = () => "u" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  const mb = bytes => (bytes / (1024 * 1024)).toFixed(1) + " MB";

  function timetableSubjects() {
    const subjects = [];
    try {
      Object.values(timetable).forEach(day => day.forEach(l => {
        if (l.subject && l.subject !== "Break" && !subjects.includes(l.subject)) subjects.push(l.subject);
      }));
    } catch (e) { /* no timetable */ }
    return subjects;
  }

  const semesterName = it => it.semesterName || (SEMESTERS.find(s => s.id === it.semester) || {}).name || (it.semester ? it.semester : "Semester not set");
  const who = () => (typeof currentUser === "string" && currentUser) || (getSession() || {}).id || "";

  // ---------------------------------------------------------------- storage
  function load() {
    const saved = loadStore("study", []);
    items = Array.isArray(saved) ? saved.filter(x => x && typeof x.id === "string" && typeof x.subject === "string") : [];
  }

  // false when the browser refuses (storage full or blocked)
  function save() { return saveStore("study", items); }

  // ---------------------------------------------------------------- upload form
  function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
  }

  function say(node, text, ok) {
    node.textContent = text;
    node.className = "study-msg " + (ok ? "ok" : "bad");
  }

  async function addMaterial(e) {
    e.preventDefault();
    const semester = ui.fSemester.value, subject = ui.fSubject.value, topic = cleanTopic(ui.fTopic.value), date = ui.fDate.value;
    const files = [...ui.fFile.files];
    if (!semester) return say(ui.formMsg, "Choose a semester.", false);
    if (!timetableSubjects().includes(subject)) return say(ui.formMsg, "Choose a subject.", false);
    if (!topic) return say(ui.formMsg, "Write a short topic.", false);
    if (!validDate(date)) return say(ui.formMsg, "Choose a valid date.", false);
    const tooBig = files.find(f => f.size > MAX_FILE);
    if (tooBig) {
      return say(ui.formMsg, `"${tooBig.name}" is ${mb(tooBig.size)}. Files larger than 1 MB cannot be stored in the browser. ` +
        "Choose a smaller file, or add the entry without a file.", false);
    }

    const base = { source: "upload", semester, subject, topic, date, addedBy: who(), addedAt: Date.now() };
    const added = [];
    try {
      if (!files.length) added.push({ id: uid(), ...base });
      for (const f of files) {
        added.push({ id: uid(), ...base, fileName: f.name, fileType: f.type || "application/octet-stream", fileSize: f.size,
                     fileData: await readFileAsDataUrl(f) });
      }
    } catch (err) {
      return say(ui.formMsg, "Could not read the file. Try another one.", false);
    }
    const before = items;
    items = items.concat(added);
    if (!save()) {                                   // storage full: undo and explain
      items = before;
      return say(ui.formMsg, "The browser's storage is full, so this could not be saved. Remove some materials or use smaller files.", false);
    }
    ui.fTopic.value = "";
    ui.fFile.value = "";
    say(ui.formMsg, `Added ${added.length} item${added.length > 1 ? "s" : ""} to the Study Panel.`, true);
    render();
  }

  function removeItem(id) {
    const before = items;
    items = items.filter(x => x.id !== id);
    if (!save()) items = before;
    render();
  }

  // ---------------------------------------------------------------- filters + list
  function currentFilters() {
    return { semester: ui.qSemester.value, subject: ui.qSubject.value, topic: ui.qTopic.value.trim().toLowerCase(),
             from: ui.qFrom.value, to: ui.qTo.value };
  }

  function matches(it, f) {
    if (f.semester && (it.semester || "none") !== f.semester) return false;
    if (f.subject && it.subject !== f.subject) return false;
    if (f.topic && !String(it.topic).toLowerCase().includes(f.topic)) return false;
    if (f.from && it.date < f.from) return false;
    if (f.to && it.date > f.to) return false;
    return true;
  }

  // keep the filter drop-downs in step with the data (subjects/semesters that exist), without losing the current choice
  function refreshFilterOptions() {
    const keep = { semester: ui.qSemester.value, subject: ui.qSubject.value };
    const semesters = [...new Map(SEMESTERS.map(s => [s.id, s.name])).entries()];
    items.forEach(it => { if (it.semester && !semesters.some(([id]) => id === it.semester)) semesters.push([it.semester, semesterName(it)]); });
    if (items.some(it => !it.semester)) semesters.push(["none", "Semester not set"]);
    ui.qSemester.replaceChildren(el("option", { value: "", text: "All semesters" }), ...semesters.map(([id, name]) => el("option", { value: id, text: name })));
    ui.qSemester.value = semesters.some(([id]) => id === keep.semester) ? keep.semester : "";

    const subjects = [...new Set([...timetableSubjects(), ...items.map(i => i.subject)])].sort((a, b) => a.localeCompare(b));
    ui.qSubject.replaceChildren(el("option", { value: "", text: "All subjects" }), ...subjects.map(s => el("option", { value: s, text: s })));
    ui.qSubject.value = subjects.includes(keep.subject) ? keep.subject : "";
  }

  function card(it) {
    const mine = it.addedBy && it.addedBy === who();
    const head = el("div", { className: "study-topic", text: it.topic });
    const tags = el("div", { className: "study-tags" },
      el("span", { className: "study-chip", text: semesterName(it) }),
      el("span", { className: "study-chip", text: it.subject }),
      el("span", { className: "study-chip", text: prettyDate(it.date) }));
    const meta = el("div", { className: "study-meta" });
    if (it.source === "vision") {
      meta.append(el("span", { className: "study-chip vision", text: "Vision · " + (it.via || "screenshot") }));
      if (it.needsCheck) meta.append(el("span", { className: "study-chip warn", text: "check this (" + Math.round((it.confidence || 0) * 100) + "% sure)" }));
      if (it.teacher) meta.append(el("span", { className: "study-chip", text: "Teacher: " + it.teacher }));
      if (it.room) meta.append(el("span", { className: "study-chip", text: "Room: " + it.room }));
    } else {
      meta.append(el("span", { className: "study-chip upload", text: "Uploaded" }));
    }
    if (it.addedBy) meta.append(el("span", { className: "study-by", text: "by " + it.addedBy }));

    const node = el("article", { className: "study-card" + (it.needsCheck ? " needs-check" : ""), "aria-label": `${it.subject}: ${it.topic}` }, head, tags, meta);
    if (it.fileData && it.fileData.startsWith("data:")) {            // only our own data URLs are ever linked
      const link = el("a", { className: "study-file", href: it.fileData, download: it.fileName || "material", text: `📄 ${it.fileName} (${mb(it.fileSize || 0)})` });
      node.append(link);
    }
    if (mine) {
      const del = el("button", { type: "button", className: "study-remove", text: "Remove", "aria-label": `Remove ${it.topic}` });
      del.addEventListener("click", () => removeItem(it.id));
      node.append(del);
    }
    return node;
  }

  function render() {
    refreshFilterOptions();
    const f = currentFilters();
    const shown = items.filter(it => matches(it, f)).sort((a, b) => (b.date || "").localeCompare(a.date || "") || b.addedAt - a.addedAt);
    ui.list.replaceChildren();
    if (!items.length) ui.list.append(el("p", { className: "study-empty", text: "No study materials yet. Upload one above, or import a timetable or notice from a screenshot." }));
    else if (!shown.length) ui.list.append(el("p", { className: "study-empty", text: "No materials match these filters." }));
    else shown.forEach(it => ui.list.append(card(it)));
    ui.count.textContent = `Showing ${shown.length} of ${items.length}`;
  }

  // ---------------------------------------------------------------- building the tab
  function build() {
    const section = document.getElementById("study");
    const list = document.getElementById("materialsList");          // the existing (empty) container is reused for the list
    ui.list = list;
    list.className = "study-list";

    const field = (label, input, id) => el("div", { className: "study-field" }, el("label", { for: id, text: label }), input);

    ui.fSemester = el("select", { id: "study-semester" }, el("option", { value: "", text: "Choose…" }), ...SEMESTERS.map(s => el("option", { value: s.id, text: s.name })));
    ui.fSubject = el("select", { id: "study-subject" });
    ui.fTopic = el("input", { id: "study-topic", type: "text", maxlength: String(MAX_TOPIC), placeholder: "e.g. Loops, Normalization" });
    ui.fDate = el("input", { id: "study-date", type: "date" });
    ui.fFile = el("input", { id: "study-file", type: "file", multiple: "" });
    ui.formMsg = el("p", { className: "study-msg", role: "status" });
    const form = el("form", { className: "study-form", novalidate: "" },
      el("h4", { text: "Add a study material" }),
      field("Semester", ui.fSemester, "study-semester"),
      field("Subject", ui.fSubject, "study-subject"),
      field("Topic", ui.fTopic, "study-topic"),
      field("Date", ui.fDate, "study-date"),
      field("File (optional, up to 1 MB each)", ui.fFile, "study-file"),
      el("button", { type: "submit", className: "study-btn primary", text: "Add to Study Panel" }),
      ui.formMsg);
    form.addEventListener("submit", addMaterial);

    ui.qSemester = el("select", { id: "study-q-semester" });
    ui.qSubject = el("select", { id: "study-q-subject" });
    ui.qTopic = el("input", { id: "study-q-topic", type: "search", placeholder: "Search topic…" });
    ui.qFrom = el("input", { id: "study-q-from", type: "date" });
    ui.qTo = el("input", { id: "study-q-to", type: "date" });
    const clear = el("button", { type: "button", className: "study-btn", text: "Clear filters" });
    clear.addEventListener("click", () => {
      ui.qSemester.value = ""; ui.qSubject.value = ""; ui.qTopic.value = ""; ui.qFrom.value = ""; ui.qTo.value = "";
      render();
    });
    ui.count = el("p", { className: "study-count", role: "status" });
    const filters = el("div", { className: "study-filters", role: "search", "aria-label": "Filter study materials" },
      field("Semester", ui.qSemester, "study-q-semester"), field("Subject", ui.qSubject, "study-q-subject"),
      field("Topic", ui.qTopic, "study-q-topic"), field("From", ui.qFrom, "study-q-from"), field("To", ui.qTo, "study-q-to"), clear);
    [ui.qSemester, ui.qSubject, ui.qTopic, ui.qFrom, ui.qTo].forEach(c => c.addEventListener("input", render));

    section.insertBefore(el("div", { className: "study-top" }, form, el("div", { className: "study-right" }, el("h4", { text: "Filter" }), filters, ui.count)), list);
    ui.fDate.value = today();
  }

  function fillSubjectChoices() {
    const keep = ui.fSubject.value;
    const subjects = timetableSubjects();
    ui.fSubject.replaceChildren(el("option", { value: "", text: subjects.length ? "Choose…" : "No subjects in the timetable" }), ...subjects.map(s => el("option", { value: s, text: s })));
    ui.fSubject.value = subjects.includes(keep) ? keep : "";
  }

  function init() {
    document.head.append(el("link", { rel: "stylesheet", href: "study.css" }));
    build();
    load();
    fillSubjectChoices();
    render();

    // Vision (Import tab) or another tab changed the Study Panel data: show it
    window.addEventListener("storage", e => {
      if (e.key !== null && e.key !== STORE_KEYS.study && e.key !== STORE_KEYS.timetable) return;
      load();
      fillSubjectChoices();
      render();
    });

    // wrap showTab from app.js: re-read the data whenever the tab opens
    const originalShowTab = window.showTab;
    window.showTab = function (id) {
      originalShowTab(id);
      if (id === "study") { load(); fillSubjectChoices(); render(); }
    };
  }

  init();
})();

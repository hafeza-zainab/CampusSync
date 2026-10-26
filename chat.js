// CampusSync Chat tab (front-end only).
//
// WHAT THIS IS: a demo chat inside the attendance app. The "users" are DEMO users picked from the
// "Chatting as" box, all in ONE browser. Messages are kept in localStorage (key "chat" in store.js),
// and two tabs of the same browser stay in sync through the browser's "storage" event.
// There is no server and no accounts, so this is NOT real multi-user chat.
//
// HOW IT HOOKS IN: index.html loads this file with one <script> line. This file then builds its own nav
// button, its own tab section and its own stylesheet link, and wraps showTab()/login() from app.js,
// so app.js, style.css and data.js are not edited.
//
// Message text is always put on the page with textContent (never innerHTML), so typed HTML is shown as
// plain text and cannot break the page.
(function () {
  "use strict";

  const USERS = ["Zainab", "Aarav", "Meera", "Kabir"];                  // demo users
  const COLORS = { Zainab: "#5b4bc4", Aarav: "#1f7a4a", Meera: "#b8400c", Kabir: "#0e6f86" };
  const ME_KEY = "campussync.chat.me";   // sessionStorage: who THIS tab is chatting as (so two tabs can differ)
  const MAX_TEXT = 1000;
  const MAX_TOPIC = 80;   // a note request's topic is a short text

  let data = null;       // { messages: [...], reads: { user: { conversation: lastReadTime } } }
  let me = USERS[0];     // current demo user in this tab
  let convo = "class";   // id of the open conversation
  const ui = {};         // DOM elements we need to find again

  // ---------------------------------------------------------------- small helpers
  // el("div", {className: "x"}, "text", childElement) -> element. Strings become TEXT, never HTML.
  function el(tag, props, ...children) {
    const node = document.createElement(tag);
    Object.entries(props || {}).forEach(([k, v]) => {
      if (k === "className") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v);
    });
    children.forEach(c => node.append(c));
    return node;
  }

  // one-to-one conversations have one id for the pair, whoever is "me": dmId("Zainab","Meera") === dmId("Meera","Zainab")
  const dmId = (a, b) => "dm:" + [a, b].sort().join("|");
  const uid = () => "m" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  const timeOf = ts => new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const dayKey = ts => { const d = new Date(ts); return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`; };

  function dayLabel(ts) {
    const today = dayKey(Date.now()), yesterday = dayKey(Date.now() - 24 * 3600 * 1000);
    if (dayKey(ts) === today) return "Today";
    if (dayKey(ts) === yesterday) return "Yesterday";
    return new Date(ts).toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" });
  }

  // The subjects you can request notes for: the ones in the timetable the app is using right now
  // (data.js, or the one Vision saved). "timetable" is the global from data.js / app.js.
  function subjectList() {
    const subjects = [];
    try {
      Object.values(timetable).forEach(day => day.forEach(l => {
        if (l.subject && l.subject !== "Break" && !subjects.includes(l.subject)) subjects.push(l.subject);
      }));
    } catch (e) { /* no timetable: the form will say so */ }
    return subjects;
  }

  const pad = n => String(n).padStart(2, "0");
  const localDate = (d = new Date()) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;   // yyyy-mm-dd, local time
  const validDate = v => /^\d{4}-\d{2}-\d{2}$/.test(v) && localDate(new Date(v + "T12:00:00")) === v;
  const cleanTopic = v => String(v || "").replace(/\s+/g, " ").trim().slice(0, MAX_TOPIC);
  const prettyDate = v => new Date(v + "T12:00:00").toLocaleDateString([], { weekday: "short", day: "numeric", month: "short", year: "numeric" });

  // A request must be exactly {subject, date, topic, status, ...} with plain strings; anything else is not drawn.
  const isRequest = m => m.type === "request" && m.request && ["subject", "date", "topic", "status"].every(k => typeof m.request[k] === "string");
  const previewOf = m => m.type === "request" ? "📝 Note request: " + (m.request ? m.request.subject : "") : m.text;

  // ---------------------------------------------------------------- storage (uses store.js)
  function seedData() {
    const now = Date.now(), H = 3600 * 1000, D = 24 * H;
    const msg = (from, ago, text, c = "class") => ({ id: uid(), convo: c, from, ts: now - ago, type: "text", text });
    const zm = dmId("Zainab", "Meera"), ak = dmId("Aarav", "Kabir");
    const subjects = subjectList();
    const request = {   // one open note request from Meera, so the tab is not empty on first load
      id: uid(), convo: "class", from: "Meera", ts: now - 1.5 * H, type: "request",
      request: { subject: subjects.includes("DAA") ? "DAA" : (subjects[0] || "Subject"), date: localDate(new Date(now - D)),
                 topic: "Second half of the lecture", status: "open" },
    };
    return {
      version: 1,
      messages: [
        msg("Aarav", D + 3 * H, "Hi all! Is the DAA assignment still due this Friday?"),
        msg("Meera", D + 2.5 * H, "Yes, Friday. I'll post my notes once I've cleaned them up."),
        msg("Kabir", 3 * H, "Reminder: the Python lab starts at 10 tomorrow."),
        request,
        msg("Zainab", 2 * H, "Thanks Kabir! I'll bring my laptop."),
        msg("Meera", 5 * H, "Are you free to go over the DAA assignment tonight?", zm),
        msg("Zainab", 4.5 * H, "Sure, 8pm works for me.", zm),
        msg("Meera", 0.7 * H, "Great, I'll call you then.", zm),
        msg("Kabir", 2 * H, "Did you finish the OS lab questions?", ak),
      ],
      reads: {},
    };
  }

  function isValid(d) { return d && Array.isArray(d.messages) && d.reads && typeof d.reads === "object"; }

  // load(true) creates the demo data the first time; load(false) never writes (used by the storage event)
  function load(seedIfMissing) {
    const saved = loadStore("chat", null);
    if (isValid(saved)) return saved;
    if (!seedIfMissing) return data;
    const fresh = seedData();
    saveStore("chat", fresh);
    return fresh;
  }

  // Read the newest saved data, change it, save it. Re-reading first means another tab's new messages are not lost.
  function update(change) {
    const fresh = load(true);
    change(fresh);
    saveStore("chat", fresh);
    data = fresh;
  }

  // ---------------------------------------------------------------- conversations and unread counts
  const convoMessages = id => data.messages.filter(m => m.convo === id).sort((a, b) => a.ts - b.ts || (a.id < b.id ? -1 : 1));
  const chatShown = () => ui.section && ui.section.offsetParent !== null && document.visibilityState === "visible";

  function unreadCount(id) {
    const last = (data.reads[me] || {})[id] || 0;
    return convoMessages(id).filter(m => m.from !== me && m.ts > last).length;
  }

  function markRead() {
    if (!chatShown()) return;
    const msgs = convoMessages(convo);
    if (!msgs.length) return;
    const newest = msgs[msgs.length - 1].ts;
    if (newest > ((data.reads[me] || {})[convo] || 0)) {
      update(d => { (d.reads[me] ||= {})[convo] = newest; });   // only writes when something new was read
    }
  }

  // ---------------------------------------------------------------- rendering
  function renderConvoList() {
    ui.list.replaceChildren();
    const items = [{ id: "class", title: "Class group" }]
      .concat(USERS.filter(u => u !== me).map(u => ({ id: dmId(me, u), title: u })));
    items.forEach(c => {
      const msgs = convoMessages(c.id), last = msgs[msgs.length - 1], unread = unreadCount(c.id);
      // in the group show who spoke; in a one-to-one only mark your own messages
      const who = last && last.from === me ? "You: " : (c.id === "class" && last ? last.from + ": " : "");
      const preview = last ? who + previewOf(last) : "No messages yet";
      const btn = el("button", { className: "chat-convo" + (c.id === convo ? " active" : ""), type: "button",
        "aria-current": c.id === convo ? "true" : "false" },
        el("span", { className: "chat-convo-top" },
          el("span", { className: "chat-convo-title", text: c.title }),
          last ? el("span", { className: "chat-convo-time", text: timeOf(last.ts) }) : ""),
        el("span", { className: "chat-convo-preview", text: preview }),
        unread ? el("span", { className: "chat-badge", text: String(unread), "aria-label": `${unread} unread` }) : "");
      btn.addEventListener("click", () => openConvo(c.id));
      ui.list.append(el("li", {}, btn));
    });
  }

  function renderHeader() {
    ui.title.textContent = convo === "class" ? "Class group" : convo.slice(3).split("|").find(u => u !== me);
    ui.subtitle.textContent = convo === "class" ? "Everyone · demo users" : "One-to-one · demo users";
  }

  function renderMessages(forceBottom) {
    const box = ui.messages;
    const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
    box.replaceChildren();
    const msgs = convoMessages(convo);
    if (!msgs.length) {
      box.append(el("p", { className: "chat-empty", text: "No messages yet. Say hello!" }));
      return;
    }
    let prevDay = "";
    msgs.filter(m => m.type !== "request" || isRequest(m)).forEach(m => {
      if (dayKey(m.ts) !== prevDay) {
        prevDay = dayKey(m.ts);
        box.append(el("div", { className: "chat-day", text: dayLabel(m.ts) }));
      }
      box.append(renderMessage(m));
    });
    if (forceBottom || nearBottom) box.scrollTop = box.scrollHeight;
  }

  // The card for a note request: Subject / Date / Topic, a status, and a button for everyone except the requester.
  function renderRequest(m) {
    const r = m.request;
    const row = (label, value) => el("div", { className: "chat-req-row" }, el("dt", { text: label }), el("dd", { text: value }));
    const shared = r.status === "shared";
    const status = el("span", { className: "chat-status " + (shared ? "shared" : "open"), text: shared ? "Shared" : "Open" });
    const foot = el("div", { className: "chat-req-foot" }, status);
    if (shared) {
      foot.append(el("span", { className: "chat-req-by", text: `by ${r.sharedBy} at ${timeOf(r.sharedAt)}` }));
    } else if (m.from !== me) {
      const btn = el("button", { type: "button", className: "chat-btn", text: "I have these notes",
        "aria-label": `I have the notes for ${r.subject}, ${prettyDate(r.date)}` });
      btn.addEventListener("click", () => shareNotes(m.id));
      foot.append(btn);
    }
    return el("div", { className: "chat-request", role: "group", "aria-label": `Note request: ${r.subject}` },
      el("div", { className: "chat-req-title", text: "📝 Note request" }),
      el("dl", { className: "chat-req-list" }, row("Subject", r.subject), row("Date", prettyDate(r.date)), row("Topic", r.topic)),
      foot);
  }

  function renderMessage(m) {
    const mine = m.from === me;
    const avatar = el("span", { className: "chat-avatar", text: m.from[0], "aria-hidden": "true" });
    avatar.style.background = COLORS[m.from] || "#555";
    const head = el("div", { className: "chat-meta" },
      el("span", { className: "chat-from", text: mine ? "You" : m.from }),
      el("time", { text: timeOf(m.ts), datetime: new Date(m.ts).toISOString() }));
    const body = isRequest(m) ? renderRequest(m) : el("div", { className: "chat-text", text: m.text });   // textContent: typed HTML stays plain text
    return el("div", { className: "chat-msg" + (mine ? " mine" : "") }, avatar, el("div", { className: "chat-bubble" }, head, body));
  }

  function render(forceBottom) {
    renderHeader();
    renderMessages(forceBottom);
    markRead();          // before drawing the list, so the unread badge of the open conversation is already gone
    renderConvoList();
  }

  function openConvo(id) {
    convo = id;
    render(true);
  }

  // ---------------------------------------------------------------- actions
  function sendText() {
    const text = ui.input.value.trim().slice(0, MAX_TEXT);
    if (!text) { ui.input.value = ""; return; }              // empty / spaces only: ignore
    update(d => d.messages.push({ id: uid(), convo, from: me, ts: Date.now(), type: "text", text }));
    ui.input.value = "";
    render(true);
    ui.input.focus();
  }

  // "I have these notes": only someone other than the requester, and only while the request is still open
  function shareNotes(id) {
    update(d => {
      const m = d.messages.find(x => x.id === id);
      if (m && isRequest(m) && m.request.status === "open" && m.from !== me) {
        m.request.status = "shared";
        m.request.sharedBy = me;
        m.request.sharedAt = Date.now();
      }
    });
    render(false);
  }

  // The request form has exactly three inputs: Subject, Date, Topic. Nothing else can be typed into a request.
  function buildRequestDialog() {
    ui.reqSubject = el("select", { id: "chat-req-subject", required: "" });
    ui.reqDate = el("input", { id: "chat-req-date", type: "date", required: "" });
    ui.reqTopic = el("input", { id: "chat-req-topic", type: "text", maxlength: String(MAX_TOPIC), required: "", placeholder: "e.g. Chapter 3, second half" });
    ui.reqTarget = el("p", { className: "chat-req-target" });
    ui.reqError = el("p", { className: "chat-req-error", role: "alert" });
    const field = (label, input, id) => el("div", { className: "chat-field" }, el("label", { for: id, text: label }), input);
    const cancel = el("button", { type: "button", className: "chat-btn", text: "Cancel" });
    cancel.addEventListener("click", () => ui.dialog.close());
    const form = el("form", { novalidate: "" },
      el("h4", { text: "Request notes" }),
      ui.reqTarget,
      field("Subject", ui.reqSubject, "chat-req-subject"),
      field("Date", ui.reqDate, "chat-req-date"),
      field("Topic", ui.reqTopic, "chat-req-topic"),
      ui.reqError,
      el("div", { className: "chat-dialog-buttons" }, cancel, el("button", { type: "submit", className: "chat-btn primary", text: "Send request" })));
    form.addEventListener("submit", e => { e.preventDefault(); submitRequest(); });
    ui.dialog = el("dialog", { className: "chat-dialog", "aria-label": "Request notes" }, form);
    ui.dialog.addEventListener("close", () => ui.requestBtn.focus());     // give focus back to the button that opened it
    document.body.append(ui.dialog);
  }

  // prefill = {subject, date, topic} (all optional). The user always reviews and presses Send.
  function openRequestForm(prefill) {
    const subjects = subjectList();
    ui.reqSubject.replaceChildren(el("option", { value: "", text: subjects.length ? "Choose a subject…" : "No subjects in the timetable" }),
      ...subjects.map(sub => el("option", { value: sub, text: sub })));
    const pre = prefill || {};
    ui.reqSubject.value = subjects.includes(pre.subject) ? pre.subject : "";
    ui.reqDate.value = validDate(pre.date) ? pre.date : localDate();     // defaults to today
    ui.reqTopic.value = cleanTopic(pre.topic);
    ui.reqError.textContent = "";
    ui.reqTarget.textContent = "Sending to: " + ui.title.textContent;
    ui.dialog.showModal();
    (ui.reqSubject.value ? ui.reqTopic : ui.reqSubject).focus();
  }

  function submitRequest() {
    const subject = ui.reqSubject.value, date = ui.reqDate.value, topic = cleanTopic(ui.reqTopic.value);
    let problem = "", field = null;
    if (!subjectList().includes(subject)) { problem = "Choose a subject."; field = ui.reqSubject; }
    else if (!validDate(date)) { problem = "Choose a valid date."; field = ui.reqDate; }
    else if (!topic) { problem = "Write a short topic."; field = ui.reqTopic; }
    if (problem) { ui.reqError.textContent = problem; field.focus(); return; }
    update(d => d.messages.push({ id: uid(), convo, from: me, ts: Date.now(), type: "request",
      request: { subject, date, topic, status: "open" } }));
    ui.dialog.close();
    render(true);
  }

  function switchUser(name) {
    me = USERS.includes(name) ? name : USERS[0];
    try { sessionStorage.setItem(ME_KEY, me); } catch (e) { /* private mode: just not remembered */ }
    convo = "class";
    render(true);
  }

  // Reset needs two clicks (no confirm() popup): the first arms the button, the second does it.
  function resetChat() {
    if (!ui.reset.dataset.armed) {
      ui.reset.dataset.armed = "1";
      ui.reset.textContent = "Click again to reset";
      setTimeout(() => { delete ui.reset.dataset.armed; ui.reset.textContent = "Reset chat"; }, 4000);
      return;
    }
    delete ui.reset.dataset.armed;
    ui.reset.textContent = "Reset chat";
    data = seedData();
    saveStore("chat", data);
    convo = "class";
    render(true);
  }

  // ---------------------------------------------------------------- building the page
  function injectStyles() {
    const link = el("link", { rel: "stylesheet", href: "chat.css" });
    document.head.append(link);
  }

  function build() {
    const select = el("select", { id: "chat-as", "aria-label": "Chatting as" },
      ...USERS.map(u => el("option", { value: u, text: u })));
    select.addEventListener("change", () => switchUser(select.value));
    ui.as = select;

    ui.reset = el("button", { type: "button", className: "chat-btn", text: "Reset chat" });
    ui.reset.addEventListener("click", resetChat);

    const topbar = el("div", { className: "chat-topbar" },
      el("label", { for: "chat-as", text: "Chatting as " }), select,
      el("span", { className: "chat-demo", text: "Demo users: simulated in this browser, no server sync. Open a second tab and pick another user." }),
      ui.reset);

    ui.list = el("ul", { className: "chat-convos", "aria-label": "Conversations" });
    ui.title = el("h3", { className: "chat-title" });
    ui.subtitle = el("span", { className: "chat-subtitle" });
    ui.messages = el("div", { className: "chat-messages", role: "log", "aria-live": "polite", "aria-label": "Messages", tabindex: "0" });
    ui.input = el("textarea", { id: "chat-input", rows: "2", maxlength: String(MAX_TEXT), placeholder: "Write a message…" });
    ui.input.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendText(); }   // Shift+Enter = new line
    });
    const sendBtn = el("button", { type: "button", className: "chat-btn primary", text: "Send" });
    sendBtn.addEventListener("click", sendText);

    const composer = el("div", { className: "chat-composer" },
      el("label", { for: "chat-input", className: "chat-sr", text: "Message" }), ui.input, sendBtn,
      el("span", { className: "chat-hint", text: "Enter to send · Shift+Enter for a new line" }));

    ui.requestBtn = el("button", { type: "button", className: "chat-btn", text: "📝 Request notes" });
    ui.requestBtn.addEventListener("click", () => openRequestForm());
    buildRequestDialog();

    const pane = el("div", { className: "chat-pane" },
      el("div", { className: "chat-pane-head" }, el("div", {}, ui.title, ui.subtitle), ui.requestBtn),
      ui.messages, composer);

    ui.section = el("section", { id: "chat", className: "tab hidden" },
      el("h3", { text: "Chat" }), topbar, el("div", { className: "chat-shell" }, ui.list, pane));
    document.getElementById("dashboard").append(ui.section);

    const navBtn = el("button", { type: "button", text: "💬 Chat" });
    navBtn.addEventListener("click", () => window.showTab("chat"));
    document.querySelector(".tab-nav").append(navBtn);
  }

  function init() {
    try { me = sessionStorage.getItem(ME_KEY) || USERS[0]; } catch (e) { me = USERS[0]; }
    if (!USERS.includes(me)) me = USERS[0];
    data = load(true);
    injectStyles();
    build();
    ui.as.value = me;
    render(true);

    // another tab changed the chat -> show it (this is what keeps two tabs in sync)
    window.addEventListener("storage", e => {
      if (e.key !== null && e.key !== STORE_KEYS.chat) return;
      data = load(false);
      render(false);
    });
    document.addEventListener("visibilitychange", () => { if (chatShown()) render(true); });

    // wrap showTab from app.js: when the Chat tab opens, scroll to the newest message and mark it read
    const originalShowTab = window.showTab;
    window.showTab = function (id) {
      originalShowTab(id);
      if (id === "chat") render(true);
    };
  }

  init();
})();

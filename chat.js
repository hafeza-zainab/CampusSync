// CampusSync Chat tab (front-end only).
//
// WHAT THIS IS: a demo chat inside the attendance app, with a class group and one-to-one chats.
// There is NO free-text box. Every message is sent from a template with exactly three fields,
// Subject, Date and Topic, so the chat stays on topic. The templates are:
//     Request notes    -> a request card that someone else can answer with "I have these notes"
//     Notes shared     -> a card telling the class which notes you are sharing
//     Ask a doubt      -> a doubt card that someone else can answer with "I can help"
//
// WHO IS CHATTING: the logged-in college ID (see store.js). The demo accounts have placeholder IDs.
// A "Demo only" switch lets one browser act as another demo account, for the two-tab demo.
//
// HONEST LIMITS: messages live in localStorage (key "chat" in store.js) and two tabs of the SAME
// browser stay in sync through the "storage" event. There is no server, so this is NOT real-time
// chat between different computers or browsers.
//
// HOW IT HOOKS IN: index.html loads this file with one <script> line. This file builds its own nav
// button, tab section and stylesheet link, and wraps showTab()/login() from app.js, so app.js,
// style.css and data.js are not edited. All text goes onto the page with textContent (never innerHTML).
(function () {
  "use strict";

  const USERS = DEMO_USERS.map(u => u.id);   // the demo accounts (placeholder college IDs)
  const COLORS = { "DEMO-CS-001": "#5b4bc4", "DEMO-CS-002": "#1f7a4a", "DEMO-CS-003": "#b8400c", "DEMO-CS-004": "#0e6f86" };
  const ME_KEY = "campussync.chat.demoswitch";   // sessionStorage: DEMO-ONLY override of who this tab chats as
  const MAX_TOPIC = 80;                          // the topic is a short text
  const DATA_VERSION = 3;                        // 3 = template-only messages (older saved chats are replaced by fresh demo data)

  // The three templates. Each card has the same three fields; they differ in the status flow.
  //   states: the words shown for each status;  done: the status after someone answers;  action: the answer button
  const KINDS = {
    request: { icon: "📝", title: "Note request", open: "Request notes", send: "Send request", placeholder: "e.g. Chapter 3, second half",
               states: { open: "Open", shared: "Shared" }, done: "shared", action: "I have these notes" },
    shared:  { icon: "📤", title: "Notes shared", open: "Notes shared", send: "Post to chat", placeholder: "What are the notes about?",
               states: { posted: "Shared" } },
    doubt:   { icon: "❓", title: "Doubt", open: "Ask a doubt", send: "Post doubt", placeholder: "What are you stuck on?",
               states: { open: "Open", answered: "Answered" }, done: "answered", action: "I can help" },
  };

  let data = null;       // { version, messages: [...], reads: { id: { conversation: lastReadTime } } }
  let me = USERS[0];     // who this tab chats as
  let convo = "class";   // id of the open conversation
  let kind = "request";  // which template the form is open for
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

  const nameOf = id => demoName(id) || id;       // "Aarav" for a demo ID, otherwise the ID itself

  function currentIdentity() {                   // the login ID, unless the demo switch is used in this tab
    let override = "";
    try { override = sessionStorage.getItem(ME_KEY) || ""; } catch (e) { /* private mode */ }
    if (USERS.includes(override)) return override;
    const session = getSession();
    return session && session.id ? session.id : USERS[0];
  }

  // one-to-one conversations have one id for the pair, whoever is "me": dmId(a, b) === dmId(b, a)
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

  // The subjects you can pick: the ones in the timetable the app is using right now
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

  // A message must be a known template with plain-string subject/date/topic/status; anything else is not drawn.
  const isCard = m => m && KINDS[m.type] && m.card && ["subject", "date", "topic", "status"].every(k => typeof m.card[k] === "string");
  const previewOf = m => `${KINDS[m.type].icon} ${KINDS[m.type].title}: ${m.card.subject}`;

  // ---------------------------------------------------------------- storage (uses store.js)
  function seedData() {
    const now = Date.now(), H = 3600 * 1000, D = 24 * H;
    const U = name => DEMO_USERS.find(u => u.name === name).id;      // "Meera" -> "DEMO-CS-003"
    const subjects = subjectList();
    const pick = (name, i) => subjects.includes(name) ? name : (subjects[i % Math.max(subjects.length, 1)] || "Subject");
    const card = (type, who, ago, c, subject, daysAgo, topic, status) => ({
      id: uid(), convo: c, from: U(who), ts: now - ago, type,
      card: { subject: pick(subject, 0), date: localDate(new Date(now - daysAgo * D)), topic, status },
    });
    const zm = dmId(U("Zainab"), U("Meera")), ak = dmId(U("Aarav"), U("Kabir"));
    return {
      version: DATA_VERSION,
      messages: [
        card("shared", "Aarav", D + 3 * H, "class", "Python", 1, "File handling basics", "posted"),
        card("request", "Meera", 1.5 * H, "class", "DAA", 1, "Second half of the lecture", "open"),
        card("doubt", "Kabir", 3 * H, "class", "Web Tech", 0, "Flexbox or grid for a layout", "open"),
        card("shared", "Zainab", 4.5 * H, zm, "Python", 2, "Loops and functions", "posted"),
        card("doubt", "Meera", 0.7 * H, zm, "OOP C++", 0, "When is a constructor called", "open"),
        card("request", "Kabir", 2 * H, ak, "EVS", 3, "Water pollution chapter", "open"),
      ],
      reads: {},
    };
  }

  function isValid(d) { return d && d.version === DATA_VERSION && Array.isArray(d.messages) && d.reads && typeof d.reads === "object"; }

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
  const convoMessages = id => data.messages.filter(m => m.convo === id && isCard(m)).sort((a, b) => a.ts - b.ts || (a.id < b.id ? -1 : 1));
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
      .concat(USERS.filter(u => u !== me).map(u => ({ id: dmId(me, u), title: nameOf(u) })));
    items.forEach(c => {
      const msgs = convoMessages(c.id), last = msgs[msgs.length - 1], unread = unreadCount(c.id);
      // in the group show who sent it; in a one-to-one only mark your own messages
      const who = last && last.from === me ? "You: " : (c.id === "class" && last ? nameOf(last.from) + ": " : "");
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
    ui.title.textContent = convo === "class" ? "Class group" : nameOf(convo.slice(3).split("|").find(u => u !== me));
    ui.subtitle.textContent = (convo === "class" ? "Everyone" : "One-to-one") + " · template messages only";
  }

  function renderMessages(forceBottom) {
    const box = ui.messages;
    const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
    box.replaceChildren();
    const msgs = convoMessages(convo);
    if (!msgs.length) {
      box.append(el("p", { className: "chat-empty", text: "No messages yet. Use one of the templates below to start." }));
      return;
    }
    let prevDay = "";
    msgs.forEach(m => {
      if (dayKey(m.ts) !== prevDay) {
        prevDay = dayKey(m.ts);
        box.append(el("div", { className: "chat-day", text: dayLabel(m.ts) }));
      }
      box.append(renderMessage(m));
    });
    if (forceBottom || nearBottom) box.scrollTop = box.scrollHeight;
  }

  // The card for one template message: Subject / Date / Topic, a status, and (for requests and doubts)
  // an answer button for everyone except the person who sent it.
  function renderCard(m) {
    const k = KINDS[m.type], c = m.card;
    const row = (label, value) => el("div", { className: "chat-req-row" }, el("dt", { text: label }), el("dd", { text: value }));
    const answered = m.type !== "shared" && c.status === k.done;
    const state = k.states[c.status] || c.status;
    const foot = el("div", { className: "chat-req-foot" },
      el("span", { className: "chat-status " + (answered || m.type === "shared" ? "shared" : "open"), text: state }));
    if (answered) {
      foot.append(el("span", { className: "chat-req-by", text: `by ${idLabel(c.handledBy)} at ${timeOf(c.handledAt)}` }));
    } else if (k.action && m.from !== me) {
      const btn = el("button", { type: "button", className: "chat-btn", text: k.action,
        "aria-label": `${k.action}: ${c.subject}, ${prettyDate(c.date)}` });
      btn.addEventListener("click", () => answerCard(m.id));
      foot.append(btn);
    }
    return el("div", { className: "chat-request", role: "group", "aria-label": `${k.title}: ${c.subject}` },
      el("div", { className: "chat-req-title", text: `${k.icon} ${k.title}` }),
      el("dl", { className: "chat-req-list" }, row("Subject", c.subject), row("Date", prettyDate(c.date)), row("Topic", c.topic)),
      foot);
  }

  function renderMessage(m) {
    const mine = m.from === me;
    const avatar = el("span", { className: "chat-avatar", text: nameOf(m.from)[0], "aria-hidden": "true" });
    avatar.style.background = COLORS[m.from] || "#555";
    const head = el("div", { className: "chat-meta" },
      el("span", { className: "chat-from", text: mine ? "You" : idLabel(m.from) }),
      el("time", { text: timeOf(m.ts), datetime: new Date(m.ts).toISOString() }));
    return el("div", { className: "chat-msg" + (mine ? " mine" : "") }, avatar, el("div", { className: "chat-bubble" }, head, renderCard(m)));
  }

  function render(forceBottom) {
    if (ui.who) ui.who.textContent = idLabel(me) + (getSession() && me !== getSession().id ? " (demo switch)" : "");
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
  // "I have these notes" / "I can help": only someone other than the sender, and only while the card is still open
  function answerCard(id) {
    update(d => {
      const m = d.messages.find(x => x.id === id);
      if (m && isCard(m) && KINDS[m.type].done && m.card.status === "open" && m.from !== me) {
        m.card.status = KINDS[m.type].done;
        m.card.handledBy = me;
        m.card.handledAt = Date.now();
      }
    });
    render(false);
  }

  // The form has exactly three inputs: Subject, Date, Topic. Nothing else can be typed into a message.
  function buildDialog() {
    ui.fSubject = el("select", { id: "chat-req-subject", required: "" });
    ui.fDate = el("input", { id: "chat-req-date", type: "date", required: "" });
    ui.fTopic = el("input", { id: "chat-req-topic", type: "text", maxlength: String(MAX_TOPIC), required: "" });
    ui.fTarget = el("p", { className: "chat-req-target" });
    ui.fError = el("p", { className: "chat-req-error", role: "alert" });
    ui.fHeading = el("h4");
    ui.fSend = el("button", { type: "submit", className: "chat-btn primary" });
    const field = (label, input, id) => el("div", { className: "chat-field" }, el("label", { for: id, text: label }), input);
    const cancel = el("button", { type: "button", className: "chat-btn", text: "Cancel" });
    cancel.addEventListener("click", () => ui.dialog.close());
    const form = el("form", { novalidate: "" },
      ui.fHeading, ui.fTarget,
      field("Subject", ui.fSubject, "chat-req-subject"),
      field("Date", ui.fDate, "chat-req-date"),
      field("Topic", ui.fTopic, "chat-req-topic"),
      ui.fError,
      el("div", { className: "chat-dialog-buttons" }, cancel, ui.fSend));
    form.addEventListener("submit", e => { e.preventDefault(); submitCard(); });
    ui.dialog = el("dialog", { className: "chat-dialog", "aria-label": "Message template" }, form);
    ui.dialog.addEventListener("close", () => { if (ui.opener) ui.opener.focus(); });   // focus goes back to the button that opened it
    document.body.append(ui.dialog);
  }

  // type: "request" | "shared" | "doubt". prefill = {subject, date, topic} (all optional). The user always reviews and presses Send.
  function openForm(type, prefill, opener) {
    kind = KINDS[type] ? type : "request";
    const k = KINDS[kind], subjects = subjectList();
    ui.opener = opener || ui.buttons[kind];
    ui.fHeading.textContent = k.open;
    ui.fSend.textContent = k.send;
    ui.fTopic.placeholder = k.placeholder;
    ui.fSubject.replaceChildren(el("option", { value: "", text: subjects.length ? "Choose a subject…" : "No subjects in the timetable" }),
      ...subjects.map(sub => el("option", { value: sub, text: sub })));
    const pre = prefill || {};
    ui.fSubject.value = subjects.includes(pre.subject) ? pre.subject : "";
    ui.fDate.value = validDate(pre.date) ? pre.date : localDate();     // defaults to today
    ui.fTopic.value = cleanTopic(pre.topic);
    ui.fError.textContent = "";
    ui.fTarget.textContent = "Sending to: " + ui.title.textContent;
    ui.dialog.showModal();
    (ui.fSubject.value ? ui.fTopic : ui.fSubject).focus();
  }

  function submitCard() {
    const subject = ui.fSubject.value, date = ui.fDate.value, topic = cleanTopic(ui.fTopic.value);
    let problem = "", field = null;
    if (!subjectList().includes(subject)) { problem = "Choose a subject."; field = ui.fSubject; }
    else if (!validDate(date)) { problem = "Choose a valid date."; field = ui.fDate; }
    else if (!topic) { problem = "Write a short topic."; field = ui.fTopic; }
    if (problem) { ui.fError.textContent = problem; field.focus(); return; }
    const status = kind === "shared" ? "posted" : "open";
    update(d => d.messages.push({ id: uid(), convo, from: me, ts: Date.now(), type: kind, card: { subject, date, topic, status } }));
    ui.dialog.close();
    render(true);
  }

  // DEMO ONLY: chat as another demo account in this tab (for the two-tab demo). "" goes back to the login ID.
  function switchUser(id) {
    try {
      if (USERS.includes(id)) sessionStorage.setItem(ME_KEY, id);
      else sessionStorage.removeItem(ME_KEY);
    } catch (e) { /* private mode: just not remembered */ }
    me = currentIdentity();
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
  function build() {
    const select = el("select", { id: "chat-as" },
      el("option", { value: "", text: "My login" }),
      ...USERS.map(u => el("option", { value: u, text: idLabel(u) })));
    select.addEventListener("change", () => switchUser(select.value));
    ui.as = select;
    ui.who = el("strong", { id: "chat-me" });

    ui.reset = el("button", { type: "button", className: "chat-btn", text: "Reset chat" });
    ui.reset.addEventListener("click", resetChat);

    const topbar = el("div", { className: "chat-topbar" },
      el("span", { className: "chat-who" }, "Chatting as ", ui.who),
      el("span", { className: "chat-demo", text: "Demo accounts with placeholder college IDs, simulated in this browser, no server sync." }),
      ui.reset,
      el("details", { className: "chat-demo-switch" },
        el("summary", { text: "Demo only: chat as another demo account (for the two-tab demo)" }),
        el("label", { for: "chat-as", text: "Chat as " }), select));

    ui.list = el("ul", { className: "chat-convos", "aria-label": "Conversations" });
    ui.title = el("h3", { className: "chat-title" });
    ui.subtitle = el("span", { className: "chat-subtitle" });
    ui.messages = el("div", { className: "chat-messages", role: "log", "aria-live": "polite", "aria-label": "Messages", tabindex: "0" });

    // No text box: three template buttons are the only way to send a message
    ui.buttons = {};
    const actions = el("div", { className: "chat-actions" }, el("span", { className: "chat-actions-label", text: "Send a message from a template:" }));
    Object.keys(KINDS).forEach(type => {
      const btn = el("button", { type: "button", className: "chat-btn primary", id: "chat-new-" + type, text: `${KINDS[type].icon} ${KINDS[type].open}` });
      btn.addEventListener("click", () => openForm(type, null, btn));
      ui.buttons[type] = btn;
      actions.append(btn);
    });
    actions.append(el("span", { className: "chat-hint", text: "Each template has only Subject, Date and Topic, so the chat stays on topic." }));
    buildDialog();

    const pane = el("div", { className: "chat-pane" },
      el("div", { className: "chat-pane-head" }, el("div", {}, ui.title, ui.subtitle)),
      ui.messages, actions);

    ui.section = el("section", { id: "chat", className: "tab hidden" },
      el("h3", { text: "Chat" }), topbar, el("div", { className: "chat-shell" }, ui.list, pane));
    document.getElementById("dashboard").append(ui.section);

    const navBtn = el("button", { type: "button", text: "💬 Chat" });
    navBtn.addEventListener("click", () => window.showTab("chat"));
    document.querySelector(".tab-nav").append(navBtn);
  }

  // Vision's "Request notes" link opens /campus/?chat=request&subject=..&date=..&topic=..
  // The app shows its login first, so remember the values and open the (pre-filled) form right after login.
  function readPrefill() {
    const q = new URLSearchParams(location.search);
    return q.get("chat") === "request" ? { subject: q.get("subject") || "", date: q.get("date") || "", topic: q.get("topic") || "" } : null;
  }

  function init() {
    me = currentIdentity();
    data = load(true);
    document.head.append(el("link", { rel: "stylesheet", href: "chat.css" }));
    build();
    render(true);

    // another tab changed the chat -> show it (this is what keeps two tabs in sync)
    window.addEventListener("storage", e => {
      if (e.key !== null && e.key !== STORE_KEYS.chat) return;
      data = load(false);
      render(false);
    });
    document.addEventListener("visibilitychange", () => { if (chatShown()) render(true); });

    // wrap login from app.js: the college ID that just logged in is the chat identity, and if we arrived from
    // Vision, open the Chat tab with the request form pre-filled (the user reviews it and presses Send).
    let pending = readPrefill();
    const originalLogin = window.login;
    window.login = function () {
      originalLogin();
      if (!document.getElementById("dashboard").classList.contains("hidden")) {
        me = currentIdentity();
        render(true);
      }
      if (pending && !document.getElementById("dashboard").classList.contains("hidden")) {
        const prefill = pending;
        pending = null;
        history.replaceState(null, "", location.pathname);   // so a reload does not open the form again
        window.showTab("chat");
        openConvo("class");
        openForm("request", prefill, ui.buttons.request);
      }
    };

    // wrap showTab from app.js: when the Chat tab opens, scroll to the newest message and mark it read
    const originalShowTab = window.showTab;
    window.showTab = function (id) {
      originalShowTab(id);
      if (id === "chat") render(true);
    };
  }

  init();
})();

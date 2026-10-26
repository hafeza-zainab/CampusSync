// "Import from screenshot" tab of the CampusSync app.
//
// It shows the Vision page (the screenshot reader) inside the app, so Vision feels like part of the product.
// Vision lives at the server root ("../" from /campus/). It saves its results into the same localStorage
// keys the app already reads (timetable, announcements, study), and the app picks the changes up through
// the browser's "storage" event (see the listener at the bottom of app.js), so nothing needs a page reload.
//
// Like chat.js, this file builds its own nav button and tab section; index.html only loads the script.
(function () {
  "use strict";

  let frame = null;

  function build() {
    const css = document.createElement("link");           // gives the frame a real size (see import.css)
    css.rel = "stylesheet";
    css.href = "import.css";
    document.head.append(css);

    frame = document.createElement("iframe");
    frame.id = "importFrame";
    frame.title = "CampusSync Vision: import from a screenshot";
    // not loaded until the tab is opened first, so the OCR page does not start with the app

    const intro = document.createElement("p");
    intro.className = "import-intro";
    intro.textContent = "Upload a timetable screenshot, a notice or a PDF. Vision reads it and shows what it found. " +
      "A timetable goes to the Calendar after you confirm, notices go to Announcements, and every entry is added to the Study Panel.";

    const open = document.createElement("a");
    open.href = "../";
    open.target = "_blank";
    open.rel = "noopener";
    open.textContent = "Open Vision in its own tab ↗";

    const section = document.createElement("section");
    section.id = "import";
    section.className = "tab hidden";
    const title = document.createElement("h3");
    title.textContent = "Import from screenshot";
    section.append(title, intro, open, frame);
    document.getElementById("dashboard").append(section);

    const nav = document.createElement("button");
    nav.type = "button";
    nav.textContent = "📷 Import from screenshot";
    nav.addEventListener("click", () => window.showTab("import"));
    document.querySelector(".tab-nav").append(nav);
  }

  build();

  // the embedded Vision page reports how tall it is; the frame grows to fit, so the app page scrolls (not a box inside it)
  window.addEventListener("message", e => {
    if (e.origin !== location.origin || !e.data || typeof e.data.visionHeight !== "number") return;
    frame.style.height = Math.max(640, Math.min(Math.ceil(e.data.visionHeight) + 4, 5000)) + "px";
  });

  // load the Vision page the first time the tab is opened (?embedded=1 hides its own header and shows no back link)
  const originalShowTab = window.showTab;
  window.showTab = function (id) {
    originalShowTab(id);
    if (id === "import" && !frame.getAttribute("src")) frame.setAttribute("src", "../?embedded=1");
  };
})();

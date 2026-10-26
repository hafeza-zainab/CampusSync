// "Import from screenshot" inside the Study Panel tab (it is not a tab of its own).
//
// A collapsible card at the top of the Study Panel shows the Vision page (the screenshot reader) in an iframe.
// Vision lives at the server root ("../" from /campus/). It saves its results into the same localStorage
// keys the app already reads (timetable, announcements, study), and the app picks the changes up through
// the browser's "storage" event (see the listener at the bottom of app.js), so nothing needs a page reload.
//
// Like chat.js, this file builds its own content; index.html only loads the script.
(function () {
  "use strict";

  const study = document.getElementById("study");
  if (!study) return;

  const css = document.createElement("link");           // card look + a real size for the frame (see import.css)
  css.rel = "stylesheet";
  css.href = "import.css";
  document.head.append(css);

  const frame = document.createElement("iframe");
  frame.id = "importFrame";
  frame.title = "CampusSync Vision: import from a screenshot";
  // not loaded until the card is opened, so the OCR page does not start with the app

  const intro = document.createElement("p");
  intro.className = "import-intro";
  intro.textContent = "Upload a timetable screenshot, a notice or a PDF. Vision reads it and shows what it found. " +
    "A timetable goes to the Calendar after you confirm, notices go to Announcements, and every entry is added to the Study Panel below.";

  const details = document.createElement("details");
  details.id = "import";
  details.className = "import-card";
  const summary = document.createElement("summary");
  summary.textContent = "📷 Import from screenshot";
  details.append(summary, intro, frame);
  study.insertBefore(details, study.querySelector("h3").nextSibling);

  details.addEventListener("toggle", () => {
    if (details.open && !frame.getAttribute("src")) frame.setAttribute("src", "../?embedded=1");   // hides Vision's own header
  });

  // the embedded Vision page reports how tall it is; the frame grows to fit, so the app page scrolls (not a box inside it)
  window.addEventListener("message", e => {
    if (e.origin !== location.origin || !e.data || typeof e.data.visionHeight !== "number") return;
    frame.style.height = Math.max(520, Math.min(Math.ceil(e.data.visionHeight) + 4, 5000)) + "px";
  });
})();

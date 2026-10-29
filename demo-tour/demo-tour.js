// demo-tour.js: a small, dependency-free "watch the app use itself" demo tour.
//
// It drives the REAL page: each step runs an action (click, type, choose, or your own code) while a caption bar
// explains what is happening. There is a Stop button, and your seed() / reset() hooks run before and after.
//
//   const tour = DemoTour.create({
//     steps: [
//       { caption: "Type a task", action: async t => { await t.type("new-item", "Buy milk"); }, wait: 600 },
//       { caption: "Add it",      action: async t => { await t.click("add"); },                 wait: 900 }
//     ],
//     seed:  () => { /* put sample data in place */ },
//     reset: () => { /* remove everything the tour added; runs on finish, Stop and error */ },
//     pace: 1                      // 1 = as written; 2 = every pause twice as long; 0.1 = ten times faster (tests)
//   });
//   document.querySelector("[data-tour=start]").addEventListener("click", () => tour.start());
//
// Selectors: a plain word such as "add" means [data-tour="add"]. Anything else ("#id", ".class", "ul > li") is a CSS selector.
// A step can be a bare caption (no action): it just shows the text for `wait` ms.
// Not included (CampusSync's tour.js has it): continuing across a page reload.
(function (root) {
  "use strict";

  const CSS = `
#demoTourBar{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:2147483647;width:min(720px,calc(100% - 24px));
  box-sizing:border-box;background:#1f2740;color:#fff;border-radius:10px;padding:10px 14px;font:600 15px system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.35)}
#demoTourBar .dt-row{display:flex;align-items:center;gap:12px}
#demoTourBar .dt-text{flex:1}
#demoTourBar .dt-count{font-weight:400;color:#aab4d4;font-size:13px}
#demoTourBar button{background:#e74c3c;border:0;color:#fff;border-radius:6px;padding:4px 12px;font:inherit;cursor:pointer}
.demo-tour-focus{outline:4px solid #ffb703!important;outline-offset:3px;box-shadow:0 0 0 8px rgba(255,183,3,.25)!important}`;

  const STOPPED = "demo-tour: stopped";

  function create(options) {
    const steps = options.steps || [];
    const pace = typeof options.pace === "number" ? options.pace : 1;
    const seed = options.seed || (() => {});
    const reset = options.reset || (() => {});
    let running = false, aborted = false, bar = null;

    const sleep = ms => new Promise(r => setTimeout(r, ms));
    async function wait(ms) {                      // sleeps in small slices so Stop is noticed quickly
      const end = Date.now() + ms * pace;
      while (Date.now() < end) { if (aborted) throw new Error(STOPPED); await sleep(Math.min(40, Math.max(end - Date.now(), 0))); }
      if (aborted) throw new Error(STOPPED);
    }

    function find(sel) {
      if (sel && sel.nodeType === 1) return sel;
      const css = /^[\w-]+$/.test(sel) ? `[data-tour="${sel}"]` : sel;
      const node = document.querySelector(css);
      if (!node) throw new Error(`demo-tour: no element for "${sel}" (looked for ${css})`);
      return node;
    }
    async function focus(sel, ms) {
      const node = find(sel);
      node.scrollIntoView({ block: "center", behavior: "smooth" });
      node.classList.add("demo-tour-focus");
      await wait(ms === undefined ? 400 : ms);
      return node;
    }
    const unfocus = node => node.classList.remove("demo-tour-focus");

    // the helpers every action receives; they call the page's real elements, exactly as a user would
    const t = {
      sleep: wait,
      el: find,
      focus: async (sel, ms) => { unfocus(await focus(sel, ms)); },
      async click(sel, ms) { const n = await focus(sel, ms); n.click(); unfocus(n); },
      async type(sel, text, perChar) {
        const n = await focus(sel, 250);
        n.focus(); n.value = "";
        for (const ch of text) { n.value += ch; n.dispatchEvent(new Event("input", { bubbles: true })); await wait(perChar || 45); }
        unfocus(n);
      },
      choose(sel, value) {                          // <select>: set the value and fire the event the page listens for
        const n = find(sel); n.value = value; n.dispatchEvent(new Event("change", { bubbles: true }));
      }
    };

    function showBar() {
      if (!document.getElementById("demoTourStyle")) {
        const st = document.createElement("style"); st.id = "demoTourStyle"; st.textContent = CSS; document.head.append(st);
      }
      bar = document.createElement("div");
      bar.id = "demoTourBar"; bar.setAttribute("role", "status"); bar.setAttribute("aria-live", "polite");
      const row = document.createElement("div"); row.className = "dt-row";
      const text = document.createElement("span"); text.className = "dt-text";
      const count = document.createElement("span"); count.className = "dt-count";
      const stop = document.createElement("button"); stop.type = "button"; stop.textContent = "Stop demo"; stop.id = "demoTourStop";
      stop.addEventListener("click", () => { aborted = true; });
      row.append(text, count, stop); bar.append(row); document.body.append(bar);
      bar._text = text; bar._count = count;
    }
    const say = (msg, n) => { bar._text.textContent = msg; bar._count.textContent = n ? `${n}/${steps.length}` : ""; };

    async function start() {
      if (running) return false;                    // a second click while running does nothing
      running = true; aborted = false;
      let error = null;
      showBar();
      try {
        await seed();
        for (let i = 0; i < steps.length; i++) {
          const s = steps[i];
          say(s.caption || "", i + 1);
          if (s.action) await s.action(t);
          await wait(s.wait === undefined ? 800 : s.wait);
        }
      } catch (e) {
        if (e.message !== STOPPED) error = e;
      }
      try { await reset(); } catch (e) { error = error || e; }   // always runs: finish, Stop or error
      if (error) { console.warn(error); say("Demo stopped: " + error.message); await sleep(2500); }
      bar.remove(); bar = null; running = false;
      if (options.onEnd) options.onEnd(error);
      return !error;
    }

    return { start, stop: () => { aborted = true; }, get running() { return running; } };
  }

  root.DemoTour = { create };
})(window);

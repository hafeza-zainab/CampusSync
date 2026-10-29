# How the "▶ Run 60-second demo" button works

Written for the person who built CampusSync and wants to understand her own demo button again. Everything below comes from reading the code on `main` at commit `31efc25`, plus two runs in a headless browser (listed at the end, with what was *not* checked).

**The short version.** The button does not play a video. `tour.js` is a script that *uses the real app*: it types into the real login box, clicks real buttons, calls the real `showTab()` function, and shows a caption bar on top. It reloads the page halfway to log in as a second person. When it ends, it deletes what it added and reloads again.

## The files involved

| File | Job in the demo |
|---|---|
| [index.html](../index.html) | Has the two buttons `#tourStart` ("▶ Run 60-second demo") and `#resetDemo` ("↺ Reset demo data") on the login box (lines 18 and 19). Loads the scripts in this order (lines 91 to 98): `store.js`, `data.js`, `app.js`, `demo.js`, `chat.js`, `import.js`, `study.js`, `tour.js`. |
| [tour.js](../tour.js) | The tour itself: the caption bar, the clicking and typing, the timing, the cleanup. |
| [demo.js](../demo.js) | Fills the app with believable data for the four demo accounts when the page loads. Also handles the "Reset demo data" button. |
| [store.js](../store.js) | `loadStore` / `saveStore` (localStorage), the four demo accounts (`DEMO_USERS`), the session helpers. The tour and `demo.js` both use them. |
| [app.js](../app.js) | The real app: `login()`, `showTab()`, the calendar, `openAttendanceMenu()`, `postAnnouncement()`. The tour calls into these. |
| [study.js](../study.js), [chat.js](../chat.js) | The Study Panel form and the Chat request form that the tour fills in. Both also *wrap* `window.showTab` so their tab refreshes when opened. |
| [import.js](../import.js) | Builds the "📷 Import from screenshot" card. The tour opens it. |
| [style.css](../style.css) | Lines 251 to 262: the look of the caption bar (`#tourBar`) and the yellow highlight (`.tour-focus`). |
| [vision/main.py](../vision/main.py) | The server. Line 110 is the list of files it is allowed to send (`CAMPUS_FILES`), which includes `demo.js` and `tour.js`. |

**Not the same thing:** the Vision page ([vision/static/index.html](../vision/static/index.html)) has its own button, `▶ Run demo` (`id="demo"`, line 110; handler at line 184). That one uploads a sample picture to the server. The campus tour never presses it. More on this at the end.

---

## What happens, in order

### 0. Before any click: the page loads

1. The browser asks the server for `/campus/`. `main.py` answers with `index.html` only for names in `CAMPUS_FILES`; any other file name gets a 404.
2. The scripts run top to bottom. `app.js` defines the app. Then **`demo.js` runs** and seeds data (see "How data is seeded and reset"). Later, **`tour.js` runs last** and does two things in its `init()` (line 222):
   - If the `#tourStart` button exists, attach a click handler to it.
   - Look in `sessionStorage` under the key `campussync.tour`. If it says `part: 2`, the page was reloaded in the middle of a tour, so continue with part 2 (step 12 below). If it says anything else, it is the leftover of an interrupted run: delete it and do nothing.

### 1. The click

The handler (`tour.js` lines 224 to 229):

```js
const start = Date.now();
setState({ start, part: 1 });   // sessionStorage "campussync.tour" = {"start": ..., "part": 1}
btn.disabled = true;
run(1, start);
```

`run()` calls `showBar(start)` (the caption bar) and then `partOne(start)`.

### 2. The caption bar appears

`showBar()` (line 31) builds a `<div id="tourBar">` entirely with `document.createElement` and appends it to `document.body`. It contains:

- `.tour-text`: the caption. `say("...")` just sets this element's `textContent`.
- `.tour-time`: shows "12 / 60 s".
- A **Stop demo** button. Its whole job is `aborted = true`.
- A thin progress strip (`.tour-track` / `.tour-fill`).

A `setInterval` every 250 ms fills the strip and the clock from `Date.now() - start`, capped at `TOTAL_MS = 60000`. The clock uses the real elapsed time, and `start` is stored in `sessionStorage`, so the clock keeps counting across the mid-tour reload.

The bar is styled in `style.css`: `position: fixed`, bottom centre, `z-index: 100000`, with `role="status"` set in JS.

### 3. How every step is timed

All timing goes through one function (`tour.js` line 22):

```js
async function wait(ms) {
  const end = Date.now() + ms * PACE;                 // PACE = 1.25
  while (Date.now() < end) { if (aborted) throw new Error("stopped"); await sleep(50); }
  if (aborted) throw new Error("stopped");
}
```

- Every pause you see is a `wait()`, **multiplied by `PACE` (1.25)**. The comment says this stretches the tour to fill about 60 seconds.
- It sleeps in 50 ms slices and checks `aborted` each time. That is why the Stop button reacts almost immediately: pressing it makes the *next* slice throw `Error("stopped")`.
- There is no global schedule. The tour is a plain top-to-bottom `async` function; each line waits for the previous one. The "60 seconds" is the sum of the pauses, not an enforced limit. **Measured on this machine: 62.7 s** from click to the page reloading at the end (caption 13 appeared at 57.5 s). The bar therefore sits at "60 / 60 s" for the last few seconds.

### 4. How it drives the real UI (functions or events?)

Both, depending on the action. It never fakes pixels or moves a mouse; it calls the page's own code:

| Action | How `tour.js` does it | What the app sees |
|---|---|---|
| Click | `node.click()` (`click()`, line 63) | A normal `click` event, so the element's `onclick` runs. Lecture boxes (`l.onclick = ...` in `app.js`) and the buttons with `onclick="login()"` work this way. |
| Type | `type()` (line 68): focus, set `input.value` one character at a time (every 35 to 55 ms), and after each character dispatch `new Event("input", { bubbles: true })` | Looks like typing to any `input` listener. |
| Choose from a `<select>` | `choose()` (line 79): set `select.value`, dispatch `change`. If the wanted value is not in the list, it falls back to the first non-empty option. | The page's `change` listener. |
| Submit a form | `form.requestSubmit()` for the Study Panel form (`.study-form`) and the Chat request form | The `submit` event, so `addMaterial` (`study.js`) and the chat form handler run, validation included. |
| Change tab | **A direct function call**: `window.showTab("attendance")` (line 84). The tab buttons are *not* clicked. | The same `showTab` the buttons call, including the versions `chat.js` and `study.js` wrap. |
| Open the Import card | `$("import").open = true` (line 185) | The `<details>` fires its `toggle` event, and `import.js` (line 38) then sets the iframe's `src` to `../vision?embedded=1`. |
| Set a date | `$("study-date").value = todayIso()` | Just sets the value; no event is fired. |

Before each click or typing, `focusOn(node)` runs: it scrolls the element to the middle of the screen (smooth), adds the class `tour-focus` (yellow outline from `style.css`) and waits. After the action it removes the class.

Because `node.click()` creates an **untrusted** event (`isTrusted === false`), this only works because CampusSync's handlers do not check that. It is a useful limit to know.

### 5. Part 1: the CR (`partOne`, line 117)

Numbers match the captions on screen. Waits are before the 1.25 stretch.

1. **Login.** Caption "1/8 Login...". `loginAs("DEMO-CS-001", "cr-demo")` types into `#username` and `#password` and clicks `.login-container > button` (the first button directly inside the login box, which is "Enter"). This calls the real `login()`, which checks `DEMO_USERS`.
2. **Calendar.** Clicks the calendar's previous-month button, then next-month. Buttons are found by position: `document.querySelector(".calendar-header button")` (first) and `document.querySelectorAll(".calendar-header button")[1]` (second).
3. **Semester 6 not started.** Clicks "next" three times, pauses, clicks "previous" three times. This assumes that three months ahead shows a semester that has not started; that depends on today's date and the semester dates in `data.js`.
4. **Mark attendance.** First it **saves a copy of the CR's attendance** (`sessionStorage["campussync.tour.att"] = JSON.stringify(attendance)`). Then `pastLectures()` collects calendar lectures whose `style.cursor === "pointer"` (a finished lecture; `app.js` line 159), picks the last one, clicks it (this opens the attendance menu), clicks `.attend-menu .attend-absent`, scrolls to `#statsPanel`, then changes it back to Present the same way. If no finished lecture exists the whole step is skipped without a message.
5. **Attendance tab.** `showTab("attendance")`, highlight `#attendanceList`.
6. **Announcements.** `showTab("announcements")`, types `"Class test on Friday: DBMS Unit 2. Revise normalization! (demo)"` into `#msg`, clicks the Post button (`.announce-input button`, which calls `postAnnouncement()`).
7. **Study Panel.** Chooses `sem5` and `DBMS`, types "Normalization notes (demo)", sets today's date, `requestSubmit()` on `.study-form`.
8. **Chat.** `showTab("chat")`, clicks `#chat-new-request`, picks DBMS, types "Unit 2 notes (demo)", `requestSubmit()` on the form.
9. **Vision caption.** `showTab("study")`, opens the `#import` card and highlights it for 2.3 s. **It does not upload anything**; the caption describes what Vision can do.
10. **Hand-over.** Puts the saved attendance back (`saveStore("attendance", att, "DEMO-CS-001")`), sets `{ start, part: 2 }` in `sessionStorage`, and calls `location.reload()`.

### 6. The reload: why it exists

A reload throws away all in-memory state (`currentUser`, the rendered calendar), so the app is back at the login screen without a logout step. That is the only reason for it; `sessionStorage` survives a reload, so the tour finds out it is in the middle of a run by reading `campussync.tour` in `init()`.

### 7. Part 2: a student (`partTwo`, line 197)

After the reload `init()` sees `part: 2` and calls `run(2, s.start)`. It shows the bar again (the clock continues from the original `start`), logs in as `DEMO-CS-003` / `student-demo`, opens Announcements, points at `#announceNote` (the "Only the CR and ACR can post" note, which `login()` shows instead of the input box), and ends with the closing caption.

### 8. How it ends

`run()` (line 211) wraps everything in `try/catch`. After part 2 finishes it calls `finish()`:

```js
function finish() {
  const att = attendanceBackup();                    // the saved copy of the CR's attendance
  sessionStorage.removeItem(KEY); sessionStorage.removeItem(KEY + ".att");
  cleanup(att);                                      // remove "(demo)" items, restore attendance
  location.reload();                                 // back to the login screen
}
```

`cleanup()` (line 96) filters out every announcement whose `msg` contains `(demo)`, every study item whose `topic` contains `(demo)`, and every chat card whose `topic` contains `(demo)`, then writes the CR's saved attendance back.

**Stop button:** sets `aborted`; the next `wait()` throws `Error("stopped")`; `run()`'s `catch` ignores that particular message and calls `finish()`. So Stop and "finished" take the same exit.

**Any other error** (for example `tour: element not found` thrown by `focusOn`) is `console.warn`-ed and then also goes to `finish()`.

---

## How data is seeded and reset

**Seeding is `demo.js`, not the tour.** It runs when the page loads, before anyone clicks anything.

- It gives each of the four accounts a different attendance history, built from `PROFILES` (for example, Meera `DEMO-CS-003` misses 30 percent of lectures, Aarav `DEMO-CS-002` misses 42 percent of DBMS). It reads the semesters and timetable from `data.js` and writes with `saveStore("attendance", marks, id)`.
- It adds 4 announcements and 6 study items, but **only if those lists are empty**.
- It then sets a flag, `localStorage["campussync.demoseed.v2"]`, so **it never runs again in that browser**. The first line after the `resetDemo` listener is `if (localStorage.getItem(FLAG)) return;`.
- It also means a changed `PROFILES` does nothing in a browser that already has the flag.

**"↺ Reset demo data"** is handled in `demo.js` (line 13) by a click listener on the whole document that watches for `id === "resetDemo"`. It removes the flag, the announcements and the study list from localStorage, then reloads; on the reload the seeding above runs again. It does *not* clear chat data, the saved timetable, or the login.

**The tour's own data** is deliberately small and recognisable: the three things it types all end with `(demo)`, and the CR's attendance is saved first and restored after. `cleanup()` is the tour's reset.

---

## How it can fail

### Nothing happens when you click the button (the stale-server problem)

`main.py` builds `CAMPUS_FILES` once, when the server process starts. If a server that was started **before** `demo.js` / `tour.js` were added to that list is still running (or an old server is still holding port 8000 so your new one could not start), then:

1. The browser asks for `/campus/tour.js`.
2. The server answers 404 (`if name not in CAMPUS_FILES: raise HTTPException(404)`).
3. The `<script src="tour.js">` fails quietly. No error on the page.
4. `#tourStart` never got a click handler, so the button looks alive and does nothing.

The same thing happens to a brand-new file you add and forget to list. The `Cache-Control: no-cache` header only affects *files*; the list itself is Python memory, so **editing `main.py` needs a server restart**. How to check: open the browser dev tools, Network tab, and look for a red `tour.js` or `demo.js`; or open `http://localhost:8000/campus/tour.js` directly.

*(Reasoned from the code; I did not start the real server for this documentation.)*

### localStorage / sessionStorage problems

- **Storage blocked** (some private modes, strict settings): `demo.js` bails out (`catch` returns), so there is no seed data; the tour's `setState` silently fails, so after the mid-tour reload `init()` finds no state and **part 2 never runs**: the tour stops at the login screen after part 1.
- **The seed flag is already set**: seeded data is not refreshed. Use "Reset demo data".
- **Old data from earlier testing**: the seed only fills announcements / study if they are empty, so earlier test posts stay and the screen differs from the intended demo. "Reset demo data" clears them first.
- **Dates:** the seed marks attendance relative to the day you first loaded the page, and the tour's steps 3 and 4 depend on the calendar for today. A stale browser profile or a changed system date can make the screen not match the caption.
- **One tab:** the tour state is in `sessionStorage`, which belongs to a single tab. Opening the page in a second tab and pressing the button there is a separate run.

### Interrupted runs (closing the tab or reloading the page mid-tour)

Tested: I started the tour, waited until caption "8/8" (by then the announcement and study item had been posted), then did one of two things.

| What I did | Left behind afterwards |
|---|---|
| Pressed **Stop demo** | Nothing. 0 `(demo)` announcements, 0 `(demo)` study items; login screen. |
| **Reloaded the page** (same for closing the tab, then reopening) | **1 `(demo)` announcement and 1 `(demo)` study item stayed in localStorage.** The login screen came back, and the tour state was gone. (I did not count the chat card.) |

Why: the cleanup is only called from `finish()`. A reload mid-tour does not go through `finish()`; on the next load `init()` sees `part: 1`, deletes the `campussync.tour` key ("an interrupted run: forget it", line 232) and does not call `cleanup()`. The leftovers show up as extra "(demo)" posts the next time someone logs in. Two further consequences, from reading the code and not tested: the saved copy of the attendance (`campussync.tour.att`) is also left in `sessionStorage`, and if the interruption lands during the few seconds of step 4 (when one lecture is temporarily Absent) that mark stays Absent. "Reset demo data" removes the leftover announcements and study items.

### Popups and dialogs

- The app uses no `alert()`, `confirm()` or `prompt()` (the only mentions are in comments: `app.js` line 306, `chat.js` line 345), so a browser dialog will not freeze the tour.
- The "popup" the tour does depend on is the attendance menu, a plain `<div class="attend-menu">` that `openAttendanceMenu()` appends to `document.body`. Step 4 looks for `.attend-menu .attend-absent` straight after the click; if the menu is not there, the step throws, and the whole tour ends (see next point).
- No `window.open`, so popup blockers are not involved.

### Missing elements end the tour silently

If any selector finds nothing, `focusOn` throws `tour: element not found`; `run()` writes it to the browser console with `console.warn` and calls `finish()`. What the viewer sees is the caption bar disappearing and the page reloading to the login screen. Typical causes: an id or class renamed in `index.html` / `app.js`, or a different layout. The position-based selectors (`.calendar-header button`, `[1]`) are the most likely to drift.

### The iframe

Step 9 opens the Import card, which asks the server for `/vision?embedded=1`. If the server is not the CampusSync server (for example you open `index.html` straight from disk or from a plain static server) that frame shows an error page. The tour does not care, and carries on.

---

## The Vision page's own "Run demo" button, for contrast

This is a *different mechanism* in a different file (`vision/static/index.html`):

| | Campus tour (`tour.js`) | Vision "Run demo" |
|---|---|---|
| Starts from | `#tourStart` on the login screen | `#demo` button on the Vision page (line 110) |
| How it works | A script that clicks and types in the page | The button's handler (line 184) picks a catalog course, then **fetches `/samples/timetable.png` from the server and calls the page's own `run(file, true)`** with it. That sends the picture to `POST /api/analyze`: real OpenCV and OCR run. |
| Caption | Its own `#tourBar`, created in JS | The page's built-in `#caption` element; `caption(text, sub)` rewrites its text for the steps 1 to 6 |
| Timing | `wait()` pauses with `PACE` | `await sleep(...)`, e.g. 1500 ms after showing the upload when `demo` is true, plus however long the server takes, plus the box-drawing delays |
| Needs the server | Only for the files (and the Vision iframe) | Yes: `/samples`, `/api/analyze`, `/api/catalog`, `/api/entries` |
| Side effect | Cleans up after itself | `/api/analyze` saves entries into `vision/data/entries.json` on the server and the page writes the Study Panel items into localStorage; "Reset panel" (`DELETE /api/entries`) clears the server copy |

Because the tour never presses Vision's button, the campus tour does not exercise Vision at all.

---

## What was checked, and what was not

Checked:

- Read all of `tour.js`, `demo.js`, `import.js`, `vision/main.py`, the relevant parts of `index.html`, `app.js`, `store.js`, and the Vision page's script.
- Ran the real `tour.js` and `demo.js` in headless Chromium (Playwright) against a plain static file server (not `main.py`). The tour ran to the end with no page errors, took **62.7 s**, showed the 13 captions in the order listed above, ended on the login screen, and left no `(demo)` announcements behind.
- The interrupted-run result above.

Not checked:

- The real FastAPI server (OCR dependencies not started). That means the stale-server 404, the iframe loading `/vision`, and the Vision "Run demo" button are described from the code, not observed.
- What the screen looked like at each step (the run checked captions, errors and cleanup, not screenshots). In particular I did not confirm that step 3 lands on a not-started semester today.
- Other browsers, a slower computer, blocked storage.

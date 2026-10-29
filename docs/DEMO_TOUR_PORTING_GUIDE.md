# Porting the demo-tour method to another web project

A checklist for reusing the "the app demos itself" button. Read [DEMO_BUTTON_EXPLAINED.md](DEMO_BUTTON_EXPLAINED.md) first; this guide assumes you know what `tour.js` and `demo.js` do.

**Two ways to reuse it**

| | What you do | When to pick it |
|---|---|---|
| A. Use the generic file | Copy [demo-tour/demo-tour.js](../demo-tour/demo-tour.js), write a `steps` array, add `data-tour` attributes | A new project, or any project where the tour is one page with no reload in the middle |
| B. Copy CampusSync's `tour.js` and edit it | Copy `tour.js` + the CSS block, replace the steps in `partOne` / `partTwo` | You need the reload-in-the-middle behaviour (log in as a second user), or a progress bar |

`demo-tour.js` is a rewrite of the *idea*, not a pull-out of `tour.js`. It has no CampusSync names in it, but it also lacks two things `tour.js` has (see "What the generic file does not do").

---

## 1. What to copy

For route A:

- [ ] `demo-tour/demo-tour.js` (the only file you need; it injects its own CSS).
- [ ] Read `demo-tour/example.html`: it is the smallest complete use, about 70 lines.

For route B:

- [ ] `tour.js` (235 lines).
- [ ] The tour CSS block in `style.css` (lines 251 to 262: `.tour-start`, `#tourBar` and its parts, `.tour-focus`).
- [ ] The two buttons from `index.html` (`#tourStart`, `#resetDemo`) and the `<script>` tag for `tour.js`, loaded **last**.
- [ ] `demo.js` if you also want seeded accounts / data.

## 2. What to change

Route A:

- [ ] Write `steps`: each is `{ caption, action, wait }`. `action` is optional, `wait` defaults to 800 ms.
- [ ] Write `seed()` and `reset()` (section 4).
- [ ] Wire your own start button to `tour.start()`.

Route B (everything in `tour.js` that names CampusSync):

- [ ] `KEY` (`"campussync.tour"`) and `TAG` (`"(demo)"`).
- [ ] `TOTAL_MS` and the `"/ 60 s"` text: they are the "60-second" promise. If the tour takes longer, the bar sits at full. (Measured here: 62.7 s against a 60 s bar.)
- [ ] `PACE` (1.25) is a fudge factor used to stretch the pauses to fit 60 s; set it to 1 and re-time.
- [ ] Every selector and `$("id")` in `partOne` / `partTwo`.
- [ ] `cleanup()`: it knows CampusSync's storage names (`announcements`, `study`, `chat`, `attendance`).
- [ ] `loginAs()` and the demo account IDs / passwords.
- [ ] The `window.showTab(...)` calls: your app's way of changing view.

## 3. What the other project needs

**Stable selectors.** The tour finds things by looking them up, so a renamed class silently breaks it.

- [ ] Add `data-tour="..."` attributes to everything the tour touches, and use only those. CampusSync's `tour.js` does *not* do this: it uses ids (`#username`, `#msg`) and structural selectors (`.login-container > button`, `document.querySelectorAll(".calendar-header button")[1]`). That works until someone adds a button to the calendar header. With `data-tour`, a designer can restyle freely and the attribute name tells the next person "a demo depends on this".
- [ ] Items in lists need their own hooks, or the tour must compute them (the example uses `data-tour="item-<index>"`).
- [ ] Do not target by visible text unless the text is fixed.

**Actions that go through the real handlers.**

- [ ] Clicks: `element.click()` runs the page's `onclick` and `addEventListener("click")` handlers.
- [ ] Typing: set `.value`, then dispatch an `input` event with `bubbles: true` (frameworks listen for it; setting `.value` alone changes nothing they can see). With React-controlled inputs this may not be enough; test it.
- [ ] Selects: set `.value`, dispatch `change`.
- [ ] Forms: `form.requestSubmit()` (not `.submit()`, which skips the `submit` event and validation).
- [ ] View changes: call the app's own function (`showTab`) or click the nav button; both work, but the nav button is closer to a user.
- [ ] If your app checks `event.isTrusted`, none of this works; you would need a real input driver, which is a different tool.

**Seed and reset functions.** See section 4.

**A static-file list, if the server restricts files.** CampusSync's server serves only the names in `CAMPUS_FILES` (`vision/main.py` line 110).

- [ ] Add every new file the tour loads (the `.js`, any `.css`) to that list.
- [ ] **Restart the server** afterwards (the list lives in the running process). A stale server answers 404 for the new file, the `<script>` fails silently, and the button does nothing.
- [ ] If your server is a plain static server, this does not apply.

**Somewhere to put the caption bar.** `position: fixed`, a very high `z-index`, and `role="status"` / `aria-live="polite"` so a screen reader hears the captions.

## 4. Seed and reset: the part that decides whether the tour is safe

The tour presses real buttons, so it **writes real data**. Decide, before writing steps, how that data is put back.

- [ ] **Seed** puts the app into a known starting state, so every run looks the same. In CampusSync that is `demo.js`, run on page load, guarded by a flag so it runs once per browser.
- [ ] **Reset** removes what the tour added, on every exit: finished, Stop pressed, or error. In `demo-tour.js` it is called from the same place for all three.
- [ ] Prefer **snapshot and restore** for anything the tour changes that the visitor might also own (CampusSync does this for attendance: `KEY + ".att"`). The example page presses "Clear finished" and would otherwise delete the visitor's own finished tasks.
- [ ] Prefer **tagging** for things the tour *adds* (CampusSync appends `(demo)` to its text and filters those out). Tag a field that survives the app's own processing.
- [ ] Decide what happens when the tab is **closed mid-tour**. CampusSync's reset only runs from `finish()`; see the failure section of DEMO_BUTTON_EXPLAINED.md for what that leaves behind. A fix is to run the cleanup on the next page load whenever an interrupted state is found.

## 5. Timing

- [ ] Every wait should be interruptible: a loop of short sleeps checking an `aborted` flag (`tour.js` `wait()`, 50 ms; `demo-tour.js`, 40 ms). A single `await sleep(5000)` makes Stop feel broken.
- [ ] Add an automatic pace knob so tests can run the tour fast (`pace: 0.1` in `demo-tour.js`).
- [ ] Time the real thing, on a slower machine than yours. Smooth scrolling and layout make a tour slower than the sum of its `wait()` calls.
- [ ] If you show a progress bar, drive it from the wall clock, not from the steps, or it jumps.

## 6. Mistakes to avoid (those about CampusSync are visible in its code; none of them is a bug report)

1. **Silent failure.** `tour.js` logs a missing element with `console.warn`, then reloads the page. The viewer sees the demo vanish. `demo-tour.js` shows "Demo stopped: no element for ..." in the bar for 2.5 s.
2. **Selectors by position.** `querySelectorAll(".calendar-header button")[1]` means "the second button", which is a layout fact, not a meaning.
3. **Steps that depend on today's date.** CampusSync's step 3 clicks "next month" three times expecting an unstarted semester, step 4 clicks the last finished lecture. Both depend on the calendar and on the semester dates in `data.js`; when the data goes out of date, the caption stays and the screen no longer matches. Seed relative dates, or check them.
4. **Caption says more than the screen shows.** The CampusSync caption "Vision: upload a timetable screenshot or notice and it fills the calendar..." is shown while the tour only opens the Import card; nothing is uploaded. Say what happens.
5. **Reset only on the happy path.** Put it where Stop and errors also land.
6. **Forgetting the server restart / file list** (section 3).
7. **State that dies with the tab.** `sessionStorage` carries the tour across a reload but only in that tab; if storage is blocked, the continuation silently never happens.
8. **Letting the visitor click during the tour.** Neither version blocks input. A visitor who clicks mid-tour can change the state the next step expects. If that matters, put a transparent full-page layer under the caption bar.
9. **Browser dialogs.** `alert()` / `confirm()` / `prompt()` freeze the page and the tour with it. CampusSync's app replaced them with in-page menus; do the same.
10. **Two things called "demo".** CampusSync has the tour button and, inside the Vision page, a separate "Run demo" button. Name them differently in the UI and the docs.

## 7. What the generic file does not do

- **No continuation across a page reload.** `tour.js` survives a reload (part 1 to part 2) by saving `{ start, part }` in `sessionStorage` and resuming in `init()`. `demo-tour.js` runs in one page lifetime. Multi-page tours need that mechanism added.
- **No overall time bar.** There is a "2/7" step counter instead.
- **No built-in login/seed helpers.** `seed()` and `reset()` are yours.
- **No input blocking** (point 8).

## 8. What was tested, and what was not

Tested (Playwright, Chromium, [demo-tour/test_demo_tour.py](../demo-tour/test_demo_tour.py), 13 checks, all passed, pace set to 0.1):

- The bar appears, the start button is disabled during the run and re-enabled after.
- The tour's typing and clicking go through the page's own handlers (a task appears in the list mid-run).
- All 7 captions appear in order.
- `seed` runs once before the steps and `reset` once after; the visitor's own saved data is identical afterwards, even though the tour pressed "Clear finished".
- A second run on the same page works.
- Stop ends the tour in under 2 s and `reset` still runs.
- A step pointing at a missing `data-tour` element shows the error, runs `reset`, and leaves the page usable.
- Calling `start()` while running returns `false` and adds no second bar.

Not tested:

- Any browser except Chromium (Firefox, Safari).
- A real project other than the one-page example. In particular **`demo-tour.js` has not been run inside CampusSync** and CampusSync's own `tour.js` was not changed.
- Frameworks that control inputs (React, Vue). The `input`-event approach may need extra work there.
- Touch devices, small screens, screen readers (the `role="status"` / `aria-live` attributes are set but nobody listened to them).
- A visitor interacting during the tour.
- Pace 1 for the whole example (only the Stop and double-start tests run at normal speed, and only for the first moments).

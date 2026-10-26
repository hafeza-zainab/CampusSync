# Proposed integrated demo flow (about 90 seconds) — PROPOSAL, not final

Nothing here is final. **No overlay text is written yet**, as agreed: it comes after you approve the flow. Every step below has been run by `py tests/demo_walkthrough.py` (9/9 checks passed); the screenshots from that run are in the report. The demo uses **synthetic** images and **demo accounts**; say so on screen or in the Devpost text.

## What you need ready
- Server running; open `http://localhost:8000/campus/` in a fresh Incognito window (see CHECKLIST.md, steps 1–6).
- Files to upload: `vision/samples/timetable_demo_new.png` (a different weekly timetable, same subjects) and `vision/samples/notice.png`.
- Log in with a placeholder ID, for example `DEMO-CS-001`.

## The flow

| # | Step (what you do) | What the viewer sees | Time on screen (estimate) | Measured in the scripted run |
|---|---|---|---|---|
| 1 | Log in with `DEMO-CS-001` | College ID login, no phone/email; dashboard with the nav | 6 s | 3.4 s |
| 2 | **Import from screenshot** tab → choose `timetable_demo_new.png` | Blue boxes on every cell, green boxes on every text block, entries tagged, step timings | 18 s | 7.3 s for tab + read + animation |
| 3 | Scroll to the attendance card; press **Replace timetable** | The preview of lectures added and removed, then confirm | 8 s | under 1 s |
| 4 | **Calendar** tab → previous month → click six lectures *Present*, two *Absent* | Green and red lectures; the side panel with held / attended / % and the 75% banner | 20 s | 0.9 s |
| 5 | **Import** tab → choose `notice.png` → **Post all** → **Announcements** tab | Five dated tasks as announcements by your ID, "via Vision" | 16 s | 5.3 s |
| 6 | **Study Panel** tab → filter by a subject | Everything Vision read, tagged by semester / subject / topic / date, with its source | 10 s | 0.2 s |
| 7 | **Chat** tab → **Ask a doubt** → pick subject, type a topic → send | The template-only chat: no free-text box, a doubt card | 12 s | 0.3 s |
| | **Total** | | **about 90 s** | about 17 s of scripted actions |

The "time on screen" column is **my estimate for a person** (a scripted browser clicks far faster than you will). The OCR read and the box animation are real waits of about 5–7 s per upload.

## Things to know before approving
- **It starts from the default timetable.** In a fresh window the calendar uses the timetable in `data.js`; step 3 replaces it with the new one, so the change is visible.
- **Marks in the previous month.** The walkthrough marks lectures in the previous month because every lecture there has already finished (lectures that have not ended cannot be marked).
- **No course is selected** in the embedded Vision page, so entries are tagged "(no course selected)" and confidence is slightly lowered (89%). Selecting the course and semester in its dropdowns first would show "Semester 4" tags; that adds about 5 seconds.
- **The Vision page is dark and the app is light.** The embedded page keeps Vision's own look.
- **Optional extra (+10–15 s):** open a second tab, switch the "Demo only" chat user to another account, and press **I can help** on your doubt, to show the answer arriving. Say "simulated users in one browser".
- **Not shown:** real data, a phone, other browsers. Don't claim them.
- **Vision-only 60-second demo** (`DEMO_SCRIPT.md`) still works unchanged and is shorter if 90 seconds is too long.

## What I need from you
1. Is this the right order and are these the right seven steps?
2. Do you want the optional second-tab chat answer?
3. Once approved, I write the on-screen text overlays (kept to what the screen actually shows).

# Pre-recording checklist and known issues

## A. Before you record (in order)

**1. Start the server**
- Close anything already using port 8000.
- Terminal: `cd` into the `vision` folder, then `py -m uvicorn main:app --port 8000`.
- The server loads the OCR model before it accepts connections (about 15 s). **If the page loads, it is ready.**

**2. URLs**
- The CampusSync app (the main thing to demo): `http://localhost:8000/campus/`
- Vision on its own: `http://localhost:8000/`
- Demo accounts (placeholder IDs, no password in the committed code): `DEMO-CS-001` to `DEMO-CS-004`.
- Do **not** open `index.html` from a file or Live Server: it can't see Vision's data (measured).

**3. Run the tests** (with the server running; the e2e run resets the saved entries)
- `py tests/unit.py` → expect `44/44 checks passed`
- `py tests/e2e.py` → expect `169/169 checks passed`
- `py tests/demo_walkthrough.py` → expect `9/9 walkthrough checks passed` (runs the proposed integrated demo in order and prints step timings)
- If either fails, don't record. Tell me which line failed.

**4. Edit `data/catalog.json`** (reload the page afterwards; no server restart needed)
- Course `main`: replace the name "My course (rename me)" with your real course name.
- The semester id `sem4` is a guess. Rename it / its display name to your real semester.
- Add your real teachers (`"teacher": {"name": "Dr. Full Name", "code": "AB"}`) and rooms (`"room": "LH-3"`) per subject. Leave `null` where unknown.
- **If you use the built-in "Run demo" image, don't rename or remove the nine subjects**: the image shows Hindi, OOP C++, Extension Work, Python, Web Tech, EVS, DAA, Advanced Python, Leadership.
- The two PLACEHOLDER courses show in the Course dropdown. They are needed for the tests; do the edit/removal **after** step 3 if you want them gone from the video (keep a copy of the file).

**5. Reset state**
- Vision page: click **Reset panel** (empties `data/entries.json`).
- Browser storage (announcements, timetable, attendance marks per ID, Study Panel items, chat, last login all live here): record in a fresh **Incognito/Private window**, or clear site data for `localhost:8000` (DevTools → Application → Storage → Clear site data). A fresh window also means the calendar starts on the default `data.js` timetable.
- Chat: a fresh Incognito window already starts with the seeded demo messages; otherwise open the Chat tab and click **Reset chat** twice.
- Re-check the Study Panel (app) shows "No study materials yet" and Vision's Study Panel is empty.
- The built-in "Run demo" image is identical to the default timetable, so importing it changes nothing in the calendar. For the integrated demo use `vision/samples/timetable_demo_new.png` (different slots, same subjects). See DEMO_FLOW_PROPOSAL.md.

**6. Screen setup**
- Use Chrome or Edge (all tests ran in Chromium; nothing else is tested).
- Window at 1920×1080 if you can. **Browser zoom 75–80%** (Ctrl and minus), so the upload area and the filled Study Panel are both visible. (At 100% the Study Panel is about 1250 px tall and runs off the screen.) Hide the bookmarks bar; turn on Do Not Disturb.

**7. One dry run, then record**
- Vision only: click **Run demo**; expect about 6–7 s until "6 · Auto-tagged", 11 entries, 9 subject cards.
- Integrated flow: follow DEMO_FLOW_PROPOSAL.md once, then reset (step 5).
- Click **Reset panel** again, then start recording and repeat.
- The page labels the sample "(synthetic sample)". Keep that visible, and say it in the Devpost text.

## B. Don't demo these (known issues)

| Don't | Why |
|---|---|
| Upload a real screenshot or photo you haven't tried first | Real-image accuracy has not been measured. Try each one in a rehearsal; only show ones that work. |
| Borderless timetables, handwriting, sideways or upside-down photos with no EXIF tag | Unsupported or untested (see README Limitations). A borderless timetable gives one meaningless entry. |
| Open `studypanel.html` | The old standalone form posts to a route that doesn't exist. It is unused; the Study Panel **tab** in the app is the real one. |
| Call the login "secure" or talk about passwords | There is no password in the committed code: any well-formed ID gets in. It is a demo identity. |
| Upload a study file over 1 MB and expect it to be kept | Browser storage is small: files above 1 MB are refused with a message. Use a small file. |
| Promise that data is shared between people | Everything lives in one browser's storage. Another computer or browser sees nothing. |
| Click **Replace timetable** with a placeholder course selected, on a browser profile you care about | It replaces the timetable the attendance app uses (Undo restores it; marks for lectures not in the new timetable are hidden until you Undo). |
| Open the app from a file / Live Server | Different origin, so Vision's data won't appear. |
| Leave old uploads in place | Entries and announcements persist (server file + browser storage) until you reset them (step 5). |
| Call the chat "real-time multi-user chat" | It is four simulated demo users in one browser, no server (the page says so). Show it with two tabs and say "simulated users". |
| Rely on chat message times looking "live" | Seeded messages are timestamped relative to when the data was first created. Click Reset chat right before recording. |
| Hover over Vision's lecture rows while recording the vision-only demo | A small "Request notes" link appears on hover. Keep the mouse off the rows. |
| Claim accuracy numbers | The only numbers are from synthetic images. Say "tested on synthetic images; real-image accuracy is being measured". |

## C. If something goes wrong on the day
- Page won't load: the server isn't running or port 8000 is taken. Restart it (step 1).
- A run looks stuck: refresh, **Reset panel**, run again.
- `pip install` fails with a path-length error on Windows: use a shorter folder path or a virtual environment closer to the drive root.

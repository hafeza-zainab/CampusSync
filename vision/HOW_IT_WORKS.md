# How it works (the "re-learning my own code" version)

> **Note:** this document describes an earlier version of the app (no password, a separate Import tab, one semester) and has not been updated. The README is current.

A picture is just a grid of numbers. OpenCV loads it as a numpy array: `img[y][x] = (blue, green, red)`. Everything below is arithmetic on that array.

## Files
| File | Job |
|------|-----|
| `pipeline.py` | All the vision and text-understanding. Read it top to bottom. |
| `main.py` | FastAPI: receives the upload, calls `pipeline.analyze`, saves tags to `data/entries.json`. |
| `static/index.html` | The page: drop zone, animated boxes, Study Panel. |
| `catalog.py` + `data/catalog.json` | The course/semester/subject/teacher/room list (see "The course catalog"). |
| `eval.py` | Measures accuracy against hand-written answer files (see "Measuring accuracy"). |
| `make_sample.py` | Draws fake (synthetic) test timetables/notices so you can test without real files. |
| `tests/unit.py`, `tests/e2e.py` | Scripted checks: extraction rules, and the real pages in a headless browser. |
| `../store.js` | Shared localStorage keys used by the attendance app and Vision (see "the bridge"). |
| `../chat.js`, `../chat.css` | The Chat tab of the attendance app (see "The Chat tab"). |
| `../study.js`, `../study.css` | The Study Panel tab (see "Study Panel"). |
| `../import.js`, `../import.css` | The "Import from screenshot" tab (see "Import from screenshot"). |
| `tests/demo_walkthrough.py` | Runs the proposed integrated demo flow end to end and times it. |

## The pipeline, step by step
1. **Load** (`load_pages`, `decode_image`). Images are opened with Pillow and `ImageOps.exif_transpose` turns them upright using their EXIF orientation tag (phones store photos sideways plus a tag; without this a portrait photo would arrive rotated). Images that are physically rotated or upside-down with **no** tag are not corrected and will fail. For PDFs, PyMuPDF renders each page (up to 3) to an image first, so a PDF becomes "just an image"; the PDF's own text layer is not used.
2. **Clean-up** (`preprocess`)
   - *Deskew*: `Canny` finds edges, `HoughLinesP` finds long straight lines, and we take the median angle of the near-horizontal ones and rotate back by that amount.
   - *CLAHE*: boosts contrast in small tiles. It is meant to help dim photos, but on the synthetic noisy/uneven-light sample the output was identical with and without it, so its benefit is unmeasured.
3. **Find the table** (`find_grid`). This is classical computer vision, no AI model:
   - `adaptiveThreshold` makes lines/text white on a black background.
   - `morphologyEx(OPEN)` with a very wide, 1-pixel-tall rectangle keeps only horizontal lines. A tall, 1-pixel-wide one keeps only vertical lines. Text is too short to survive; lines are not.
   - Add the two results together to get the table skeleton. `findContours` on the empty spaces between lines gives one rectangle per cell.
   - `drop_containers` throws away any "cell" that contains other cells (a faint line can make OpenCV return one big region over many cells, which used to shift the columns), then `group_rows` sorts the rest into rows.
4. **OCR** (`run_ocr`). RapidOCR (ONNX models, installed with pip only) returns text blocks: box, text, confidence. A Tesseract fallback exists in the code but has never been run (it needs the Tesseract program installed).
5. **Understand**
   - *Timetable* (`parse_timetable`): the row with the most day names is the header (or, if the days run down the left side, the row of time slots is). Each cell is assigned to a day/time by how much it overlaps the header cell horizontally, not by its position in the row. The OCR text inside the cell is the subject; the time is the first time-looking cell of the row (or the column header). Subjects are fuzzy-matched (`difflib`) against the catalog (see "The course catalog" below), so "OOP C+" still becomes "OOP C++". The table can have days across the top *or* down the side (`detect_layout`). Date = next occurrence of that weekday.
   - *Notice* (`parse_notice`): OCR boxes at the same height are joined into lines. Each line with a date (`14 Nov 2026`, `14/11/2026`, `Nov 25`) becomes one entry. Subject comes from the catalog or a `Subject:` prefix, task from keywords (submit / viva / quiz ...), topic is the words after "on".
   - *Notes with no dates* (`parse_notes`): first line is the topic, dated today. This has only been tried on one synthetic image.
6. **Auto-tag.** `main.py` saves each entry with its course and semester, skipping duplicates (same course + semester + subject + date + topic). The page groups them Course > Semester > Subject, then lists topic and date.

## Honest limitations
- Printed text works well. **Handwriting is hit-and-miss**: general OCR models are weak at it, and I have not tested it on real handwriting.
- Grid detection needs visible table lines. A timetable drawn without lines is **not supported**: on a synthetic one the result was a single meaningless "notes" entry.
- Extraction is rule-based (regex plus fuzzy match), not an LLM. It is predictable and offline, but only knows the date/task formats written in `pipeline.py`.
- SAM (Segment Anything) is **not** used. Classical morphology worked for the ruled tables in the test set and needs no GPU. SAM is a possible future upgrade for layouts without lines; it has not been tried.

## Measuring accuracy: eval.py
`eval.py` is how we know the numbers in the README are real.
1. For every image/PDF in `real_samples/` that has a `NAME.truth.json` (the answer key you write by hand), it runs `pipeline.analyze()` and times it.
2. `pair_entries()` pairs each truth entry with an extracted entry by **slot** (timetable: day, plus time if the truth has it; notice: date), preferring one with the same subject. A same-slot entry with a different subject is still paired and reported as "subject wrong".
3. For notices the topic and task text are then compared with `difflib.SequenceMatcher` (a 0-1 "how alike are these strings" score). Below the threshold it is a **partial**, which is reported and *not* counted correct.
4. Truth entries with no partner are **missed**; extracted entries with no partner are **extra**.
5. It prints a table and writes `eval_results.md`. `py eval.py --dir samples` does the same for the synthetic images and writes `eval_results_samples.md`.

How to write a truth file: see `real_samples/README.md`. `make_sample.py` also writes truth files for the synthetic samples, as working examples.

## How Vision connects to the attendance app (the bridge)
The attendance app (`../index.html`, `app.js`, `data.js`) is plain front-end code with no server and, originally, no saving. Vision is a Python server. They meet in **localStorage**:
- `main.py` also serves the attendance app at `http://localhost:8000/campus/` (only a fixed list of files, so `.git` and the Python source are not served). Vision lives at `http://localhost:8000/`.
- Same address and port = same "origin" = the browser gives both pages the same localStorage.
- `../store.js` defines the keys (announcements, timetable, attendance, study, chat, plus a timetable backup for Undo), the login helpers, and `loadStore(name, fallback, suffix?)` / `saveStore(name, value, suffix?)`. The keys hold the shapes the app already used: `announcements` `[{msg, by, ...}]`, `timetable` `{Monday: [{time, subject, color}]}`, `attendance` `{"2026-1-12-Hindi-07-08": "present"}`; attendance is one map per college ID (`campussync.attendance.<ID>`).
- `app.js` loads those (attendance after login) and saves after posting an announcement or marking attendance. Before this, a page reload erased everything.
- **You must open the app through `/campus/`.** Opening `index.html` from a file or Live Server is a different origin and will not see Vision's data.

## Post as announcement
For notices/notes (not timetables) the page shows a review card under the Study Panel.
1. Each row is editable (subject, date, topic, task). Edits change the announcement only, not the Study Panel copy.
2. Entries under 80% confidence get an amber **check this** flag and the Post button refuses until **I checked this** is ticked. "Post all" skips unchecked ones and says how many.
   *Where confidence comes from:* see "Confidence" below (OCR score, times subject-match similarity, times 0.9 if no course+semester was chosen).
3. Posting appends `{msg, by: <logged-in college ID>, role, via: "Vision", title, date, source, key}` to the announcements key (`by` is "Vision" only if nobody is logged in). `msg` is still the text the app displays (`title · date · original sentence`); `title`, `date`, `source` and `key` are optional extras. The app draws announcement text with `textContent`, so text read from a screenshot cannot inject HTML.
4. **Duplicates:** `key` = subject + date + topic (lower-case, single spaces). If that key is already in the list, it is not posted again. If you edit the topic, it counts as a different announcement.
5. The Announcements tab re-reads the saved list every time it opens, so new posts appear without a reload.

## Small fixes made to the attendance app (one commit each)
| Fix | Why |
|---|---|
| Removed the `alert("JS is connected")` | It popped up on every page load. |
| `prevMonth()` / `nextMonth()` added | The buttons called functions that did not exist. |
| `parseEndTime()` | `data.js` times are `"07-08"`, the code expected `"09:00"`, so no lecture ever counted as finished and attendance could not be marked. Hours below 7 are treated as afternoon (`"01"` = 1 pm). |
| `by: currentRole` | Announcements showed "— undefined". |
| Re-render announcements when the tab opens | The list was blank until you posted. |
Later changes to the attendance app are described in "Attendance", "Login with a college ID" and "Study Panel" below. `checkWarnings()` (which read counters that were local to `renderCalendar()`) is fixed there.

## The course catalog (`data/catalog.json`, `catalog.py`)
Real colleges have many courses; each course has its own number of semesters; each semester has its own subjects; each subject can have a teacher and a room. All of that lives in **one JSON file**, so no college is written into the code:
```
courses -> semesters -> subjects -> { name, color?, teacher?: {name, code}, room? }
```
- `main` is seeded from `data.js`. `data.js` only has subject names and colours (no course name, semester number, teacher or room), so those fields are empty and the semester id `sem4` is a guess. **Edit the file** to put in your real course name, semester ids, teachers (`{"name": "Dr. ...", "code": "AP"}`) and rooms.
- `demo-a` and `demo-b` are **fake placeholder courses** (`"placeholder": true`) with different numbers of semesters, used only for tests. They are never searched when no course is selected.
- The upload page has Course and Semester dropdowns (filled from `GET /api/catalog`). Their choice becomes a **Scope** (`catalog.make_scope`):

| You picked | Subjects searched | Confidence | May fill teacher/room from catalog |
|---|---|---|---|
| course + semester | only that semester | normal | yes |
| course only | all semesters of that course | x 0.9 | no |
| nothing | every subject of every non-placeholder course | x 0.9 | no |

- **Fuzzy matching** (`match_subject`): OCR text must be at least 0.85 similar to a subject name to count as that subject. Below that it is kept as read and treated as unknown. (It was 0.78 at first; a test showed "Placeholder Seminar" being matched to "Placeholder Chemistry". 0.85 still catches real typos such as `OOP C+` = 0.92 and `0OP C++` = 0.86.)

## Teacher and room (`extract_teacher_room`, `resolve_fields`)
Patterns recognised: `Prof./Dr./Mr./Mrs./Ms. Name`, a teacher short code from the catalog (`AP`, `(AP)`, `Dr. AP`, or a code at the end of a timetable cell), `Room 301`, `R-204`, `LH-3`, `LH 3`.
Every entry records where each value came from:

| field | meaning |
|---|---|
| `teacher_source` / `room_source` = `"image"` | read from the image. Initials are expanded to the full name through the catalog and the raw text is kept in `teacher_read` (shown as `AP → Dr. Asha ...`). |
| `= "catalog"` | **not** in the image; copied from the catalog. Only when course + semester were chosen **and** the subject matched at least 0.90 (`CATALOG_FILL_MIN`). Shown with a dashed amber outline and "from catalog". |
| `= ""` | not found, left empty. Nothing is guessed. |

Short codes are only recognised when they exist in the catalog, so a bare all-caps word like `CSE` is not turned into a teacher. A title overrides that: `Dr. CSE` is read as the teacher "Dr. CSE", as written. Checked in `tests/unit.py`.

## Confidence
`confidence = OCR score of the text (RapidOCR) x subject match similarity (or 0.85 if no known subject matched) x 0.9 if no course+semester was chosen`, capped at 0.99. The OCR score is real model output; 0.85 and 0.9 are fixed rules of ours. Below **0.80** the entry is shown amber with "check this".
(The timetable confidence used to be a fixed 0.99/0.7. It is now computed.)

## One OCR fix worth knowing
RapidOCR has an "is this line upside down?" check. It turned the header `08-09` into `60-80` (99.9% confident) because the digits look alike when rotated 180°. `run_ocr` now calls the engine with `use_cls=False`. Screenshots and deskewed photos are upright, so nothing is lost; a photo taken upside-down would now fail.

## eval.py: per-field accuracy
Entries are paired by their **slot** (timetable: day, plus time if the truth has it; notice: date). A pair with the right slot but wrong subject is reported as "subject expected X got Y" instead of one miss plus one extra. The report gives accuracy separately for **subject, day/time, teacher and room**. Teacher and room are only scored when the truth entry has them, and the report also says how many correct values were read from the image versus filled from the catalog. Truth files may name a `course` and `semester`; eval then runs the pipeline with that scope.

## New synthetic test layouts (`make_sample.py`)
All of these are drawn by the script (**synthetic**): `timetable_transposed.png` (days down the side), `timetable_teacher_room.png` (cells with subject + initials + room, fake placeholder course, some cells deliberately missing teacher/room to exercise catalog filling), `notice_teacher_room.png`, `timetable_demo_new.png` (a different weekly timetable with the same subjects, used in the integrated demo so the import visibly changes the calendar), two EXIF-rotated JPEGs (`timetable_exif6.jpg`, `timetable_exif3.jpg`), and `timetable_pdf.pdf` (the timetable on an A4 page).

## Timetable -> attendance
After a timetable upload the page shows card 4. How it works:
1. `currentTimetable()` reads what the attendance app uses now: the saved `campussync.timetable` key, or else the default `timetable` from `/campus/data.js` (run inside a function so its variables do not leak into the page).
2. `buildTimetable()` turns the lecture entries into the same shape (`{Monday: [{time, subject, color?}]}`), keeping the colour the app already uses for a subject. Entries without a day or time are skipped and listed.
3. `diffTimetables()` shows what is added, removed and unchanged. The calendar and the Monthly Stats panel already compute lectures from the timetable, so there is no separate lecture list to fill; the preview shows lectures per week per subject.
4. `hiddenMarks()` reads the attendance key (read only) and finds marks whose weekday, subject and time are not in the new timetable. They stay saved but the calendar stops showing them; the card warns and lists them.
5. Nothing is written until **Replace timetable** is pressed. Then the old timetable is copied to a backup key and the new one saved. The attendance key is never written. **Undo** restores the backup.
6. If any lecture is under 80% sure, the button stays disabled until "I checked them" is ticked. If the new timetable equals the current one the button says so and stays disabled.

## Tests (what backs the claims in the README)
- `py tests/unit.py` (no server needed): 45 checks of the extraction rules: which room/teacher/date patterns are recognised, which are *not*, what the fuzzy match accepts and rejects, the confidence formula, and the eval helpers.
- `py tests/e2e.py` (server running): 168 checks that drive the real pages in headless Chromium: the Vision demo flow, announcements (editing, confidence flag, duplicates), catalog dropdowns and chips, login by college ID, the Import tab (live updates into the calendar, announcements and Study Panel), the Study Panel (tags, filters, 1 MB limit, storage-full message), attendance (green/red/neutral, monthly counts, 75% warning, per-ID storage), timetable → attendance (preview, warning, confirm, undo), the Chat tab (templates only, one-to-one, answers across tabs, quality bar at 1920x1080 and 1366x768) and Vision's "Request notes" prefill. It also checks that the page makes no requests outside `localhost`. It uses the synthetic images; run `make_sample.py` first.
- `py tests/demo_walkthrough.py` (server running): 9 checks that run the proposed integrated demo flow in order and print how long each step took.
- Run all of them after **any** code change. None tests real student images, handwriting, a phone, or browsers other than Chromium.

## Login with a college ID (`../store.js`, `login()` in `../app.js`)
- The login box asks for a **college ID** (4-20 letters, digits or hyphens, case-insensitive) and a role. There is no name, phone number or email field anywhere (a browser test checks this).
- `normalizeId()` upper-cases it; a bad ID shows an inline message (no popup). `setSession({id, role})` remembers who is logged in: in `sessionStorage` (per tab, so two tabs can be two people) and in `localStorage` (the last login, so the Vision page knows whose data to use).
- The ID is the identity everywhere: attendance is stored per ID (`campussync.attendance.<ID>`), announcements are authored by the ID, and chat senders are IDs.
- `DEMO_USERS` in `store.js` lists four demo accounts, `DEMO-CS-001` to `DEMO-CS-004`, with first-name labels. **These are placeholders, not real people.** Any other well-formed ID can also log in; it just has no demo name.
- **There is no password in the committed code, so this is not authentication.** Anyone can type any ID. Logout (`logout()`) clears the tab's session and reloads.

## Attendance (`renderCalendar`, `renderStats`, `renderAttendanceTab`, `checkWarnings` in `../app.js`)
- Calendar by month: the days list each lecture by subject. The month shown starts as the current month.
- Click a lecture for a small menu: **Present** (green), **Absent** (red), **Clear** (grey, "unmarked"). A lecture whose end time has not passed cannot be marked; the menu says when it opens. The stored shape is unchanged: `attendance["2026-8-7-Hindi-07-08"] = "present" | "absent"` (month is 0-11).
- `monthRows()` computes, per subject for the month on screen: scheduled lectures, **held** (end time passed), present, absent, unmarked, and percent = present / held. The side panel and the Attendance tab table both use it.
- `checkWarnings()` flags subjects under 75% in a visible banner and in the Attendance tab (no popup). It was broken before: it read counters that were local to `renderCalendar()`; they are global now. Exactly 75% is not flagged.

## Study Panel (`../study.js`, `../study.css`)
- Built into the existing Study Panel tab (`#study`), using its existing list container `#materialsList`. Data lives under the `study` key of `store.js`:
  `{id, source: "upload" | "vision", semester, subject, topic, date, addedBy, addedAt, fileName?, fileType?, fileSize?, fileData?, via?, kind?, teacher?, room?, confidence?, needsCheck?}`.
- **Upload form:** Semester, Subject (the subjects in the timetable the app is using), Topic (max 80 characters), Date, and an optional file. A file is stored as a data URL **only if it is 1 MB or smaller**; a larger file is refused with a message and nothing is added. If the browser's storage is full, the add is undone and the user is told. Files are offered back through a download link (only `data:` links the panel created itself).
- **Filters:** semester, subject, topic text (contains), and a date range (from / to), with "Showing X of Y" and "Clear filters". The list is newest date first.
- **Vision entries:** the Vision page writes every entry it extracts into this key (`saveToStudyPanel`) with `source: "vision"`, the file name, who was logged in, and `needsCheck` when confidence is below 0.80. They show a "Vision · file" chip and an amber "check this (NN% sure)". Entries are de-duplicated by course + semester + subject + date + topic.
- You can remove items you added (or that Vision added while you were logged in); not other people's.
- Text is always added with `textContent`.

## Import from screenshot (`../import.js`, `../import.css`)
- A nav entry opens a tab that shows the Vision page in an `<iframe>` (`../?embedded=1`), loaded the first time the tab is opened. In that mode Vision hides its own header.
- The frame grows to fit its content: the Vision page reports its height with `postMessage` and `import.js` sizes the frame, so the whole app page scrolls.
- The standalone Vision page has a "← Back to CampusSync" link.
- **How results reach the app without a reload:** Vision saves into the same `localStorage` keys (timetable, announcements, study). When one document in the same browser changes localStorage, the browser sends a `storage` event to the other documents, including the parent page of an iframe. `app.js` listens: a new timetable is applied with `applySavedTimetable()` (the `data.js` timetable is remembered so Undo can restore it) and the calendar is redrawn; announcements are re-read; `study.js` re-reads its list.
- Timetable → attendance still goes through the existing preview-and-confirm card; notices still go through the review card.

## The Chat tab (`../chat.js`, `../chat.css`)
**What it is, honestly:** a front-end demo chat inside the attendance app. The "users" are the demo accounts, in **one browser**. There is no server, so it is **not** real-time chat between different computers or browsers. Two tabs of the same browser stay in sync.

**No free text.** There is no text box. A message can only be sent from one of three templates, each with exactly Subject, Date and Topic:

| Template | Card | Answer button | After the answer |
|---|---|---|---|
| 📝 Request notes | Note request, status *Open* | "I have these notes" | *Shared*, by whom and when |
| 📤 Notes shared | Notes shared, status *Shared* | none | |
| ❓ Ask a doubt | Doubt, status *Open* | "I can help" | *Answered*, by whom and when |

The answer button is shown to everyone except the sender, and only while the card is open. Subject comes from the timetable the app is using; Date defaults to today; Topic is trimmed, spaces collapsed, max 80 characters. Errors show inline in the form (a `<dialog>`, so Esc closes it and focus returns to the button that opened it).

**Who is chatting:** the logged-in college ID. A section labelled "Demo only" lets one browser act as another demo account (stored per tab in `sessionStorage`) so one person can show a conversation in two tabs.

**How it hooks in without editing your files:** `index.html` has one `<script>` line per feature. `chat.js` builds its own nav button, tab section and stylesheet link, and wraps `showTab()` and `login()` from `app.js`.

**Data** (`store.js` key `chat`): `{ version: 3, messages: [ {id, convo, from, ts, type: "request"|"shared"|"doubt", card: {subject, date, topic, status, handledBy?, handledAt?}} ], reads: { "<id>": { "<convo>": <time of the newest message seen> } } }`.
- `convo` is `"class"` or `"dm:A|B"` (IDs sorted) so both people compute the same id. Unread = messages from others newer than `reads[me][convo]`; opening a conversation updates `reads` (only when something new was read, so two tabs cannot loop).
- `update()` re-reads the newest saved data, changes it and saves, so another tab's message is not overwritten. Version 3 replaces older saved chats (free text, first-name senders) with fresh demo data.
- A message is drawn only if it is a known template with plain-string fields. All text goes onto the page with `textContent`.
- Seed data: three cards in the group, two in a one-to-one, one in another pair; **Reset chat** (two clicks, no popup) restores them. Message times are relative to when the data was created.
- **Prefill from Vision:** the lecture rows on the Vision page have a "Request notes" link (invisible until hover or keyboard focus; positioned so the layout does not change). It opens `/campus/?chat=request&subject=..&date=..&topic=..`. After the normal login the Chat tab opens with the Request-notes form pre-filled (date = the most recent occurrence of that weekday). The user reviews it and presses Send.

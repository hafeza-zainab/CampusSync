# How it works (the "re-learning my own code" version)

A picture is just a grid of numbers. OpenCV loads it as a numpy array: `img[y][x] = (blue, green, red)`. Everything below is arithmetic on that array.

## Files
| File | Job |
|------|-----|
| `pipeline.py` | All the vision and text-understanding. Read it top to bottom. |
| `main.py` | FastAPI: receives the upload, calls `pipeline.analyze`, saves tags to `data/entries.json`. |
| `static/index.html` | The page: drop zone, animated boxes, Study Panel. |
| `make_sample.py` | Draws fake test timetables/notices so you can test without real files. |

## The pipeline, step by step
1. **Load.** PNG/JPG is decoded with `cv2.imdecode`. For PDFs, PyMuPDF renders each page to an image first, so a PDF becomes "just an image".
2. **Clean-up** (`preprocess`)
   - *Deskew*: `Canny` finds edges, `HoughLinesP` finds long straight lines, and we take the median angle of the near-horizontal ones and rotate back by that amount.
   - *CLAHE*: boosts contrast in small tiles so dim photos are readable.
3. **Find the table** (`find_grid`). This is classical computer vision, no AI model:
   - `adaptiveThreshold` makes lines/text white on a black background.
   - `morphologyEx(OPEN)` with a very wide, 1-pixel-tall rectangle keeps only horizontal lines. A tall, 1-pixel-wide one keeps only vertical lines. Text is too short to survive; lines are not.
   - Add the two results together to get the table skeleton. `findContours` on the empty spaces between lines gives one rectangle per cell.
   - `group_rows` sorts the rectangles into rows and columns.
4. **OCR** (`run_ocr`). RapidOCR (ONNX models, installed with pip only) returns text blocks: box, text, confidence. Tesseract is the fallback.
5. **Understand**
   - *Timetable* (`parse_timetable`): the row with the most day names is the header. For every other cell, the OCR text inside it is the subject and the row's first cell is the time. Subjects are fuzzy-matched (`difflib`) against the catalog (see "The course catalog" below), so "OOP C+" still becomes "OOP C++". The table can have days across the top *or* down the side (`detect_layout`). Date = next occurrence of that weekday.
   - *Notice* (`parse_notice`): OCR boxes at the same height are joined into lines. Each line with a date (`14 Nov 2026`, `14/11/2026`, `Nov 25`) becomes one entry. Subject comes from your known list or a `Subject:` prefix, task from keywords (submit / viva / quiz ...), topic is the words after "on".
   - *Notes with no dates* (`parse_notes`): first line is the topic, dated today.
6. **Auto-tag.** `main.py` saves each entry with its course and semester, skipping duplicates (same course + semester + subject + date + topic). The page groups them Course > Semester > Subject, then lists topic and date.

## Honest limitations
- Printed text works well. **Handwriting is hit-and-miss**: general OCR models are weak at it, and I have not tested it on real handwriting.
- Grid detection needs visible table lines. Borderless timetables fall back to free-text mode, which suits notices but not grids.
- Extraction is rule-based (regex plus fuzzy match), not an LLM. It is predictable and offline, but only knows the date/task formats written in `pipeline.py`.
- SAM (Segment Anything) is **not** used. Classical morphology was enough for ruled tables and needs no GPU. SAM would be the upgrade for photos of curved paper or borderless layouts.

## Measuring accuracy: eval.py
`eval.py` is how we know the numbers in the README are real.
1. For every image/PDF in `real_samples/` that has a `NAME.truth.json` (the answer key you write by hand), it runs `pipeline.analyze()` and times it.
2. `compare()` pairs each truth entry with an extracted entry using a **key**: subject + day for timetables, subject + date for notices.
3. For notices the topic and task text are then compared with `difflib.SequenceMatcher` (a 0-1 "how alike are these strings" score). Below the threshold it is a **partial**, which is reported and *not* counted correct.
4. Entries with no partner are **missed** (in the key, not found) or **extra** (found, not in the key).
5. It prints a table and writes `eval_results.md`. `py eval.py --dir samples` does the same for the synthetic images and writes `eval_results_samples.md`.

How to write a truth file: see `real_samples/README.md`. `make_sample.py` also writes truth files for the synthetic samples, as working examples.

## How Vision connects to the attendance app (the bridge)
The attendance app (`../index.html`, `app.js`, `data.js`) is plain front-end code with no server and, originally, no saving. Vision is a Python server. They meet in **localStorage**:
- `main.py` also serves the attendance app at `http://localhost:8000/campus/` (only a fixed list of files, so `.git` and your data are not exposed). Vision lives at `http://localhost:8000/`.
- Same address and port = same "origin" = the browser gives both pages the same localStorage.
- `../store.js` defines three keys and two helpers, `loadStore(name, fallback)` and `saveStore(name, value)`. The keys hold the shapes the app already used: `announcements` `[{msg, by}]`, `timetable` `{Monday: [{time, subject, color}]}`, `attendance` `{"2026-1-12-Hindi-07-08": "present"}`.
- `app.js` loads those at startup and saves after posting an announcement or marking attendance. Before this, a page reload erased everything.
- **You must open the app through `/campus/`.** Opening `index.html` from a file or Live Server is a different origin and will not see Vision's data.

## Post as announcement
For notices/notes (not timetables) the page shows a review card under the Study Panel.
1. Each row is editable (subject, date, topic, task). Edits change the announcement only, not the Study Panel copy.
2. Entries under 80% confidence get an amber **check this** flag and the Post button refuses until **I checked this** is ticked. "Post all" skips unchecked ones and says how many.
   *Where confidence comes from:* the OCR score of the line (RapidOCR), multiplied by 0.85 when the subject is not one we know. That 0.85 is a simple rule of ours, not an OCR output.
3. Posting appends `{msg, by: "Vision", title, date, source, key}` to the announcements key. `msg` is still the text the old page displays (`title · date · original sentence`); `title`, `date`, `source` and `key` are optional extras the old page ignores.
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
**Not fixed:** `checkWarnings()` reads a variable that only exists inside `renderCalendar()`, so after you mark attendance the browser console shows `subjectCount is not defined` and the "below 75%" alert never appears. Marking itself still works.

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

Short codes are only recognised when they exist in the catalog, so a random all-caps word like `CSE` is never turned into a teacher.

## Confidence
`confidence = OCR score of the text (RapidOCR) x subject match similarity (or 0.85 if no known subject matched) x 0.9 if no course+semester was chosen`, capped at 0.99. The OCR score is real model output; 0.85 and 0.9 are fixed rules of ours. Below **0.80** the entry is shown amber with "check this".
(The timetable confidence used to be a fixed 0.99/0.7. It is now computed.)

## One OCR fix worth knowing
RapidOCR has an "is this line upside down?" check. It turned the header `08-09` into `60-80` (99.9% confident) because the digits look alike when rotated 180°. `run_ocr` now calls the engine with `use_cls=False`. Screenshots and deskewed photos are upright, so nothing is lost; a photo taken upside-down would now fail.

## eval.py: per-field accuracy
Entries are paired by their **slot** (timetable: day, plus time if the truth has it; notice: date). A pair with the right slot but wrong subject is reported as "subject expected X got Y" instead of one miss plus one extra. The report gives accuracy separately for **subject, day/time, teacher and room**. Teacher and room are only scored when the truth entry has them, and the report also says how many correct values were read from the image versus filled from the catalog. Truth files may name a `course` and `semester`; eval then runs the pipeline with that scope.

## New synthetic test layouts (`make_sample.py`)
All of these are drawn by the script (**synthetic**): `timetable_transposed.png` (days down the side), `timetable_teacher_room.png` (cells with subject + initials + room, fake placeholder course, some cells deliberately missing teacher/room to exercise catalog filling) and `notice_teacher_room.png`.

## Timetable -> attendance
After a timetable upload the page shows card 4. How it works:
1. `currentTimetable()` reads what the attendance app uses now: the saved `campussync.timetable` key, or else the default `timetable` from `/campus/data.js` (run inside a function so its variables do not leak into the page).
2. `buildTimetable()` turns the lecture entries into the same shape (`{Monday: [{time, subject, color?}]}`), keeping the colour the app already uses for a subject. Entries without a day or time are skipped and listed.
3. `diffTimetables()` shows what is added, removed and unchanged. The calendar and the Monthly Stats panel already compute lectures from the timetable, so there is no separate lecture list to fill; the preview shows lectures per week per subject.
4. `hiddenMarks()` reads the attendance key (read only) and finds marks whose weekday, subject and time are not in the new timetable. They stay saved but the calendar stops showing them; the card warns and lists them.
5. Nothing is written until **Replace timetable** is pressed. Then the old timetable is copied to a backup key and the new one saved. The attendance key is never written. **Undo** restores the backup.
6. If any lecture is under 80% sure, the button stays disabled until "I checked them" is ticked. If the new timetable equals the current one the button says so and stays disabled.

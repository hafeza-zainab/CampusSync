# CampusSync Vision — OpenCV AI Competition

> Upload a timetable screenshot, a notice (image or PDF) or a page of notes. CampusSync Vision finds the table, reads the text with OCR, and turns the lectures and dated tasks it recognises into entries tagged **Course → Semester → Subject → Topic → Date**, with teacher and room when they are written on the page. The entries can be posted as announcements, loaded into the attendance calendar and added to the Study Panel of the CampusSync app after you review them.

**Status:** working prototype, tested on synthetic images and with scripted browser tests (Chromium only). **It has not yet been measured on real student screenshots** (see [Results](#results)).

## Why
Re-typing a timetable and a list of deadlines into separate tools every semester is tedious. Vision reads them from the screenshot or PDF instead, and shows its work (detected cells, text blocks, confidence) so mistakes are easy to spot.

## What it does
1. **Upload** an image or PDF (timetable, notice, notes).
2. **See the vision**: detected table cells (blue) and OCR text blocks (green) are drawn over the image, with per-stage timings.
3. **Auto-tagging**: each lecture or deadline becomes `{course, semester, subject, topic, date, task, teacher, room}` and is listed on the Vision page with a confidence score and is added to the app's Study Panel. Teacher and room are marked **read from image** (solid) or **filled from catalog** (dashed). They are left empty when neither source has them.
4. **Course catalog**: pick a course and semester and only that semester's subjects are searched (`data/catalog.json`: courses → semesters → subjects → teacher/room).

## CampusSync as one product
CampusSync is a college app you open at `http://localhost:8000/campus/`. Vision (the screenshot reader) is built into it as an **Import from screenshot** card at the top of the Study Panel, and feeds the other features, so a timetable or a notice does not have to be typed by hand.

| Feature | What works | How Vision feeds it |
|---|---|---|
| **Login with college ID + password** | Log in with an ID such as `DEMO-CS-001` and a password. The ID is the identity used for attendance, announcement authors and chat senders, and the account decides the role (CR, ACR or student). No phone number, email or name is asked. | |
| **Attendance** | Calendar by month, day and subject. Click a lecture to mark Present / Absent / Clear: attended is green, not attended red, unmarked grey. The side panel shows, per subject, lectures held, attended, absent, unmarked, this month's total and the percentage; subjects under 75% get a warning banner. The Attendance tab shows the same numbers as a table. Marks are stored per college ID. The calendar is **semester-aware**: each date shows the lectures of the semester that contains it; a semester that has not started is greyed out with no stats. | A timetable screenshot replaces the weekly timetable after a preview and a confirm click. Marks are never edited; Undo restores the old timetable. |
| **Announcements** | The CR and ACR can post; students can only read (the box is hidden and a note says why). The author is the college ID and role. | Notice screenshots are reviewed, edited and posted as announcements (duplicates blocked, low-confidence entries need a tick). |
| **Study Panel** | Upload a study material tagged by Semester, Subject, Topic and Date (file optional, up to 1 MB each; bigger files are refused with a message). Filters for semester, subject, topic text and a date range. | Every entry Vision reads is added here with its source ("Vision · file name") and an amber "check this" when Vision was under 80% sure. |
| **Chat** | Class group and one-to-one chats. **No free text:** every message is a template with only Subject, Date and Topic: *Request notes* (answered with "I have these notes"), *Notes shared*, *Ask a doubt* (answered with "I can help"). | The lecture rows on the Vision page have a "Request notes" link that opens the form pre-filled; you review it and press Send. |
| **Demo helpers** | Each demo account is seeded with different attendance (one excellent, one with a weak subject, one struggling, one mostly unmarked). The login screen has **▶ Run 60-second demo** (the app clicks and types by itself with a caption bar, as the CR and then as a student) and **↺ Reset demo data**. | |

**Demo accounts** (placeholder IDs, not real people): `DEMO-CS-001` CR, `DEMO-CS-002` ACR, `DEMO-CS-003` and `DEMO-CS-004` students; the passwords are shown on the login screen.

**How this was tested.** `tests/smoke_app.py` runs 16 checks against the current app in headless Chromium: login and wrong password, roles, tabs, the Import card, notice → announcements, timetable → calendar, student read-only, template-only chat, and the semester calendar. The 60-second demo button was run to the end once (no page errors, no popups). Also: 44 unit checks of the extraction rules (`tests/unit.py`) and the Vision accuracy tool on 12 synthetic images (see Results). Everything uses synthetic images and demo accounts. **Not tested:** real student data, browsers other than Chromium, a phone, screen readers. `tests/e2e.py` (169 checks) and `tests/demo_walkthrough.py` were written for an earlier version of the app (no password, a separate Import tab, one semester) and **no longer match it**; they are not evidence for the current app.

**Read these limits:**
- **Passwords are only a demo.** They are written in plain text in the page's JavaScript (`store.js`) and shown on the login screen. This is **not secure authentication**; a real deployment needs a server that checks them.
- **The chat uses simulated users in one browser, with no server sync.** Two tabs of the same browser stay in sync. It is **not** real-time multi-user chat between different computers or browsers.
- **Everything is stored in the browser's localStorage** (no server database): it is per browser, a few MB in total, and anyone using that browser profile can see or edit it. Clearing site data deletes it.
- **Semesters 1-3, 5 and 6 in `data.js` are placeholders** (invented dates and subjects). Only Semester 4 comes from your real timetable.
- **No real-image accuracy has been measured yet** (see Results).
- The app must be opened through the Vision server (`/campus/`); that is how the two share data. After changing `vision/main.py`, restart the server.

**In progress / future work (not built):**
- Real accounts and a server, and chat between real users on different devices.
- Study Panel visibility settings (private / class / selected students) and file preview. The old standalone `studypanel.html` form is unused.
- Handwriting, SAM-style segmentation for tables without lines, and an LLM extraction pass.
- `data/catalog.json` (used by Vision's subject matching) is seeded from the old `data.js` subjects; real teachers, rooms and semester ids must be added by hand. Demo courses A and B in it are fake placeholders.

## How it works
| Stage | Technique |
|-------|-----------|
| Load | PDFs are rendered page by page with PyMuPDF (first 3 pages); images are opened with Pillow and rotated upright from their EXIF orientation tag |
| Deskew | Canny edges + probabilistic Hough lines → median angle of near-horizontal lines → affine warp |
| Contrast | CLAHE on the L channel of LAB colour space (applied; no measurable effect on the synthetic samples) |
| Table segmentation | Adaptive threshold → morphological opening with long horizontal/vertical kernels → contours of the gaps → drop regions that contain other cells → row grouping |
| Text detection + recognition | RapidOCR (PP-OCR ONNX models bundled in the pip package, run on CPU). A Tesseract fallback exists in the code but has never been run |
| Cell ↔ text assignment | Centre-point-in-rectangle matching; columns are assigned by horizontal overlap with the header cell |
| Understanding | Header detection (days across the top or down the side), fuzzy subject matching against the catalog (`difflib`, threshold 0.85), day-first date regexes, keyword task classification, teacher/room patterns |
| Confidence | OCR score × subject-match similarity × 0.9 if no course+semester was chosen (rules in [HOW_IT_WORKS.md](HOW_IT_WORKS.md)) |

Stack: Python, OpenCV, RapidOCR, PyMuPDF, Pillow, FastAPI, vanilla JS canvas for the box overlay.

**Privacy:** the server contains no outbound network calls, the OCR models ship inside the pip package, and in the browser test the page made no requests outside `localhost`. Run locally as described below, documents are processed on your own machine. (Installing the packages needs internet once.)

## Problems found while testing (and fixed)
- RapidOCR's "is this text upside down?" check turned the header `08-09` into `60-80` at 99.9% confidence, which broke one timetable layout. The check is now turned off (a consequence: images that are physically upside-down without an EXIF tag are not read, see Limitations).
- A timetable placed on an A4 PDF page produced one extra, oversized "cell" that shifted columns: lecture on the wrong day, plus a bogus lecture. Fixed by dropping cells that contain other cells and assigning columns by position; the PDF timetable is now in the test set.
- A subject match threshold of 0.78 matched "Placeholder Seminar" to "Placeholder Chemistry" and copied its teacher and room. Raised to 0.85, with catalog filling only at 0.90 or better.

## Results

### Real images
**Not measured yet.** `real_samples/` has no labelled images. When there are, `py eval.py` will report accuracy per field and this section will be filled from `eval_results.md` (template: [`README_RESULTS_TEMPLATE.md`](README_RESULTS_TEMPLATE.md)).

### Synthetic test images (regression tests, not evidence of real-world accuracy)
These 12 images were drawn by `make_sample.py` by the same person who wrote the code, so passing them shows the code does what it was designed to do. They say nothing about how it handles real, messier input.

| Synthetic input | Result (from `py eval.py --dir samples`) |
|-------|--------|
| Timetable screenshot (5 days × 6 slots) | 42/42 cells found, 11/11 lectures correct |
| Same, rotated 2.5° with noise and uneven light | 11/11 correct |
| Same, as a JPEG with an EXIF rotation tag (pixels stored rotated 90°, tag 6) | 11/11 correct |
| Same, stored rotated 180° with EXIF tag 3 | 11/11 correct |
| Same, placed on an A4 PDF page | 42/42 cells, 11/11 correct |
| Same, days down the side (transposed), course + semester chosen | 11/11 correct |
| A different weekly timetable (same subjects, other slots; used in the integrated demo) | 30 cells, 10/10 correct |
| Cells with subject + teacher initials + room (fake placeholder course, course + semester chosen) | 7/7 lectures; teacher 6/6, room 6/6 |
| Notice with 5 dated tasks, PNG | 5/5 correct (subject, date, topic, task) |
| Same notice as an image-only PDF (picture in a PDF) | 5/5 correct |
| Same notice as a text-layer PDF (selectable text) | 5/5 correct |
| Notice mentioning "Prof. ..." and "Room ..." (placeholder course) | 2/2 correct incl. teacher and room |

Totals reported by eval for these 12 images: 100/100 entries; subject 100/100, day/time 100/100, teacher 8/8, room 8/8; mean 1.3 s per image on the author's PC. Of the correct teacher values, 6 were read from the image and 2 filled from the catalog; of the correct room values, 5 were read from the image and 3 filled from the catalog. Both kinds of PDF are rendered to an image and read with OCR; the PDF's own text layer is not used.

## Limitations
- **Image orientation:** photos rotated by an EXIF tag (what phones write) are turned upright. Images that are *physically* rotated or upside-down with **no** EXIF tag are **not supported**. On the synthetic timetable, a 90° rotation without a tag gave 1 entry instead of 11, and an upside-down copy gave 11 entries, several with garbled subject names (`python tests/measure.py`).
- **Tables without visible lines are not supported.** On a synthetic timetable drawn without lines, the result was a single meaningless "notes" entry.
- **Handwriting has not been tested.** The OCR models are general printed-text models.
- Only the first 3 pages of a PDF are read and only the first page is previewed. Multi-page behaviour was checked on synthetic PDFs only.
- Dates are read day-first (`14/11/2026`). Notices with other layouts or formats than those in `tests/unit.py` may be missed.
- Teacher short codes (`AP`) are only recognised if they are in the catalog; a title makes any name count (`Dr. CSE` is read as written).
- Dateless notes use the first line as the topic and today's date; this was tried on one synthetic image.
- Extraction is rule-based (regex + fuzzy match), not an LLM.
- Dropped from this version: SAM-style segmentation, handwriting models, an LLM extraction pass.

## Run it
```bash
cd vision
pip install -r requirements.txt        # tested in a fresh virtual environment on Windows / Python 3.14
python make_sample.py                  # creates samples/ (synthetic test images)
python -m uvicorn main:app --port 8000
# the CampusSync app:  http://localhost:8000/campus/   (click "Run 60-second demo", or log in as DEMO-CS-001 / cr-demo)
# Vision on its own:  http://localhost:8000/vision    (click "Run demo")
# restart the server after changing vision/main.py
```
Chat screenshots (demo users, seeded messages) are in [`../chat_screenshots/`](../chat_screenshots), made by `py tests/chat_screenshots.py`.
Tests (with the server running): `py tests/unit.py`, `py tests/measure.py` (prints the measurements behind the limitations), and `py tests/smoke_app.py` (needs `pip install playwright` and `python -m playwright install chromium`). `tests/e2e.py` and `tests/demo_walkthrough.py` target an earlier version of the app. Accuracy tool: `py eval.py --dir samples` (synthetic) or `py eval.py` (your images in `real_samples/`).
Code walkthrough: [HOW_IT_WORKS.md](HOW_IT_WORKS.md) · Vision-only demo plan: [DEMO_SCRIPT.md](DEMO_SCRIPT.md) · Claim-by-claim evidence: [CLAIMS_AUDIT.md](CLAIMS_AUDIT.md)

## Built with
python · opencv · rapidocr · pymupdf · pillow · fastapi · javascript

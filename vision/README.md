# CampusSync Vision — OpenCV AI Competition

> Upload a timetable screenshot, a notice (image or PDF) or a page of notes. CampusSync Vision finds the table, reads the text with OCR, and turns the lectures and dated tasks it recognises into entries tagged **Course → Semester → Subject → Topic → Date**, with teacher and room when they are written on the page. The entries can be posted as announcements or loaded into the attendance calendar after you review them.

**Status:** working prototype, tested on synthetic images and with scripted browser tests. **It has not yet been measured on real student screenshots** (see [Results](#results)).

## Why
Re-typing a timetable and a list of deadlines into separate tools every semester is tedious. Vision reads them from the screenshot or PDF instead, and shows its work (detected cells, text blocks, confidence) so mistakes are easy to spot.

## What it does
1. **Upload** an image or PDF (timetable, notice, notes).
2. **See the vision**: detected table cells (blue) and OCR text blocks (green) are drawn over the image, with per-stage timings.
3. **Auto-tagging**: each lecture or deadline becomes `{course, semester, subject, topic, date, task, teacher, room}` and is listed in the Study Panel view on the Vision page with a confidence score. Teacher and room are marked **read from image** (solid) or **filled from catalog** (dashed). They are left empty when neither source has them.
4. **Course catalog**: pick a course and semester and only that semester's subjects are searched (`data/catalog.json`: courses → semesters → subjects → teacher/room).

## CampusSync as a whole, and where Vision fits
CampusSync is a college project with attendance tracking, announcements and a demo chat; its Study Panel is still in progress. Vision is meant to remove manual data entry for the parts that work.

**Implemented and tested.** "Tested" means the scripted checks in [`tests/`](tests) pass: 44 unit checks (`tests/unit.py`) and 103 headless-Chromium checks (`tests/e2e.py`), run on synthetic images and a scripted attendance app. They have not been run on real student data.
- **Vision pipeline**: upload, EXIF/tilt correction, table detection, OCR, extraction, tagging, and a per-field accuracy tool (`eval.py`).
- **Post as announcement**: notice entries can be edited, are flagged "check this" under 80% confidence, and are posted into the attendance app's Announcements tab. Duplicates (same subject + date + topic) are blocked.
- **Timetable → attendance**: a parsed timetable can replace the lecture timetable in the attendance app after a preview (lectures added / removed, lectures per week per subject, a warning for marks that would be hidden) and a confirm click. Marked attendance is never edited. Undo restores the old timetable.
- **Fixes to the attendance app needed for the above**: lecture times like `07-08` could not be parsed (so attendance could not be marked), the month buttons called functions that did not exist, announcements showed "by undefined", and nothing was saved between page loads (announcements, timetable and attendance now persist in localStorage).
- **Chat tab** (in the attendance app, `chat.js`): class group chat and one-to-one chats with last-message preview and unread counts; a **note-request** form with only three inputs (Subject from the timetable, Date, Topic) that posts a request card (Open / Shared; another user presses "I have these notes"); messages saved in localStorage and two tabs of the same browser stay in sync. The lecture rows on the Vision page have a "Request notes" link (visible on hover) that opens this form pre-filled; the user reviews it and presses Send, nothing is sent automatically.
  **Limitation: the chat uses simulated users in one browser, with no server sync.** The "users" are four demo users (Zainab, Aarav, Meera, Kabir) chosen from a "Chatting as" box; there are no accounts, no server and no messages between different computers or browsers. It is **not** real-time multi-user chat. The old `chatbot.html` stub was replaced by a page pointing to the Chat tab.
- The attendance app must be opened through the Vision server (`http://localhost:8000/campus/`); that is how the two share data.

**In progress / future work (not built, or not working):**
- **Real chat**: accounts, a server, and messages between real users are not built (see the limitation above).
- **The attendance app's own Study Panel**: `studypanel.html` is a form that posts to `/upload`, which does not exist, and nothing links to it. The Study Panel tab in the dashboard shows an empty list (its render function `renderMaterials()` targets an element id that does not exist and nothing calls it). The "Study Panel" that Vision fills is the list on the Vision page, stored in `data/entries.json`; it is **not** connected to the attendance app's Study Panel.
- `checkWarnings()` (the "below 75%" alert in the attendance app) throws `subjectCount is not defined` after marking attendance; marking still works.
- Handwriting, SAM-style segmentation for tables without lines, and an LLM extraction pass are not built.
- No real-image accuracy is measured yet.
- `data/catalog.json` is seeded from `data.js`, which holds subject names only. Real teachers, rooms and the semester number must be added by hand. The demo courses A and B in the catalog are fake placeholders.

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
These 11 images were drawn by `make_sample.py` by the same person who wrote the code, so passing them shows the code does what it was designed to do. They say nothing about how it handles real, messier input.

| Synthetic input | Result (from `py eval.py --dir samples`) |
|-------|--------|
| Timetable screenshot (5 days × 6 slots) | 42/42 cells found, 11/11 lectures correct |
| Same, rotated 2.5° with noise and uneven light | 11/11 correct |
| Same, as a JPEG with an EXIF rotation tag (pixels stored rotated 90°, tag 6) | 11/11 correct |
| Same, stored rotated 180° with EXIF tag 3 | 11/11 correct |
| Same, placed on an A4 PDF page | 42/42 cells, 11/11 correct |
| Same, days down the side (transposed), course + semester chosen | 11/11 correct |
| Cells with subject + teacher initials + room (fake placeholder course, course + semester chosen) | 7/7 lectures; teacher 6/6, room 6/6 |
| Notice with 5 dated tasks, PNG | 5/5 correct (subject, date, topic, task) |
| Same notice as an image-only PDF (picture in a PDF) | 5/5 correct |
| Same notice as a text-layer PDF (selectable text) | 5/5 correct |
| Notice mentioning "Prof. ..." and "Room ..." (placeholder course) | 2/2 correct incl. teacher and room |

Totals reported by eval for these 11 images: 90/90 entries; subject 90/90, day/time 90/90, teacher 8/8, room 8/8; mean 1.7 s per image on the author's PC. Of the correct teacher values, 6 were read from the image and 2 filled from the catalog; of the correct room values, 5 were read from the image and 3 filled from the catalog. Both kinds of PDF are rendered to an image and read with OCR; the PDF's own text layer is not used.

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
# open http://localhost:8000 and click "Run demo"
```
Chat screenshots (demo users, seeded messages) are in [`../chat_screenshots/`](../chat_screenshots), made by `py tests/chat_screenshots.py`.
Tests (with the server running): `py tests/unit.py`, `py tests/measure.py` (prints the measurements behind the limitations), and `py tests/e2e.py` (needs `pip install playwright` and `python -m playwright install chromium`). Accuracy tool: `py eval.py --dir samples` (synthetic) or `py eval.py` (your images in `real_samples/`).
Code walkthrough: [HOW_IT_WORKS.md](HOW_IT_WORKS.md) · Demo recording plan: [DEMO_SCRIPT.md](DEMO_SCRIPT.md) · Claim-by-claim evidence: [CLAIMS_AUDIT.md](CLAIMS_AUDIT.md)

## Built with
python · opencv · rapidocr · pymupdf · pillow · fastapi · javascript

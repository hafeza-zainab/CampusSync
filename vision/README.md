# CampusSync Vision — OpenCV AI Competition

> Drop in a timetable screenshot, a PDF notice or a page of notes. CampusSync reads it, finds every lecture and deadline, and files it into your Study Panel by **Course → Semester → Subject → Topic → Date**, with teacher and room when they are written on the page. No typing.

## Inspiration
Every semester students re-type the same timetable into a calendar, an attendance app and a study folder. Notices arrive as screenshots and PDFs in chat groups, so deadlines get buried. CampusSync already has a Study Panel (tagged resource sharing) and Attendance Management; Vision is the missing input layer.

## What it does
1. **Upload** an image or PDF (timetable, notice, notes).
2. **See the vision**: detected table cells (blue) and OCR text blocks (green) are drawn live over the image, with per-stage timings.
3. **Auto-tagging**: each lecture or deadline becomes `{course, semester, subject, topic, date, task, teacher, room}` and appears in the Study Panel with a confidence score. Teacher and room are marked **read from image** (solid) or **filled from catalog** (dashed); nothing is guessed.
4. **Course catalog**: pick a course and semester and only that semester's subjects are searched (`data/catalog.json`: courses → semesters → subjects → teacher/room).

## CampusSync as a whole, and where Vision fits
CampusSync is a college platform: attendance tracking, announcements, a Study Panel for tagged resources, and (planned) structured class chat. Vision is the module that removes manual data entry: it reads a screenshot or PDF and feeds the other parts.

**Implemented and tested** (browser-tested with headless Chromium on synthetic images and a scripted attendance app; not yet tried on real student screenshots):
- Vision pipeline: upload, deskew, table detection, OCR, extraction, auto-tagging, per-field accuracy tool (`eval.py`).
- **Post as announcement**: notice entries can be edited, flagged "check this" under 80% confidence, and posted into the existing Announcements tab. Duplicates (same subject + date + topic) are blocked.
- **Timetable → attendance**: a parsed timetable can replace the lecture timetable in the attendance app after a preview (added / removed lectures, lectures per week per subject, a warning for marks that would be hidden) and a confirm click. Marked attendance is never edited. Undo restores the old timetable.
- Attendance app fixes needed for the above: lecture times like `07-08` could not be parsed (attendance could not be marked), month buttons called missing functions, announcements showed "by undefined", and nothing was saved between page loads (announcements, timetable and attendance now persist in localStorage).
- The attendance app must be opened through the Vision server (`http://localhost:8000/campus/`); that is how the two share data.

**In progress / future work (not built, or not working):**
- **Structured class chat / note-request template**: planned, not implemented. `chatbot.html` is a stub whose buttons call a function that does not exist, so "Request notes" prefill was dropped.
- **Study Panel upload form** (`studypanel.html`): a form that posts to `/upload`, which does not exist. It is not linked from the app. The dashboard's Study Panel tab also calls a render function that points at a missing element.
- `checkWarnings()` (the "below 75%" alert) throws `subjectCount is not defined` after marking attendance; marking still works.
- Handwriting, SAM-style segmentation for borderless tables, and an LLM extraction pass are not built.
- No real-image accuracy is measured yet (see Results).
- `data/catalog.json` is seeded from `data.js`, which holds subject names only. Real teachers, rooms and the semester number must be added by hand; the demo courses A and B in the catalog are fake placeholders.

## How we built it (computer-vision pipeline)
| Stage | Technique |
|-------|-----------|
| Deskew | Canny edges + probabilistic Hough lines → median angle → affine warp |
| Contrast | CLAHE on the L channel of LAB colour space |
| Table segmentation | Adaptive threshold → morphological opening with long horizontal/vertical kernels → contour detection on the gaps → row/column grouping |
| Text detection + recognition | RapidOCR (PP-OCR ONNX models, CPU only); Tesseract fallback |
| Cell ↔ text assignment | Centre-point-in-rectangle matching |
| Understanding | Header-row detection, fuzzy subject matching against the user's own subjects, day-first date regexes, keyword task classification |
| PDF support | PyMuPDF renders pages to images, so PDFs reuse the same vision path |

Stack: Python, OpenCV, RapidOCR, PyMuPDF, FastAPI, vanilla JS canvas for the box overlay. It runs on CPU with no cloud calls, so a student's private documents never leave their machine.

## Challenges
- Photos are tilted and unevenly lit → deskew + CLAHE.
- OCR garbles subject names → fuzzy-match to known subjects (`OOP C+` → `OOP C++`).
- Timetables have no standard layout → find the header row dynamically instead of hard-coding positions.

## Results

### Real images
*Not measured yet.* Real-image results will be added from `eval.py` output (see [`README_RESULTS_TEMPLATE.md`](README_RESULTS_TEMPLATE.md)).

### Synthetic images (generated by `make_sample.py`; NOT real-world evidence)
Produced by `py eval.py --dir samples` — full output in [`eval_results_samples.md`](eval_results_samples.md). **8 synthetic images: 57/57 entries correct** (subject 57/57, day/time 57/57, teacher 8/8, room 8/8). These images were drawn by the same person who wrote the code, so passing them shows the code does what it was designed to do, not that it works on unseen real images.

| Synthetic input | Result |
|-------|--------|
| Timetable screenshot (5 days × 6 slots) | 42/42 cells found, 11/11 lectures correct |
| Same timetable rotated 2.5° with noise and uneven light | auto-corrected, 11/11 lectures correct |
| Same timetable, **days down the side** (transposed), course + semester chosen | 11/11 lectures correct |
| Timetable cells with subject + teacher initials + room (fake placeholder course, course + semester chosen) | 7/7 lectures; teacher 6/6, room 6/6 |
| Notice with 5 dated tasks, PNG | 5/5 correct (subject, date, topic, task) |
| Same notice as an **image-only PDF** (picture pasted in a PDF, like a scan) | 5/5 correct |
| Same notice as a **text-layer PDF** (selectable text, like a Word export) | 5/5 correct |
| Notice mentioning "Prof. ..." and "Room ..." (placeholder course) | 2/2 correct incl. teacher and room |

Across all synthetic images, eval reports that of the 8 correct teacher values 6 were read from the image and 2 filled from the catalog, and of the 8 correct room values 5 were read from the image and 3 filled from the catalog.

Both PDF types are rendered to an image and read with OCR; the PDF's own text layer is not used. Accuracy on real student screenshots and handwriting has not been measured yet.

## Limitations and what's next
- Handwriting is unreliable with general-purpose OCR; a handwriting-specific model is the next step.
- Borderless timetables need a learned segmentation model. SAM-style segmentation is the planned upgrade (it is not used in this version).
- Extraction is rule-based; an LLM pass could handle free-form notices.
- Feed the output into the Attendance calendar so one screenshot sets up a whole semester.

## Run it
```bash
cd vision
pip install -r requirements.txt
python make_sample.py                  # creates samples/
python -m uvicorn main:app --port 8000
# open http://localhost:8000 and click "Run demo"
```
Code walkthrough: [HOW_IT_WORKS.md](HOW_IT_WORKS.md) · Demo recording plan: [DEMO_SCRIPT.md](DEMO_SCRIPT.md)

## Built with
python · opencv · rapidocr · pymupdf · fastapi · javascript

# CampusSync Vision: technical report

**Status in one paragraph.** CampusSync is a working prototype of a college app (attendance, announcements, Study Panel, template-only chat) with a built-in computer-vision module, **Vision**, that reads a timetable screenshot, a notice (image or PDF) or a page of notes and turns it into structured entries. It runs **locally on a laptop**. It is **not deployed on AWS** (or on any cloud). Vision's accuracy has been measured on **synthetic images only**; **it has not been measured on real student screenshots.** Everything below is taken from the code and from test output that can be re-run; where something is untested, it says so.

## 1. Problem
Every semester a student re-types a timetable into a calendar or attendance tool, and copies deadlines out of screenshots and PDF notices that arrive in chat groups. This is slow and error-prone, and deadlines get missed. The goal of Vision is to read the screenshot or PDF directly, show what it found, and let a person approve it, so the data does not have to be typed by hand.

## 2. Users
- **Students** (view attendance and announcements, upload materials, use the chat templates).
- **CR / ACR** (class representatives: the roles that can post announcements, and who would typically import a timetable or notice).

These roles are the ones in the demo accounts (`DEMO-CS-001` CR, `DEMO-CS-002` ACR, `DEMO-CS-003` and `-004` students). No real users or real college data have been used.

## 3. System overview
A browser app (plain HTML/JavaScript) plus a small local Python server (FastAPI). The server hosts the app files and the Vision endpoint `POST /api/analyze`; the app stores its data in the browser's `localStorage`. See [architecture.md](architecture.md) for the data-flow diagram.

| Part | Technology (from `requirements.txt`) |
|---|---|
| Server | FastAPI 0.162.0, Uvicorn 0.54.0, python-multipart 0.0.32 |
| Computer vision | **OpenCV 5.0.0** (`opencv-python-headless==5.0.0.93`), NumPy 2.3.5, Pillow 12.0.0 |
| PDF | PyMuPDF 2.0 (pages rendered to images at 170 dpi, first 3 pages) |
| Text recognition (OCR) | RapidOCR 3.10.0 with onnxruntime 1.31.0 (CPU); the PP-OCRv6 detection and recognition models ship inside the pip package |
| Front end | vanilla JavaScript, `localStorage`, the browser `storage` event |

**OpenCV version.** The code runs on OpenCV **5.0.0**: `py -c "import cv2; print(cv2.__version__)"` prints `5.0.0`, and the unit test `tests/unit.py` contains a check ("the code runs on OpenCV 5") that fails if the major version is not 5. The package is `opencv-python-headless` (the same `cv2` module as `opencv-python`, without GUI window code, which the server does not use). The whole pinned set was installed in a fresh virtual environment and the unit tests, the evaluation and the browser smoke test were run from it.

## 4. OpenCV implementation
All of this is in `vision/pipeline.py`. OpenCV does the image geometry (deskew, contrast, table-structure detection). It is **not** used for text recognition: that is RapidOCR on onnxruntime.

| Stage | OpenCV functions | What they do here |
|---|---|---|
| Colour conversion | `cvtColor` (BGR/RGB/RGBA/GRAY, BGR to LAB) | Images are handled as BGR arrays; grayscale for edge and line work; LAB for contrast correction. |
| Size limit | `resize` (`INTER_AREA`) | Images longer than 2000 px on a side are shrunk so OCR stays fast. |
| Deskew | `Canny` (50, 150), `HoughLinesP` (1 px, π/360, threshold 120, minimum length = a quarter of the width, max gap 10), `getRotationMatrix2D`, `warpAffine` (`INTER_CUBIC`, `BORDER_REPLICATE`) | Long near-horizontal lines (within 15°) are found; their median angle is the tilt; if the tilt is between 0.3° and 15° the image is rotated back. |
| Contrast | `createCLAHE` (clip 2.0, 8x8 tiles) on the L channel, `split` / `merge` | Local contrast equalisation, intended for dim or unevenly lit photos. **No measurable effect on the synthetic samples** (identical output with and without it); its effect on real photos is untested. |
| Table grid | `adaptiveThreshold` (`ADAPTIVE_THRESH_MEAN_C`, `THRESH_BINARY_INV`, block 21, C 10), `getStructuringElement` (`MORPH_RECT`), `morphologyEx` (`MORPH_OPEN`) with a long horizontal and a long vertical kernel, `add`, `dilate`, `countNonZero` | Opening with a wide 1-pixel-tall kernel keeps only horizontal lines; a tall 1-pixel-wide kernel keeps only vertical lines; text is too short to survive. Their sum is the table skeleton. Too few line pixels means "no table". |
| Cells | `bitwise_not`, `findContours` (`RETR_LIST`, `CHAIN_APPROX_SIMPLE`), `boundingRect` | The empty regions between the lines are the cells. Specks and the page-sized region are dropped; `drop_containers` removes any region that contains other cells (this fixed a real bug, see section 6); `group_rows` sorts cells into rows. |
| Fallback decode | `imdecode` | Used only if Pillow cannot open an image. |

Non-OpenCV image handling: Pillow's `ImageOps.exif_transpose` applies the EXIF orientation tag of phone photos; PyMuPDF renders PDF pages.

**What happens after the vision stage (rule-based, no machine learning beyond the OCR models):**
- Cell text is assigned by centre-point-in-rectangle matching; columns are assigned by horizontal overlap with the header cell, for timetables with days across the top or down the side.
- Subjects are fuzzy-matched (`difflib`, similarity at least 0.85) against `data/catalog.json`, limited to the selected course and semester when one is chosen. A teacher or room is filled from the catalog only when the subject matched at 0.90 or better, and is always labelled "from catalog" versus "read from image". Nothing is guessed.
- Notices: day-first date formats, keyword task types, topic extraction. Teacher and room patterns (`Prof./Dr. Name`, catalog short codes, `Room 301`, `R-204`, `LH-3`).
- **Confidence** = OCR score of the text x subject-match similarity (0.85 if no known subject matched) x 0.9 when no course and semester were chosen, capped at 0.99. The OCR score is real model output; the two fixed factors are rules of ours. Below **0.80** an entry is flagged "check this".

## 5. Evaluation

### 5.1 Real images
**Not measured.** `vision/real_samples/` contains no labelled images. No number in this report applies to real student screenshots, photos or handwriting.

### 5.2 Synthetic images (regression tests, not evidence of real-world accuracy)
The 12 images were drawn by `vision/make_sample.py`, by the same author as the code, with answer files written alongside. Passing them shows the code does what it was designed to do. Output of `py eval.py --dir samples` (file `vision/eval_results_samples.md`):

| Image | Result |
|---|---|
| Timetable screenshot, 5 days x 6 slots | 42/42 cells, 11/11 lectures |
| Same, rotated 2.5° with noise and uneven light | 11/11 |
| Same, JPEG with EXIF rotation tag 6 / tag 3 | 11/11 each |
| Same, on an A4 PDF page | 42 cells, 11/11 |
| Same, days down the side | 11/11 |
| A different weekly timetable (used in the demo) | 30 cells, 10/10 |
| Cells with subject + teacher initials + room (placeholder course) | 7/7; teacher 6/6, room 6/6 |
| Notice with 5 dated tasks: PNG, image-only PDF, text-layer PDF | 5/5 each |
| Notice with "Prof." and "Room" (placeholder course) | 2/2 incl. teacher and room |

Total: **100/100 entries**; subject 100/100, day/time 100/100, teacher 8/8, room 8/8. Of the correct teacher values 6 were read from the image and 2 filled from the catalog; of the room values 5 and 3. Time per image on the author's PC (CPU only, Python 3.14): about 1 to 2 s for images, up to about 5.5 s for the image-only PDF in one run; the committed file reports a 1.7 s mean.

### 5.3 Other tests
- `tests/unit.py`: 45 checks of the extraction rules (patterns recognised and not recognised, the fuzzy-match limits, the confidence formula) and that OpenCV is version 5.
- `tests/smoke_app.py`: 16 browser checks (headless Chromium) of the current app: login and roles, the Import card, notice to announcements, timetable to calendar, template-only chat, the semester calendar.
- `tests/e2e.py` (169 checks) and `tests/demo_walkthrough.py` were written for an earlier version of the app and **no longer match it**; they are not evidence for the current app.
- Not tested: real data, browsers other than Chromium, phones, screen readers, any operating system other than Windows, any Python other than 3.14.

### 5.4 Failure cases (measured by `tests/measure.py` on synthetic images)
| Input | What happens |
|---|---|
| Picture rotated 90° with **no** EXIF tag | 1 entry instead of 11 |
| Picture upside-down with **no** EXIF tag | 11 entries, several with garbled subject names |
| Timetable drawn **without table lines** | one meaningless "notes" entry; not supported |
| Handwriting | not tested; the OCR models are general printed-text models |
| PDF with more than 3 pages | only the first 3 are read, only the first is previewed |

### 5.5 Bugs found by testing and fixed
- RapidOCR's text-direction check turned the header `08-09` into `60-80` at 99.9% confidence (digits look alike when rotated 180°). It is now disabled (`use_cls=False`), which is why upside-down images without an EXIF tag are not supported.
- A timetable on an A4 PDF page produced one oversized false "cell" that shifted the columns (a lecture on the wrong day and a bogus lecture). Fixed by dropping cells that contain other cells and assigning columns by position.
- A subject-match threshold of 0.78 matched "Placeholder Seminar" to "Placeholder Chemistry" and copied its teacher and room. Raised to 0.85, with catalog filling only at 0.90 or better.

## 6. Limitations
- No real-image accuracy measurement (5.1). Handwriting untested.
- Orientation without an EXIF tag, tables without lines and long PDFs are not supported (5.4).
- Dates are read day-first (`14/11/2026`); other formats, languages and layouts than those in the tests may be missed. Extraction is rule-based, not a language model.
- **The app is a front-end demo:** data lives in each browser's `localStorage` (a few MB, editable by anyone with that browser profile), with no server database. Study files are limited to 1 MB.
- **Passwords are demo-only:** they are written in plain text in `store.js` and shown on the login screen. This is **not** secure authentication.
- **The chat uses simulated users in one browser with no server sync;** it is not real-time chat between devices.
- Semesters 1-3, 5 and 6 in `data.js` are placeholders (invented dates and subjects).

## 7. Responsible use
- **Privacy of student data.** The server contains no outbound network calls (nothing is sent to a cloud service), the OCR models ship inside the pip package, and in the browser tests the page made no requests outside `localhost`. The server does **not** keep the uploaded file or the image. It does keep, in `vision/data/entries.json`, the extracted entries (subject, date, topic, task, teacher, room, confidence, the source file name and, for notices, the original sentence). That file is excluded from the repository by `.gitignore`. Anyone who deploys this with real student data would need to add proper storage, access control and retention rules; none exist now.
- **Human review.** Vision never writes to the calendar or announcements by itself. Notice entries are shown in an editable review card; entries under 80% confidence are flagged "check this" and cannot be posted until the user ticks that they checked them. A timetable replacement shows a preview of what is added and removed and a warning about attendance marks that would be hidden, needs a click, never edits attendance marks, and can be undone. Study Panel entries from Vision carry their source and the "check this" flag.
- **No real IDs.** All accounts use placeholder college IDs (`DEMO-CS-001` to `-004`) and made-up names; no phone number, email or real name is collected anywhere in the app. All images used for testing are synthetic.
- **Honest labelling.** The demo timetable is labelled "synthetic sample", the chat is labelled as simulated, and the README and this report state that accuracy on real data is unknown.
- **Fairness note.** The OCR models and the date and name patterns were only exercised on English, printed, synthetic text. Performance on other scripts, handwriting or unusual layouts is unknown and could be worse; low-confidence flags and the review step are the safeguard, not a guarantee.

## 8. Deployment
**Not deployed on AWS, and not deployed anywhere.** The project runs locally (`run.bat`, then `http://localhost:8000/`). No AWS service was used or tested. *(This section will be extended only if a deployment is actually made and tested.)*

## 9. Reproducing the results
```
py -m pip install -r requirements.txt                # exact tested versions
py -c "import cv2; print(cv2.__version__)"           # 5.0.0
cd vision
py tests/unit.py                                     # 45 checks
py eval.py --dir samples                             # 12 synthetic images, writes eval_results_samples.md
# browser smoke test: install vision/requirements-dev.txt, run `py -m playwright install chromium`,
# start the server (run.bat), then:
py tests/smoke_app.py                                # 16 checks
py tests/measure.py                                  # the failure cases in 5.4
```

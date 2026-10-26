# Claims audit: README.md, HOW_IT_WORKS.md, DEMO_SCRIPT.md

Evidence key: **U** = `tests/unit.py` (44 checks) · **E** = `tests/e2e.py` (103 browser checks) · **V** = `eval_results_samples.md` (`py eval.py --dir samples`, synthetic) · **M** = `tests/measure.py` (printed measurements) · **code** = the cited function.
"Synthetic" = images drawn by `make_sample.py`. **Nothing here is evidence about real student images.**

Status: **backed** = evidence exists and matches · **softened** = wording changed to match the evidence · **removed** = no evidence, claim deleted · **flag** = depends on facts only the author can confirm.

## README.md

| # | Claim | Evidence | Status |
|---|---|---|---|
| 1 | Finds the table, reads text with OCR, turns lectures/dated tasks it recognises into tagged entries | V (synthetic), E demo/catalog | backed, "every lecture and deadline" → "the lectures and dated tasks it recognises" |
| 2 | Entries can be posted as announcements / loaded into the attendance calendar after review | E (announcements, attendance bridge) | backed |
| 3 | "Working prototype, tested on synthetic images… not measured on real" | `real_samples/` has only a README | backed |
| 4 | Motivation: "students re-type timetables into 4 apps…", "CampusSync already has a Study Panel" | none (anecdote); Study Panel is not working | **removed**: replaced with a neutral sentence; Study Panel listed as in progress |
| 5 | Detected cells/text blocks drawn over the image with per-stage timings | E demo (boxes drawn, 5 steps ticked, "42 cells") | backed |
| 6 | Entry fields incl. teacher/room, confidence score | code `parse_*`, E catalog | backed |
| 7 | Teacher/room marked image vs catalog; left empty when neither has them ("nothing is guessed") | U (patterns), E catalog (dashed chips, expansion), E "course only / nothing chosen never fills" | backed; "nothing is guessed" → "left empty when neither source has them" (OCR can still misread) |
| 8 | Course + semester limit the subjects searched | U ("catalog scope"), E | backed |
| 9 | "Study Panel" the entries are filed into | it is the list on the Vision page (`data/entries.json`), not the attendance app's Study Panel | **corrected** and stated explicitly |
| 10 | "Implemented and tested" list | E, U | backed; "tested" now defined as the scripted checks, run on synthetic data |
| 11 | Post as announcement: edit, "check this" < 80%, duplicates blocked | E (edit → 1 posted + 4 blocked; low-confidence refused until ticked; Post all skips unchecked) | backed |
| 12 | Timetable → attendance: preview, hidden-mark warning, confirm, never edits attendance, Undo | E (7 checks) | backed |
| 13 | Fixes to the attendance app (time format, month buttons, "by undefined", persistence) | E (marking works, month buttons, role shown, marks survive reload) | backed |
| 14 | App must be opened via `/campus/` | M §7: the same app from `file://` sees `None` | backed |
| 15 | (was) Chat template not implemented; `chatbot.html` stub calls missing function | superseded: the Chat tab was built (rows C1-C14 below); the stub was replaced and E checks `handleResponse` is gone | updated |
| 16 | `studypanel.html` posts to `/upload` which does not exist; not linked | code: `grep studypanel index.html` finds nothing; no `/upload` route in `main.py` | backed |
| 17 | Dashboard Study Panel tab "calls a render function pointing at a missing element" | code: `renderMaterials()` targets `#materials`, page has `#materialsList`, and nothing calls it on tab open | **corrected** (the old wording said the tab calls it) |
| 18 | `checkWarnings()` throws `subjectCount is not defined` | observed in every browser run; E whitelists exactly this error | backed |
| 19 | SAM / handwriting / LLM not built | code | backed |
| 20 | Deskew technique (Canny, Hough, median angle, warp) | code `estimate_skew`, `preprocess`; V (2.5° synthetic tilt, 11/11) | backed |
| 21 | CLAHE improves contrast / helps with uneven light | M §1: identical output with and without CLAHE on 2 synthetic images | **softened**: "applied; no measurable effect on the synthetic samples" |
| 22 | Table segmentation steps | code `find_grid`, `drop_containers` | backed |
| 23 | RapidOCR (PP-OCR ONNX models, CPU only) | M §6 (models inside the pip package); onnxruntime CPU provider | backed |
| 24 | "Tesseract fallback" | code exists, never run | **softened**: "exists in the code but has never been run" |
| 25 | Cell ↔ text by centre point; columns by horizontal overlap | code `text_in_cell`, `header_index`; V (`timetable_pdf`, previously failing) | backed |
| 26 | Fuzzy match 0.85; day-first dates; keyword tasks; teacher/room patterns | U | backed |
| 27 | Confidence formula | U (formula checks), code `entry_confidence` | backed |
| 28 | "Runs on CPU with no cloud calls, so private documents never leave their machine" | no outbound calls in `*.py` (grep), M §6 (models bundled), E ("no requests outside localhost") | **softened**: qualified to "run locally as described", install needs internet once |
| 29 | Challenges: "photos are tilted and unevenly lit → deskew + CLAHE" | tilt: V; CLAHE: none | **replaced** by "Problems found while testing", each real and reproducible (OCR `08-09`→`60-80`, PDF column shift, 0.78 threshold) |
| 30 | "OCR garbles subject names → fuzzy-match (`OOP C+` → `OOP C++`)" | U (typed examples only, not real OCR errors) | **softened** (moved to a table row; no claim about real OCR errors) |
| 31 | "Timetables have no standard layout → find header row dynamically" | V: two layouts (across, down) | **softened** to the two tested layouts |
| 32 | Results: real = not measured | `real_samples/` empty | backed |
| 33 | Synthetic table values (42/42, 11/11, 7/7, 5/5, 2/2, teacher 6/6, room 6/6) | V | backed (copied from V output) |
| 34 | "11 images: 90/90; subject 90/90…; mean 1.7 s; teacher 6 image/2 catalog; room 5/3" | V | backed; **no longer the headline**, labelled as regression tests |
| 35 | "PDF's own text layer is not used" | code `load_pages` | backed |
| 36 | Limitation: EXIF handled, no-EXIF rotation unsupported (1 entry vs 11; garbled names) | M §2 | backed; "garbled names" softened to "several garbled" (2 of the first 4 were wrong) |
| 37 | Limitation: tables without lines unsupported (1 meaningless entry) | M §3 | backed (this replaced an untested claim that it "falls back to free text") |
| 38 | Limitation: handwriting untested | no handwriting image anywhere | backed |
| 39 | Limitation: first 3 PDF pages read, only page 1 previewed | M §5, code `load_pages` / `analyze` | backed |
| 40 | Old "Feed the output into the attendance calendar so one screenshot sets up a whole semester" | now implemented for the weekly timetable (E); "whole semester" was never true (holidays/dates unused) | **removed** from future work (stale) |
| 41 | `pip install -r requirements.txt` works | fresh venv on Windows/Python 3.14: install OK, imports OK, server returned 11 entries, `unit.py` 44/44 (done once by hand; not in the repo) | backed, stated as such. Note: a very long folder path can break pip on Windows (260-character limit) |

## HOW_IT_WORKS.md

| Claim | Evidence | Status |
|---|---|---|
| Image = numpy array `img[y][x] = (b,g,r)` | OpenCV basics; `decode_image` | backed |
| Load: PNG/JPG via `cv2.imdecode` | stale: now Pillow + `exif_transpose` | **fixed** |
| EXIF handling, no tag = unsupported | V (exif6/exif3), M §2 | backed |
| CLAHE "so dim photos are readable" | M §1 | **softened** |
| Morphology: "text is too short to survive" | code `find_grid` + V | backed |
| "group_rows sorts into rows and columns" | code; columns now by overlap | **fixed** |
| Timetable parse: "row's first cell is the time", index-based | stale | **fixed** (time = first time-like cell; columns by overlap) |
| Notice parse formats | U (6 date formats), V | backed |
| Notes with no dates | M §4 (one synthetic image) | backed + "only tried on one synthetic image" |
| "Borderless timetables fall back to free-text mode, which suits notices" | M §3: result is 1 meaningless entry | **fixed** |
| "SAM would be the upgrade…" | speculation | **softened** ("possible future upgrade, not tried") |
| eval: "pairs by key subject + day" | stale: now slot pairing | **fixed** |
| Bridge: "only a fixed list of files so `.git` and your data are not exposed" | E (404 for `.git`, `main.py`) | backed; "your data" → "Python source" |
| Bridge: "three keys" | now four (backup key) | **fixed** |
| Post as announcement steps 1–5 | E | backed; confidence sentence now points to one formula |
| Small fixes table | git history, E; `parseEndTime` hours < 7 = afternoon verified for 06/01 in a browser | backed |
| Catalog scope table | U, E | backed |
| Fuzzy 0.85, examples 0.92 / 0.86, earlier 0.78 mismatch | U, session history | backed |
| Teacher/room source semantics | U, E | backed |
| "`CSE` is never turned into a teacher" | U: bare `CSE` ignored, but `Dr. CSE` IS read as a teacher | **softened** (documented the exception) |
| Confidence formula & 0.80 flag | U, E | backed |
| OCR upside-down check: `08-09`→`60-80`, now `use_cls=False` | observed, fix in `run_ocr`; V (transposed 11/11) | backed |
| eval per-field accuracy | V columns; U (helpers) | backed |
| Timetable → attendance steps 1–6 | E | backed |

## DEMO_SCRIPT.md

| Claim | Evidence | Status |
|---|---|---|
| "Wait ~15 s for the OCR model to pre-load" | server start-up warm-up in `main.py`; observed ~15 s | backed (approximate) |
| Browser zoom ~110% | at 1400×1000 the page is ~1250 px tall at 100% | **corrected** → 75–80% (see CHECKLIST.md) |
| "OpenCV finds the table grid: 42 cells" | E (step list says 42 cells) | backed (for this image) |
| "No templates" | code: no template matching | removed from overlay (not needed) |
| "Every semester I re-type my timetable into 4 apps." | none; invented by me | **removed** |
| "Runs on CPU, offline" | E (no external requests) | softened to "Runs locally on CPU" |
| "Works on notices and PDFs too" | V (synthetic) | removed from the 60 s overlay unless a notice is shown on screen |
| "Right panel: Semester > Subject" | stale | **fixed** (Course > Semester > Subject) |
| "Animation takes about 8 s on top of processing" | M §7: 6.4 s total, once | **corrected** |
| "Re-uploading never creates duplicates" | dedupe key is course+semester+subject+date+topic | **softened** |
| "Demo image is synthetic" | by construction | stated up front |

## Claims that depend on you (flag)
- Anything about your own experience (why you built it) is yours to write; I removed the numbers I had invented.
- The `main` course name, semester id (`sem4`), teachers and rooms in `data/catalog.json` are placeholders or guesses until you edit them.

## Chat tab (added later; README "Chat tab" bullet, HOW_IT_WORKS "The Chat tab")

| # | Claim | Evidence | Status |
|---|---|---|---|
| C1 | Class group + one-to-one chats, last-message preview, unread counts | E `test_chat` (conversation list, badge 2 on Meera, cleared on open, privacy: Aarav cannot see Zainab/Meera) | backed |
| C2 | Enter sends, Shift+Enter new line, empty ignored, newest message in view | E | backed |
| C3 | Typed HTML cannot break the page (textContent) | E: `<b>`/`<img onerror>` shown as text, no elements created, `window.__pwned` unset. Not a security audit: only HTML in message/topic text was tried | backed (narrowly) |
| C4 | Note request form has only Subject, Date, Topic | E: the dialog contains exactly select + date + text inputs | backed |
| C5 | Date defaults to today; topic required and max 80; subjects from the timetable | E | backed |
| C6 | Request card Open → Shared with name and time, requester sees it live, third user sees Shared, requester has no button | E (3 tabs) | backed |
| C7 | Two tabs of one browser stay in sync (storage event) | E (message, unread badge, request status) | backed |
| C8 | **"Real-time multi-user chat"** | none: users are simulated, one browser, no server | **not claimed**; README states "simulated users in one browser, no server sync" |
| C9 | Messages persist and Reset chat restores seed data (two clicks, no popup) | E | backed |
| C10 | No alert()/confirm() popups in the chat | E (dialog listener across the whole chat test) | backed |
| C11 | Readable at 1920x1080 and 1366x768: no horizontal scroll, no chat text under 13px, composer inside the screen, visible focus outline | E (both sizes; Tab from the message box reaches Send with a 3px outline) | backed. Not tested: other sizes, zoom levels, screen readers (labels and roles were added but never tried with one) |
| C12 | Vision "Request notes" link pre-fills the form, requires normal login first, never sends | E `test_chat_prefill` (11 checks) | backed |
| C13 | The link does not change the Vision page layout or the recorded demo | E: Study Panel height identical with and without the links (1223 px); link has opacity 0 until hover/focus | backed (appearance on hover only) |
| C14 | `app.js`, `style.css`, `data.js` not edited; `index.html` has one added line | `git diff vision-integrations chat-tab -- app.js style.css data.js index.html` | backed |

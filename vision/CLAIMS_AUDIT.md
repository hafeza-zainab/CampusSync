# Claims audit: README.md, HOW_IT_WORKS.md, DEMO_SCRIPT.md

Evidence key: **U** = `tests/unit.py` (44 checks) · **E** = `tests/e2e.py` (169 browser checks) · **W** = `tests/demo_walkthrough.py` (9 checks) · **V** = `eval_results_samples.md` (`py eval.py --dir samples`, synthetic) · **M** = `tests/measure.py` (printed measurements) · **code** = the cited function.
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
| 9 | (was) "The Study Panel Vision fills is a list on the Vision page, not connected to the attendance app" | superseded: Vision now also writes every entry into the app's Study Panel (E `test_import`, `test_study`); the Vision page keeps its own list too | updated |
| 10 | "Implemented and tested" list | E, U | backed; "tested" now defined as the scripted checks, run on synthetic data |
| 11 | Post as announcement: edit, "check this" < 80%, duplicates blocked | E (edit → 1 posted + 4 blocked; low-confidence refused until ticked; Post all skips unchecked) | backed |
| 12 | Timetable → attendance: preview, hidden-mark warning, confirm, never edits attendance, Undo | E (7 checks) | backed |
| 13 | Fixes to the attendance app (time format, month buttons, "by undefined", persistence) | E (marking works, month buttons, role shown, marks survive reload) | backed |
| 14 | App must be opened via `/campus/` | M §7: the same app from `file://` sees `None` | backed |
| 15 | (was) Chat template not implemented; `chatbot.html` stub calls missing function | superseded: the Chat tab was built (rows C1-C14 below); the stub was replaced and E checks `handleResponse` is gone | updated |
| 16 | (was) `studypanel.html` posts to `/upload` which does not exist; not linked | still true of that standalone file (unused). The Study Panel **tab** was rebuilt (`study.js`, E `test_study`) | updated |
| 17 | (was) The dashboard Study Panel tab shows an empty list | superseded: the tab works (tags, filters, files up to 1 MB, Vision entries; E `test_study`) | updated |
| 18 | (was) `checkWarnings()` throws `subjectCount is not defined` | superseded: fixed; the 75% warning is a visible banner (E `test_attendance`: banner, 75% exactly not flagged, no page errors) | updated |
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

## The integrated app (added later; README "CampusSync as one product", HOW_IT_WORKS sections of the same names)

| # | Claim | Evidence | Status |
|---|---|---|---|
| A1 | Attendance by month / day / subject; the month starts as the current month | E `test_attendance` | backed |
| A2 | Attended = green, not attended = red, unmarked = neutral grey | E: computed colours `rgb(46,204,113)`, `rgb(231,76,60)`, `rgb(204,204,204)` | backed |
| A3 | Side panel: per subject held / attended / absent / unmarked / this month's total / percent | E (Hindi: "3 of 4 held attended: 75%", "N this month", "1 absent") | backed |
| A4 | 75% warning works, is visible without a popup, and 75% exactly is not flagged | E | backed |
| A5 | Attendance tab shows the same numbers as a table + overall figure | E | backed |
| A6 | Stored attendance shape unchanged (`{"YYYY-M-D-Subject-time": "present"|"absent"}`) | E (regex check of every stored key) | backed |
| A7 | A lecture that is not over cannot be marked | E | backed |
| B1 | Login with a college ID; invalid IDs rejected inline (empty, too short, spaces, symbols, leading hyphen) | E `test_login` | backed |
| B2 | No phone number or email field anywhere in the app | E: no input whose type/id/name/placeholder/label matches phone/mobile/tel/email; the only login text field is the ID | backed (for the fields of the app; it cannot prove nothing else collects data) |
| B3 | The ID is the identity: attendance per ID, announcement author, chat sender | E: another ID sees none of the first ID's marks and gets them back on return; announcement shows `DEMO-CS-001 (CR)`; chat shows `Aarav (DEMO-CS-002)` | backed |
| B4 | Demo IDs are placeholders, not real people's | by construction (`DEMO-CS-001`...); README states it | backed |
| B5 | **Login is secure / authenticated** | not claimed: there is no password in the committed code; README says so | **not claimed** |
| C1 | "Import from screenshot" opens Vision inside the app; a back link exists on the standalone page | E `test_import` | backed |
| C2 | A timetable goes to the calendar after the existing preview + confirm, live, with Undo | E, W | backed |
| C3 | Notices go to Announcements (existing review card), authored by the logged-in ID, live | E, W | backed |
| C4 | All entries go to the Study Panel with source and who added them | E (5 notice + 7 lecture entries), W | backed |
| C5 | The embedded Vision frame is usable (not the 300x150 default; grows to fit its content) | E (frame 1424x772 at first, then grows, e.g. 2324 px) | backed. This was a real bug found by looking at a screenshot, not by the first tests |
| D1 | Study Panel: tags Semester / Subject / Topic / Date; filters for each | E `test_study` | backed |
| D2 | Files up to 1 MB stored as data URLs and downloadable; larger refused with a message | E (exact bytes round-trip; 1 MB + 10 bytes refused) | backed |
| D3 | Storage-full is reported and nothing half-saved appears | E (simulated by making `setItem` throw `QuotaExceededError`) | backed (simulated, not a real full disk) |
| D4 | Vision entries are marked with their source and an amber "check this" under 80% | E (7 flagged unscoped timetable entries; confident notice entries not flagged) | backed |
| D5 | You can remove your own items, not someone else's | E (an item injected for another ID has no Remove button) | backed |
| E1 | Chat: class group and one-to-one, with unread counts and last-message preview | E `test_chat` | backed |
| E2 | **No free text:** no text box or textarea in the chat; only three templates, each with exactly Subject, Date, Topic | E | backed |
| E3 | Request notes → "I have these notes" → Shared (who, when); Ask a doubt → "I can help" → Answered; Notes shared has no flow; the sender has no answer button | E (3 tabs) | backed |
| E4 | Two tabs of one browser stay in sync (messages, unread badge, answers) | E | backed |
| E5 | **"Real-time multi-user chat"** | none: simulated users, one browser, no server | **not claimed**; README states "simulated users in one browser, no server sync" |
| E6 | Typed HTML cannot break the page; text uses textContent | E (HTML in a topic shown literally; no `<b>`/`<img>` created). Not a security audit | backed (narrowly) |
| E7 | Quality bar at 1920x1080 and 1366x768: no horizontal scroll, no chat text under 13px, buttons on screen, visible focus outline, no popups | E | backed. Not tested: other sizes, zoom, screen readers |
| E8 | Vision's "Request notes" link pre-fills the form, needs the normal login, never sends, does not change the Vision layout | E `test_chat_prefill` | backed |
| F1 | The proposed 90-second flow works in order, with the timings shown | W (9 checks, scripted clicks: about 17 s total; the OCR waits are about 5-7 s per upload) | backed for the scripted flow; a person is slower, so the 90 s figure in DEMO_FLOW_PROPOSAL.md is an estimate |
| F2 | `app.js`, `index.html`, `style.css`, `data.js` edits are small and listed | `git diff 08a603e HEAD -- app.js index.html style.css data.js` (reviewed) | backed |

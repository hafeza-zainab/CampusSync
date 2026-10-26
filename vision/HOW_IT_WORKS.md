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
   - *Timetable* (`parse_timetable`): the row with the most day names is the header. For every other cell, the OCR text inside it is the subject and the row's first cell is the time. Subjects are fuzzy-matched (`difflib`) against the ones in your `data.js`, so "OOP C+" still becomes "OOP C++". Date = next occurrence of that weekday.
   - *Notice* (`parse_notice`): OCR boxes at the same height are joined into lines. Each line with a date (`14 Nov 2026`, `14/11/2026`, `Nov 25`) becomes one entry. Subject comes from your known list or a `Subject:` prefix, task from keywords (submit / viva / quiz ...), topic is the words after "on".
   - *Notes with no dates* (`parse_notes`): first line is the topic, dated today.
6. **Auto-tag.** `main.py` saves `{semester, subject, topic, date, task}`, skipping duplicates. The page groups them Semester > Subject > date.

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

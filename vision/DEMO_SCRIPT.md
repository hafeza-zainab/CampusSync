# 60-second demo - screen record only, no face, no audio

**Before recording (2 min)**
1. In a terminal: `cd vision` then `py -m uvicorn main:app --port 8000`. Wait ~15 s (the OCR model pre-loads), then open http://localhost:8000
2. Click **Reset panel** so the right side is empty. Browser zoom ~110%, hide the bookmarks bar.
3. Start your screen recorder. The page already shows big captions by itself, so the overlays below are *extras* you add in a video editor (CapCut / Clipchamp). The demo makes sense even without them.
4. Click **Run demo**. It loads `samples/timetable.png` for you, so there is no file-picker fumbling.

| Time | What is on screen | Text overlay to add |
|------|-------------------|---------------------|
| 0:00-0:06 | Empty page, cursor over the drop zone | **"Every semester I re-type my timetable into 4 apps."** |
| 0:06-0:12 | Click *Run demo*; the Course/Semester dropdowns fill themselves and the screenshot appears (caption says "synthetic sample") | **"Drop in one screenshot."** |
| 0:12-0:22 | Blue boxes pop onto every table cell | **"OpenCV finds the table grid: 42 cells, no templates."** |
| 0:22-0:30 | Green boxes on every text block | **"OCR reads each block."** |
| 0:30-0:38 | Amber highlights on filled cells; step list ticks | **"Subject, day, time, task extracted."** |
| 0:38-0:50 | Right panel fills: Semester > Subject > date chips | **"Auto-tagged into the Study Panel. Zero typing."** |
| 0:50-0:56 | Hold on the step list with timings in ms | **"Runs on CPU, offline."** |
| 0:56-1:00 | Optional: drop `notice.png`, 5 dated tasks appear | **"Works on notices and PDFs too."** then end card **CampusSync Vision** |

**Tips**
- The demo image is synthetic and the course shown is the one seeded from `data.js`. Say so in the Devpost text; do not present it as real data.
- After a timetable upload a card "4 · Add this timetable to the attendance app" appears at the bottom. For a vision-only demo, do not scroll down to it; the Study Panel fills at the top right.
- Do one dry run first. The animation itself takes about 8 s on top of processing time, so trim dead air in the editor to fit 60 s.
- Pause 1 second on the filled Study Panel at the end. Judges read slowly.
- If a take goes wrong: *Reset panel*, run again. Re-uploading never creates duplicates.

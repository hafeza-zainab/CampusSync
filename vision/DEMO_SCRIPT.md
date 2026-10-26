# 60-second demo - screen record only, no face, no audio

> This is the **vision-only** 60-second plan. A 90-second flow through the whole CampusSync app (import, attendance, announcements, Study Panel, chat) is proposed in [DEMO_FLOW_PROPOSAL.md](DEMO_FLOW_PROPOSAL.md); its overlays are not written until you approve it. Note: the standalone Vision page now has a small "← Back to CampusSync" link in its header, which will be visible in a vision-only recording.

The demo uses a **synthetic** timetable image (drawn by `make_sample.py`) and the course seeded from `data.js`. Say so in the Devpost text and in the video ("synthetic sample"); do not present it as real data. Every overlay below states only what the screen shows.

**Before recording**: follow [CHECKLIST.md](CHECKLIST.md) (server, URLs, catalog edits, reset, browser zoom 75-80%) and read its list of things not to demo.

| Time | What is on screen | Text overlay to add |
|------|-------------------|---------------------|
| 0:00-0:06 | Empty page, cursor over the drop zone | **"CampusSync Vision: from a timetable screenshot to tagged entries."** |
| 0:06-0:12 | Click *Run demo*; the Course/Semester dropdowns fill themselves and the screenshot appears (caption says "synthetic sample") | **"Upload a timetable screenshot (synthetic sample)."** |
| 0:12-0:22 | Blue boxes pop onto every table cell | **"OpenCV finds the table grid: 42 cells."** |
| 0:22-0:30 | Green boxes on every text block | **"OCR reads each text block."** |
| 0:30-0:38 | Amber highlights on filled cells; step list ticks | **"Subject, day, time and task are extracted."** |
| 0:38-0:50 | Right panel fills: Course > Semester > Subject > date chips | **"Tagged by Course, Semester, Subject, Date."** |
| 0:50-0:56 | Hold on the step list with timings in ms | **"Runs locally on CPU."** |
| 0:56-1:00 | End card | **CampusSync Vision** |

Optional extra 10 seconds (only if you show it on screen): scroll to card 4 and show the timetable → attendance preview (added / removed lectures, the warning about marks that would be hidden). Do not add a line about notices or PDFs unless you also show a notice upload.

**Tips**
- Timing, measured once: from clicking *Run demo* to the "6 · Auto-tagged" caption took about 6.5 s on the author's PC. The rest of the 60 s is you holding on screens; hold ~1 s longer on each stage or speed up the take in the editor.
- After a timetable upload a card "4 · Add this timetable to the attendance app" appears at the bottom. For a vision-only demo, do not scroll down to it.
- Keep the mouse off the lecture rows in the Study Panel: a small "Request notes" link (for the chat) appears when you hover a row.
- Pause 1 second on the filled Study Panel at the end.
- If a take goes wrong: *Reset panel*, run again. Within the same course and semester, entries with the same subject, date and topic are not saved twice.

# real_samples/ — your real test images

Put real screenshots, phone photos or PDFs here. For each one you want measured, add a truth file with the **same name** and the extension `.truth.json`:

```
real_samples/
  my_timetable.png
  my_timetable.truth.json      <- answer key for my_timetable.png
  dept_notice.pdf
  dept_notice.truth.json
  random_photo.jpg             <- no truth file = "unlabelled": still usable in the UI, skipped by eval.py
```

Run from the `vision/` folder:

```
py eval.py
```

This prints a results table and writes `eval_results.md`.

Tip: write the truth file by reading the image yourself, **not** by copying what the app extracted. Otherwise the score is meaningless.

## Truth file for a timetable

`"mode": "timetable"`. One entry per filled cell.

| key | required | meaning |
|---|---|---|
| `course`, `semester` (top level) | no | catalog ids from `data/catalog.json`. If present, eval runs the pipeline with that course + semester chosen, exactly like picking them in the dropdowns. If absent, nothing is chosen. |
| `subject` | yes | the subject as it should be named |
| `day` | yes | `Monday` ... |
| `time` | no | e.g. `07-08`. If present it must match too |
| `teacher` | no | the teacher you expect on the entry (full name; initials such as `AP` also count if they abbreviate it). Scored only if present |
| `room` | no | e.g. `LH-3`, `Room 301`. Scored only if present |

```json
{
  "mode": "timetable",
  "course": "main",
  "semester": "sem4",
  "entries": [
    {"subject": "Hindi",   "day": "Monday",  "time": "07-08"},
    {"subject": "OOP C++", "day": "Monday",  "time": "08-09", "teacher": "Dr. Asha Rao", "room": "LH-3"},
    {"subject": "Python",  "day": "Tuesday", "time": "10-11"}
  ]
}
```

Days across the top or down the side both work. If your subject is not in the catalog, the app keeps whatever OCR read, so write what is printed on the image.
`teacher` and `room` are the FINAL values you expect, whether they are written in the image or would come from the catalog. The report says which of the two it was.

## Truth file for a notice

`"mode": "notice"`. One entry per dated task. `subject` and `date` (`YYYY-MM-DD`) are required and must match exactly. `topic` and `task` are optional and compared with fuzzy matching (default thresholds: topic 0.80, task 0.70; change with `--topic-min` / `--task-min`). `teacher` and `room` are optional, as above. `course` / `semester` at the top level work the same way.

```json
{
  "mode": "notice",
  "course": "main",
  "semester": "sem4",
  "entries": [
    {"subject": "DAA", "date": "2026-11-14", "topic": "Dynamic Programming", "task": "Submit assignment"},
    {"subject": "EVS", "date": "2026-11-25", "topic": "Water Pollution", "task": "Exam / test", "teacher": "Prof. Sharma", "room": "R-204"}
  ]
}
```

`task` uses the labels the app produces: `Submit assignment`, `Lab / viva`, `Exam / test`, `Project / demo`, `Deadline`, `Task`, `Revise notes`, `Attend lecture`. If you leave `task` or `topic` out, that field is not checked.

A notice with a date but no obvious subject gets the subject `General`.

## What the columns mean

| column | meaning |
|---|---|
| expected / extracted | entries in your truth file / entries the pipeline produced |
| correct | every field that is scored for that entry is right |
| partial | paired with an extracted entry, but at least one scored field is wrong (not counted correct) |
| missed | in truth, nothing extracted in that slot |
| extra | extracted, paired with nothing |
| subject, day/time, teacher, room | right/scored for each field separately. `–` = no truth entry has that field |

Entries are paired by **slot** (timetable: day, plus time if you wrote one; notice: date). Same slot but wrong subject shows up as "subject expected X got Y" in the Details list.

## Privacy

Real timetables and notices can contain names or other personal details. Before you `git add` anything here (and before publishing the repo for Devpost), blur or crop them, or keep them out of the repo.

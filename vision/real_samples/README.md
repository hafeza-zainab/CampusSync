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

`"mode": "timetable"`. One entry per filled cell. `subject` and `day` are required; `time` is optional (if you include it, it must match too).

```json
{
  "mode": "timetable",
  "entries": [
    {"subject": "Hindi",   "day": "Monday",  "time": "07-08"},
    {"subject": "OOP C++", "day": "Monday",  "time": "08-09"},
    {"subject": "Python",  "day": "Tuesday", "time": "10-11"}
  ]
}
```

Subjects must be written exactly as the app should name them (capital letters don't matter). If your subject is not in `data.js`, the app keeps whatever the OCR read, so write what is printed on the image.

## Truth file for a notice

`"mode": "notice"`. One entry per dated task. `subject` and `date` (`YYYY-MM-DD`) must match exactly. `topic` and `task` are optional and compared with fuzzy matching (default thresholds: topic 0.80, task 0.70; change with `--topic-min` / `--task-min`). A key-match with text that is too different is reported as **partial** and is *not* counted correct.

```json
{
  "mode": "notice",
  "entries": [
    {"subject": "DAA", "date": "2026-11-14", "topic": "Dynamic Programming", "task": "Submit assignment"},
    {"subject": "EVS", "date": "2026-11-25", "topic": "Water Pollution",     "task": "Exam / test"}
  ]
}
```

`task` uses the labels the app produces: `Submit assignment`, `Lab / viva`, `Exam / test`, `Project / demo`, `Deadline`, `Task`, `Revise notes`, `Attend lecture`. If you leave `task` or `topic` out, that field is simply not checked.

A notice with a date but no obvious subject gets the subject `General`.

## What the columns mean

| column | meaning |
|---|---|
| expected | entries in your truth file |
| extracted | entries the pipeline produced |
| correct | key matched and text checks passed |
| partial | key matched, but topic/task text too different (not counted correct) |
| missed | in truth, not extracted |
| extra | extracted, not in truth |

## Privacy

Real timetables and notices can contain names or other personal details. Before you `git add` anything here (and before publishing the repo for Devpost), blur or crop them, or keep them out of the repo.

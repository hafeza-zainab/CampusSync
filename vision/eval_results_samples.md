# Evaluation results (synthetic images)

Run: 2026-10-26 21:55 · folder: `samples/` · fuzzy thresholds: topic >= 0.8, task >= 0.7 (difflib ratio)

| image | type | cells | expected | extracted | correct | partial | missed | extra | seconds |
|---|---|---|---|---|---|---|---|---|---|
| notice.png | notice | 0 | 5 | 5 | 5 | 0 | 0 | 0 | 2.6 |
| notice_scanned.pdf | notice | 0 | 5 | 5 | 5 | 0 | 0 | 0 | 4.6 |
| notice_text.pdf | notice | 0 | 5 | 5 | 5 | 0 | 0 | 0 | 2.0 |
| timetable.png | timetable | 42 | 11 | 11 | 11 | 0 | 0 | 0 | 1.3 |
| timetable_skew.png | timetable | 42 | 11 | 11 | 11 | 0 | 0 | 0 | 1.1 |

**5 synthetic images: 37/37 entries correct**

Extra (unexpected) entries: 0 · partial (key right, text too different, not counted correct): 0 · mean time 2.3 s/image


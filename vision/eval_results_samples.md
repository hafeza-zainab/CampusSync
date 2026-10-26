# Evaluation results (synthetic images)

> **SYNTHETIC**: every image here was drawn by `make_sample.py`. These numbers test the code; they are not evidence of real-world accuracy.

Run: 2026-10-26 23:08 · folder: `samples/` · fuzzy thresholds: topic >= 0.8, task >= 0.7 (difflib ratio)

| image | type | scope (course/semester) | cells | expected | extracted | correct | partial | missed | extra | subject | day/time | teacher | room | seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| notice.png | notice | -/- | 0 | 5 | 5 | 5 | 0 | 0 | 0 | 5/5 | 5/5 | – | – | 1.9 |
| notice_scanned.pdf | notice | -/- | 0 | 5 | 5 | 5 | 0 | 0 | 0 | 5/5 | 5/5 | – | – | 4.2 |
| notice_teacher_room.png | notice | demo-a/sem1 | 0 | 2 | 2 | 2 | 0 | 0 | 0 | 2/2 | 2/2 | 2/2 | 2/2 | 1.6 |
| notice_text.pdf | notice | -/- | 0 | 5 | 5 | 5 | 0 | 0 | 0 | 5/5 | 5/5 | – | – | 1.9 |
| timetable.png | timetable | -/- | 42 | 11 | 11 | 11 | 0 | 0 | 0 | 11/11 | 11/11 | – | – | 1.2 |
| timetable_exif3.jpg | timetable | -/- | 42 | 11 | 11 | 11 | 0 | 0 | 0 | 11/11 | 11/11 | – | – | 1.0 |
| timetable_exif6.jpg | timetable | -/- | 42 | 11 | 11 | 11 | 0 | 0 | 0 | 11/11 | 11/11 | – | – | 0.8 |
| timetable_pdf.pdf | timetable | -/- | 42 | 11 | 11 | 11 | 0 | 0 | 0 | 11/11 | 11/11 | – | – | 1.7 |
| timetable_skew.png | timetable | -/- | 42 | 11 | 11 | 11 | 0 | 0 | 0 | 11/11 | 11/11 | – | – | 1.0 |
| timetable_teacher_room.png | timetable | demo-a/sem1 | 30 | 7 | 7 | 7 | 0 | 0 | 0 | 7/7 | 7/7 | 6/6 | 6/6 | 1.5 |
| timetable_transposed.png | timetable | main/sem4 | 42 | 11 | 11 | 11 | 0 | 0 | 0 | 11/11 | 11/11 | – | – | 1.3 |

**11 synthetic images: 90/90 entries correct**

| field | right | scored | accuracy |
|---|---|---|---|
| subject | 90 | 90 | 100% |
| day/time | 90 | 90 | 100% |
| teacher | 8 | 8 | 100% |
| room | 8 | 8 | 100% |

Correct teacher values: 6 read from the image, 2 filled from the catalog.
Correct room values: 5 read from the image, 3 filled from the catalog.

Extra (unexpected) entries: 0 · partial (paired, a field wrong, not counted correct): 0 · mean time 1.6 s/image


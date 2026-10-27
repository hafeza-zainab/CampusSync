"""Fast checks of the extraction rules (no browser, no server, no OCR model needed).

    py tests/unit.py            (from the vision folder)

Each check feeds a TEXT string to the same functions pipeline.py uses after OCR. They back the claims in
HOW_IT_WORKS.md about which patterns are recognised, what is NOT recognised, and what the fuzzy match accepts.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import eval as ev            # noqa: E402  (teacher_equal, norm_room)
import pipeline as p         # noqa: E402
from catalog import load_catalog, make_scope   # noqa: E402

results = []


def check(name, got, want):
    ok = got == want
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   [got {got!r}, wanted {want!r}]"))
    results.append(ok)


CODES = {"AP", "RP"}


def rooms(text):
    return p.extract_teacher_room(text, CODES)[1]["room"]


def teacher(text, trailing=False):
    f = p.extract_teacher_room(text, CODES, allow_trailing=trailing)[1]
    return f["teacher"] or f["initials"]


import cv2  # noqa: E402

print("== OpenCV version")
check("the code runs on OpenCV 5 (cv2 %s)" % cv2.__version__, cv2.__version__.split(".")[0], "5")

print("== rooms")
check("Room 301", rooms("Algebra Room 301"), "Room 301")
check("Rm. 12", rooms("Algebra Rm. 12"), "Room 12")
check("R-204", rooms("Algebra R-204"), "R-204")
check("LH-3", rooms("Algebra LH-3"), "LH-3")
check("LH 3 (space)", rooms("Algebra LH 3"), "LH-3")
check("no room -> empty", rooms("Algebra on Matrices"), "")
check("'Lab viva' is not a room", rooms("Python Lab viva on files"), "")

print("== teachers")
check("Prof. Sharma", teacher("Submit by Prof. Sharma"), "Prof. Sharma")
check("Dr. P. K. Rao", teacher("DAA Dr. P. K. Rao"), "Dr. P. K. Rao")
check("Ms Anita Singh (no dot)", teacher("Ms Anita Singh"), "Ms. Anita Singh")
check("name stops before 'Submit'", teacher("Prof. Sharma Submit Assignment 2"), "Prof. Sharma")
check("catalog code in brackets (RP)", teacher("Physics (RP)"), "RP")
check("catalog code at end of a cell needs allow_trailing", teacher("Physics RP"), "")
check("catalog code at end of a cell (timetable)", teacher("Physics RP", trailing=True), "RP")
check("code NOT in the catalog is not read as a teacher", teacher("Physics (XY)"), "")
check("a bare all-caps word (CSE) is not a teacher", teacher("Python CSE", trailing=True), "")
check("but 'Dr. CSE' with a title IS read as written", teacher("Python Dr. CSE"), "Dr. CSE")
check("no teacher -> empty", teacher("Python Lab"), "")

print("== room + teacher are cut out of the text")
left, f = p.extract_teacher_room("Prof. Sharma Submit Assignment 2 in Room 12", CODES)
check("leftover text keeps the task words", left, "Submit Assignment 2")

print("== dates (day first)")
today = date(2026, 10, 26)
for text, want in [("by 14 Nov 2026", date(2026, 11, 14)), ("on 18/11/2026", date(2026, 11, 18)), ("21 November 2026", date(2026, 11, 21)),
                   ("due 02-12-2026", date(2026, 12, 2)), ("on Nov 25, 2026", date(2026, 11, 25)), ("on 3/4/26", date(2026, 4, 3))]:
    check(f"date '{text}'", p.find_date(text, today)[0], want)
check("no date -> None", p.find_date("Submit the assignment soon", today)[0], None)
check("no year: next occurrence (Jan 5 after Oct 26 -> 2027)", p.find_date("on 5 Jan", today)[0], date(2027, 1, 5))

print("== fuzzy subject match (scope main/sem4)")
scope = make_scope(load_catalog(), "main", "sem4")
for typed, want in [("OOP C+", "OOP C++"), ("Pythn", "Python"), ("Web Tec", "Web Tech"), ("0OP C++", "OOP C++")]:
    check(f"'{typed}' -> {want}", p.match_subject(typed, scope)[0], want)
check("'Kitchen' stays unknown", p.match_subject("Kitchen", scope)[1], None)
demo = make_scope(load_catalog(), "demo-a", "sem2")
check("'Placeholder Seminar' is NOT matched to 'Placeholder Chemistry'", p.match_subject("Placeholder Seminar", demo)[1], None)

print("== catalog scope")
check("course+semester is scoped", make_scope(load_catalog(), "demo-a", "sem1").scoped, True)
check("course only is not scoped", make_scope(load_catalog(), "demo-a").scoped, False)
check("nothing selected skips placeholder courses",
      any("Placeholder" in s["name"] for s in make_scope(load_catalog()).subjects), False)

print("== confidence formula")
check("scoped, exact match, OCR 0.95 -> 0.95", p.entry_confidence(0.95, 1.0, scope), 0.95)
check("unscoped lowers it x0.9", p.entry_confidence(0.90, 1.0, make_scope(load_catalog())), 0.81)
check("unknown subject x0.85", p.entry_confidence(0.95, 0.0, scope), 0.81)
check("capped at 0.99", p.entry_confidence(1.0, 1.0, scope), 0.99)

print("== eval helpers")
check("initials count as the full name", ev.teacher_equal("AP", "Dr. Asha Placeholder"), True)
check("different people are not equal", ev.teacher_equal("AP", "Prof. Rahul Placeholder"), False)
check("titles ignored", ev.teacher_equal("Prof. Rahul Placeholder", "Rahul Placeholder"), True)
check("room spelling ignored", ev.norm_room("Room 301") == ev.norm_room("301"), True)

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)

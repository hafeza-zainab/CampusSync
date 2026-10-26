"""The course catalog: courses -> semesters -> subjects (with optional teacher and room).

The data lives in data/catalog.json, so nothing about any particular college is written in code.
pipeline.py asks this file one question: "which subjects should I look for?" - the answer is a Scope.

  course AND semester chosen -> scope = just that semester's subjects          (scoped = True)
  only a course chosen       -> scope = every subject of that course            (scoped = False)
  nothing chosen             -> scope = every subject of every REAL course      (scoped = False)
                                (courses marked "placeholder": true are skipped)

Only a fully scoped search may fill in a missing teacher/room from the catalog, because only then
do we know which subject entry we are talking about.
"""
import json
import os

CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "catalog.json")


def load_catalog(path=CATALOG_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Scope:
    """What the pipeline is allowed to match against."""

    def __init__(self, subjects, scoped, course=None, semester=None):
        self.subjects = subjects        # list of subject dicts: {name, color, teacher, room}
        self.scoped = scoped            # True only when both course and semester were chosen
        self.course = course            # course dict or None
        self.semester = semester        # semester dict or None
        # teacher short codes ("AP") -> full name; only used when scoped
        self.teacher_codes = {}
        if scoped:
            for s in subjects:
                if s.get("teacher") and s["teacher"].get("code"):
                    self.teacher_codes[s["teacher"]["code"].upper()] = s["teacher"]["name"]

    @property
    def course_id(self):
        return self.course["id"] if self.course else ""

    @property
    def course_name(self):
        return self.course["name"] if self.course else ""

    @property
    def semester_id(self):
        return self.semester["id"] if self.semester else ""

    @property
    def semester_name(self):
        return self.semester["name"] if self.semester else ""

    def describe(self):
        """One short line for the UI / logs."""
        if self.scoped:
            return f"searched {len(self.subjects)} subjects in {self.course_name} / {self.semester_name}"
        where = self.course_name if self.course else "all courses"
        return f"no semester chosen: searched {len(self.subjects)} subjects ({where}), confidence lowered"


def _dedupe(subjects):
    seen, out = set(), []
    for s in subjects:
        if s["name"].lower() not in seen:
            seen.add(s["name"].lower())
            out.append(s)
    return out


def make_scope(catalog, course_id="", semester_id=""):
    """Build a Scope from the ids the user picked (empty string = not picked)."""
    course = semester = None
    if course_id:
        course = next((c for c in catalog["courses"] if c["id"] == course_id), None)
        if course is None:
            raise ValueError(f"Unknown course: {course_id}")
    if semester_id:
        if course is None:
            raise ValueError("Pick a course before a semester")
        semester = next((s for s in course["semesters"] if s["id"] == semester_id), None)
        if semester is None:
            raise ValueError(f"Unknown semester '{semester_id}' for course {course_id}")

    if course and semester:
        return Scope(semester["subjects"], True, course, semester)
    if course:
        return Scope(_dedupe([s for sem in course["semesters"] for s in sem["subjects"]]), False, course)
    real = [c for c in catalog["courses"] if not c.get("placeholder")]
    return Scope(_dedupe([s for c in real for sem in c["semesters"] for s in sem["subjects"]]), False)

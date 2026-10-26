"""Measure how accurate the pipeline is on images that have a "truth" file.

  py eval.py                    # runs on real_samples/  -> writes eval_results.md
  py eval.py --dir samples      # runs on the synthetic samples -> eval_results_samples.md

For every image (or PDF) NAME.ext that has a NAME.truth.json next to it:
  1. run pipeline.analyze() on it (timed), using the course/semester named in the truth file
  2. pair every truth entry with an extracted entry
  3. score each field separately and count correct / partial / missed / extra
Images with no truth file are listed as "unlabelled" and skipped.
See real_samples/README.md for how to write a truth file.

PAIRING (nothing is counted correct silently)
  A truth entry and an extracted entry are paired by their SLOT:
     timetable: the day (+ the time, only if the truth entry has a "time")
     notice:    the date
  First we look for a pair with the same slot AND the same subject.
  If none, a pair with the same slot but a different subject is still made, so a wrong subject
  shows up as "subject wrong" instead of looking like one missed + one extra entry.

FIELDS SCORED (accuracy is reported separately for each)
  subject    must equal the truth subject (ignoring upper/lower case)
  day/time   the slot above was found (a missed entry counts as wrong)
  teacher    only scored when the truth entry has "teacher". Equal after dropping titles (Dr./Prof.)
             and punctuation; initials ("AP") also count as equal to the full name they abbreviate.
  room       only scored when the truth entry has "room". "Room 301" == "301" == "R301"-style spelling
             differences are ignored (case, spaces, hyphens, a leading "Room").
  topic/task notices only, optional: fuzzy match with difflib, thresholds --topic-min / --task-min

An entry is CORRECT when every field that is scored for it is right.
  partial = paired, but at least one scored field is wrong (not counted correct)
  missed  = truth entry with no extracted entry in its slot
  extra   = extracted entry that is paired with nothing
"""
import argparse
import difflib
import json
import os
import re
import sys
import time
from datetime import datetime

import pipeline

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".pdf")
FIELDS = ["subject", "slot", "teacher", "room"]
FIELD_LABEL = {"subject": "subject", "slot": "day/time", "teacher": "teacher", "room": "room"}
TITLE_WORDS = {"prof", "dr", "mr", "mrs", "ms", "miss", "sir", "madam"}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def norm(text):
    """lower-case, single spaces: 'OOP  C++ ' -> 'oop c++'"""
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def norm_time(text):
    """'07 - 08' / '07–08' -> '07-08' so dash style does not matter"""
    return re.sub(r"\s*[:.\-–—]\s*", "-", norm(text))


def norm_room(text):
    """'Room 301' / 'room-301' / '301' -> '301';  'R-204' -> 'r204'"""
    t = re.sub(r"^(room|rm)\.?\s*", "", norm(text))
    return re.sub(r"[^a-z0-9]", "", t)


def norm_person(text):
    """'Dr. Anita  Rao' -> 'anita rao'"""
    return " ".join(w for w in re.findall(r"[a-z]+", norm(text)) if w not in TITLE_WORDS)


def teacher_equal(a, b):
    na, nb = norm_person(a), norm_person(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    initials = lambda n: "".join(w[0] for w in n.split())           # 'anita rao' -> 'ar'
    return initials(na) == nb.replace(" ", "") or initials(nb) == na.replace(" ", "")


def similarity(a, b):
    """0.0 (nothing alike) .. 1.0 (identical) using difflib"""
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def slot_matches(t, g, mode):
    """Is extracted entry g in the same slot as truth entry t?"""
    if mode == "timetable":
        if norm(t.get("day")) != norm(g.get("day")):
            return False
        return not t.get("time") or norm_time(t["time"]) == norm_time(g.get("time"))
    return str(t.get("date")) == str(g.get("date"))


def slot_label(t):
    return f"{t.get('day') or t.get('date')}" + (f" {t['time']}" if t.get("time") else "")


# --------------------------------------------------------------------------
# compare extracted entries against truth
# --------------------------------------------------------------------------
def pair_entries(truth_entries, got_entries, mode):
    """Returns pairs[i] = index of the extracted entry paired with truth entry i (or None)."""
    pairs = [None] * len(truth_entries)
    used = set()

    def closest(t, cands):
        if mode == "notice":   # several entries may share a date: take the most similar topic
            return max(cands, key=lambda i: similarity(t.get("topic", ""), got_entries[i].get("topic", "")))
        return max(cands, key=lambda i: similarity(t.get("subject", ""), got_entries[i].get("subject", "")))

    for exact in (True, False):          # pass 1: same slot + same subject. pass 2: same slot only
        for ti, t in enumerate(truth_entries):
            if pairs[ti] is not None:
                continue
            cands = [gi for gi, g in enumerate(got_entries)
                     if gi not in used and slot_matches(t, g, mode)
                     and (not exact or norm(g.get("subject")) == norm(t.get("subject")))]
            if cands:
                pairs[ti] = closest(t, cands)
                used.add(pairs[ti])
    return pairs


def compare(truth_entries, got_entries, mode, topic_min, task_min):
    """Score every truth entry. Returns counts, per-field [right, scored], and problem lines."""
    pairs = pair_entries(truth_entries, got_entries, mode)
    fields = {f: [0, 0] for f in FIELDS}          # field -> [right, scored]
    sources = {"teacher": {"image": 0, "catalog": 0}, "room": {"image": 0, "catalog": 0}}
    correct = partial = missed = 0
    problems = []

    for t, gi in zip(truth_entries, pairs):
        label = f"{t.get('subject')} / {slot_label(t)}"
        scored = ["subject", "slot"] + [f for f in ("teacher", "room") if t.get(f)]
        for f in scored:
            fields[f][1] += 1
        if gi is None:
            missed += 1
            problems.append(f"MISSED   {label}")
            continue

        g = got_entries[gi]
        bad = []
        fields["slot"][0] += 1
        if norm(g.get("subject")) == norm(t.get("subject")):
            fields["subject"][0] += 1
        else:
            bad.append(f"subject expected '{t.get('subject')}' got '{g.get('subject')}'")
        if t.get("teacher"):
            if teacher_equal(t["teacher"], g.get("teacher")):
                fields["teacher"][0] += 1
                sources["teacher"][g.get("teacher_source") or "image"] += 1
            else:
                bad.append(f"teacher expected '{t['teacher']}' got '{g.get('teacher') or '-'}'")
        if t.get("room"):
            if norm_room(t["room"]) == norm_room(g.get("room")):
                fields["room"][0] += 1
                sources["room"][g.get("room_source") or "image"] += 1
            else:
                bad.append(f"room expected '{t['room']}' got '{g.get('room') or '-'}'")
        if mode == "notice":
            for name, minimum in (("topic", topic_min), ("task", task_min)):
                if t.get(name) is not None:
                    s = similarity(t[name], g.get(name))
                    if s < minimum:
                        bad.append(f"{name} expected '{t[name]}' got '{g.get(name)}' (similarity {s:.2f} < {minimum})")
        if bad:
            partial += 1
            problems.append(f"PARTIAL  {label}: " + "; ".join(bad))
        else:
            correct += 1

    paired = {gi for gi in pairs if gi is not None}
    extra_idx = [i for i in range(len(got_entries)) if i not in paired]
    for i in extra_idx:
        g = got_entries[i]
        problems.append(f"EXTRA    {g.get('subject')} / {g.get('day') or g.get('date')} ('{g.get('topic')}')")
    return {"correct": correct, "partial": partial, "missed": missed, "extra": len(extra_idx),
            "fields": fields, "sources": sources, "problems": problems}


# --------------------------------------------------------------------------
# run everything
# --------------------------------------------------------------------------
def find_inputs(folder):
    """Split files into (labelled, unlabelled). Labelled = has NAME.truth.json next to it."""
    labelled, unlabelled = [], []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(IMAGE_EXT):
            continue
        truth = os.path.join(folder, os.path.splitext(name)[0] + ".truth.json")
        (labelled if os.path.exists(truth) else unlabelled).append((name, truth))
    return labelled, [n for n, _ in unlabelled]


def evaluate(folder, topic_min, task_min):
    labelled, unlabelled = find_inputs(folder)
    rows = []
    if labelled:  # load the OCR model once, so model-loading time is not blamed on the first image
        pipeline.run_ocr(__import__("numpy").full((64, 256, 3), 255, "uint8"))
    for name, truth_path in labelled:
        with open(truth_path, encoding="utf-8") as f:
            truth = json.load(f)
        mode = truth.get("mode", "notice")
        course, semester = truth.get("course", ""), truth.get("semester", "")
        with open(os.path.join(folder, name), "rb") as f:
            data = f.read()

        t0 = time.perf_counter()
        try:
            result = pipeline.analyze(data, name, semester=semester, course=course)
            error = None
        except Exception as e:  # keep going: one bad image must not stop the whole evaluation
            result, error = {"cells": [], "entries": [], "mode": "error"}, str(e)
        seconds = time.perf_counter() - t0

        res = compare(truth["entries"], result["entries"], mode, topic_min, task_min)
        res.update(name=name, expected=len(truth["entries"]), extracted=len(result["entries"]),
                   cells=len(result["cells"]), seconds=seconds, mode=mode, detected_mode=result["mode"],
                   scope=(f"{course or '-'}/{semester or '-'}"), error=error)
        if mode != result["mode"] and not error:
            res["problems"].insert(0, f"NOTE     truth says '{mode}' but the pipeline treated it as '{result['mode']}'")
        rows.append(res)
    return rows, unlabelled


def fmt_field(counts):
    right, scored = counts
    return f"{right}/{scored}" if scored else "–"


def format_report(rows, unlabelled, folder_name, label, topic_min, task_min):
    lines = [f"# Evaluation results ({label} images)", ""]
    if label == "synthetic":
        lines += ["> **SYNTHETIC**: every image here was drawn by `make_sample.py`. These numbers test the code; "
                  "they are not evidence of real-world accuracy.", ""]
    lines.append(f"Run: {datetime.now():%Y-%m-%d %H:%M} · folder: `{folder_name}/` · "
                 f"fuzzy thresholds: topic >= {topic_min}, task >= {task_min} (difflib ratio)")
    lines += ["", "| image | type | scope (course/semester) | cells | expected | extracted | correct | partial | missed | extra "
              "| subject | day/time | teacher | room | seconds |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        f = r["fields"]
        lines.append(f"| {r['name']} | {r['detected_mode']} | {r['scope']} | {r['cells']} | {r['expected']} | {r['extracted']} | "
                     f"{r['correct']} | {r['partial']} | {r['missed']} | {r['extra']} | "
                     f"{fmt_field(f['subject'])} | {fmt_field(f['slot'])} | {fmt_field(f['teacher'])} | {fmt_field(f['room'])} | "
                     f"{r['seconds']:.1f} |")

    total_expected = sum(r["expected"] for r in rows)
    total_correct = sum(r["correct"] for r in rows)
    overall = f"{len(rows)} {label} images: {total_correct}/{total_expected} entries correct"
    lines += ["", f"**{overall}**" if rows else "**No labelled images found.**", ""]

    if rows:
        lines += ["| field | right | scored | accuracy |", "|---|---|---|---|"]
        for fld in FIELDS:
            right = sum(r["fields"][fld][0] for r in rows)
            scored = sum(r["fields"][fld][1] for r in rows)
            acc = f"{100 * right / scored:.0f}%" if scored else "not scored (no truth entry has it)"
            lines.append(f"| {FIELD_LABEL[fld]} | {right} | {scored} | {acc} |")
        lines.append("")
        for fld in ("teacher", "room"):
            img = sum(r["sources"][fld]["image"] for r in rows)
            cat = sum(r["sources"][fld]["catalog"] for r in rows)
            if img + cat:
                lines.append(f"Correct {fld} values: {img} read from the image, {cat} filled from the catalog.")
        lines += ["", f"Extra (unexpected) entries: {sum(r['extra'] for r in rows)} · "
                  f"partial (paired, a field wrong, not counted correct): {sum(r['partial'] for r in rows)} · "
                  f"mean time {sum(r['seconds'] for r in rows) / len(rows):.1f} s/image", ""]

    problems = [r for r in rows if r["problems"] or r["error"]]
    if problems:
        lines.append("## Details")
        for r in problems:
            lines.append(f"\n**{r['name']}**" + (f" - ERROR: {r['error']}" if r["error"] else ""))
            lines += [f"- {p}" for p in r["problems"]]
        lines.append("")
    if unlabelled:
        lines.append("## Unlabelled (skipped - add a .truth.json to include them)")
        lines += [f"- {n}" for n in unlabelled]
        lines.append("")
    return "\n".join(lines), overall


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles can choke on '·'
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="real_samples", help="folder with images + .truth.json files")
    ap.add_argument("--topic-min", type=float, default=0.80, help="min topic similarity to count as correct")
    ap.add_argument("--task-min", type=float, default=0.70, help="min task similarity to count as correct")
    args = ap.parse_args()

    folder = args.dir if os.path.isabs(args.dir) else os.path.join(HERE, args.dir)
    if not os.path.isdir(folder):
        raise SystemExit(f"Folder not found: {folder}")
    name = os.path.basename(os.path.normpath(folder))
    label = "real" if name == "real_samples" else "synthetic"
    out_name = "eval_results.md" if name == "real_samples" else f"eval_results_{name}.md"

    rows, unlabelled = evaluate(folder, args.topic_min, args.task_min)
    report, overall = format_report(rows, unlabelled, name, label, args.topic_min, args.task_min)
    print(report)
    with open(os.path.join(HERE, out_name), "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\n(written to {out_name})")
    if not rows:
        print("Nothing to evaluate. Put an image plus NAME.truth.json in", folder)


if __name__ == "__main__":
    main()

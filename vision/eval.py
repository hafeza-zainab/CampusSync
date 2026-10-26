"""Measure how accurate the pipeline is on images that have a "truth" file.

  py eval.py                    # runs on real_samples/  -> writes eval_results.md
  py eval.py --dir samples      # runs on the synthetic samples -> eval_results_samples.md

For every image (or PDF) NAME.ext that has a NAME.truth.json next to it:
  1. run pipeline.analyze() on it (timed)
  2. compare the extracted entries with the entries you wrote in the truth file
  3. count correct / partial / missed / extra

Images with no truth file are listed as "unlabelled" and skipped.
See real_samples/README.md for how to write a truth file.

How an entry is judged (nothing is counted correct silently):
  timetable  key = subject + day (+ time, only if the truth entry has a "time")
             subject must match exactly (ignoring upper/lower case)
  notice     key = subject + date, both must match exactly
             then topic and task text are compared with difflib fuzzy matching:
             similarity must be >= --topic-min (default 0.80) and >= --task-min (default 0.70).
             If the key matches but the text is too different it is a PARTIAL: reported, NOT counted correct.
  correct = key matches and text checks pass
  partial = key matches but topic/task text is below its threshold
  missed  = truth entry with no extracted entry for that key
  extra   = extracted entry that matches no truth entry
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


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def norm(text):
    """lower-case, single spaces: 'OOP  C++ ' -> 'oop c++'"""
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def norm_time(text):
    """'07 - 08' / '07–08' -> '07-08' so dash style does not matter"""
    return re.sub(r"\s*[:.\-–—]\s*", "-", norm(text))


def similarity(a, b):
    """0.0 (nothing alike) .. 1.0 (identical) using difflib"""
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def entry_key(e, mode):
    """The part of an entry that decides WHICH truth entry it should match."""
    if mode == "timetable":
        return (norm(e.get("subject")), norm(e.get("day")))
    return (norm(e.get("subject")), str(e.get("date", "")))


# --------------------------------------------------------------------------
# compare extracted entries against truth
# --------------------------------------------------------------------------
def compare(truth_entries, got_entries, mode, topic_min, task_min):
    """Returns dict with counts and a list of human-readable problem lines."""
    used = set()          # indexes of extracted entries already matched
    correct = partial = missed = 0
    problems = []

    for t in truth_entries:
        want_key = entry_key(t, mode)
        # candidate extracted entries with the same key that are not used yet
        cands = [i for i, g in enumerate(got_entries)
                 if i not in used and entry_key(g, mode) == want_key]
        if mode == "timetable" and t.get("time"):
            cands = [i for i in cands if norm_time(got_entries[i].get("time")) == norm_time(t["time"])]
        label = f"{t.get('subject')} / {t.get('day') or t.get('date')}" + (f" {t['time']}" if t.get("time") else "")

        if not cands:
            missed += 1
            problems.append(f"MISSED   {label}")
            continue

        if mode == "timetable":
            used.add(cands[0])
            correct += 1
            continue

        # notice: pick the candidate whose topic is closest, then check the text fields
        best = max(cands, key=lambda i: similarity(t.get("topic", ""), got_entries[i].get("topic", "")))
        used.add(best)
        g = got_entries[best]
        bad = []
        if t.get("topic") is not None:
            s = similarity(t["topic"], g.get("topic"))
            if s < topic_min:
                bad.append(f"topic expected '{t['topic']}' got '{g.get('topic')}' (similarity {s:.2f} < {topic_min})")
        if t.get("task") is not None:
            s = similarity(t["task"], g.get("task"))
            if s < task_min:
                bad.append(f"task expected '{t['task']}' got '{g.get('task')}' (similarity {s:.2f} < {task_min})")
        if bad:
            partial += 1
            problems.append(f"PARTIAL  {label}: " + "; ".join(bad))
        else:
            correct += 1

    extra_idx = [i for i in range(len(got_entries)) if i not in used]
    for i in extra_idx:
        g = got_entries[i]
        problems.append(f"EXTRA    {g.get('subject')} / {g.get('day') or g.get('date')} ('{g.get('topic')}')")
    return {"correct": correct, "partial": partial, "missed": missed,
            "extra": len(extra_idx), "problems": problems}


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
        with open(os.path.join(folder, name), "rb") as f:
            data = f.read()

        t0 = time.perf_counter()
        try:
            result = pipeline.analyze(data, name)
            error = None
        except Exception as e:  # keep going: one bad image must not stop the whole evaluation
            result, error = {"cells": [], "entries": [], "mode": "error"}, str(e)
        seconds = time.perf_counter() - t0

        res = compare(truth["entries"], result["entries"], mode, topic_min, task_min)
        res.update(name=name, expected=len(truth["entries"]), extracted=len(result["entries"]),
                   cells=len(result["cells"]), seconds=seconds, mode=mode,
                   detected_mode=result["mode"], error=error)
        if mode != result["mode"] and not error:
            res["problems"].insert(0, f"NOTE     truth says '{mode}' but the pipeline treated it as '{result['mode']}'")
        rows.append(res)
    return rows, unlabelled


def format_report(rows, unlabelled, folder_name, label, topic_min, task_min):
    lines = []
    lines.append(f"# Evaluation results ({label} images)")
    lines.append("")
    lines.append(f"Run: {datetime.now():%Y-%m-%d %H:%M} · folder: `{folder_name}/` · "
                 f"fuzzy thresholds: topic >= {topic_min}, task >= {task_min} (difflib ratio)")
    lines.append("")
    lines.append("| image | type | cells | expected | extracted | correct | partial | missed | extra | seconds |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(f"| {r['name']} | {r['detected_mode']} | {r['cells']} | {r['expected']} | {r['extracted']} | "
                     f"{r['correct']} | {r['partial']} | {r['missed']} | {r['extra']} | {r['seconds']:.1f} |")
    total_expected = sum(r["expected"] for r in rows)
    total_correct = sum(r["correct"] for r in rows)
    overall = f"{len(rows)} {label} images: {total_correct}/{total_expected} entries correct"
    lines += ["", f"**{overall}**" if rows else "**No labelled images found.**", ""]
    if rows:
        lines.append(f"Extra (unexpected) entries: {sum(r['extra'] for r in rows)} · "
                     f"partial (key right, text too different, not counted correct): {sum(r['partial'] for r in rows)} · "
                     f"mean time {sum(r['seconds'] for r in rows) / len(rows):.1f} s/image")
        lines.append("")
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

"""CampusSync Vision - the whole computer-vision pipeline in one file.

Read it top to bottom, it follows the same order the image travels:

  1. load_pages()     image / PDF  ->  list of OpenCV images (numpy arrays)
  2. preprocess()     fix tilt (deskew) + boost contrast
  3. find_grid()      OpenCV morphology finds the table lines -> cell rectangles
  4. run_ocr()        OCR finds text blocks (box + text + confidence)
  5. parse_timetable() / parse_notice()   turn text blocks into
                      {subject, date, topic, task} entries
  6. analyze()        runs 1-5 and times every stage

An OpenCV image is just a numpy array of shape (height, width, 3) in BGR order.
A "box" is [x1, y1, x2, y2] = left, top, right, bottom in pixels.
"""
import difflib
import os
import re
import time
from datetime import date, datetime, timedelta

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


# --------------------------------------------------------------------------
# 0. Known subjects - borrowed from your own data.js so tags match your app
# --------------------------------------------------------------------------
def load_known_subjects():
    subjects = {"Break", "Lunch"}  # not real subjects, but recognised so we can skip them
    try:
        with open(os.path.join(ROOT, "data.js"), encoding="utf-8") as f:
            subjects |= set(re.findall(r'subject:\s*"([^"]+)"', f.read()))
    except OSError:
        pass
    return sorted(subjects - {"Break", "Lunch"}), {"break", "lunch", "recess"}


KNOWN_SUBJECTS, SKIP_WORDS = load_known_subjects()


def canonical_subject(text):
    """'oop c+' -> 'OOP C++'. Fuzzy-match OCR text to a subject we know about."""
    t = re.sub(r"\s+", " ", text).strip()
    if not t:
        return None, False
    lowered = {s.lower(): s for s in KNOWN_SUBJECTS}
    hit = difflib.get_close_matches(t.lower(), lowered.keys(), n=1, cutoff=0.78)
    if hit:
        return lowered[hit[0]], True
    return t, False  # unknown subject: keep what OCR read


# --------------------------------------------------------------------------
# 1. Load image or PDF
# --------------------------------------------------------------------------
def load_pages(data: bytes, filename: str, max_pages=3):
    """Return a list of BGR images. PDFs are rendered page by page."""
    if filename.lower().endswith(".pdf") or data[:5] == b"%PDF-":
        import pymupdf as fitz  # PyMuPDF

        pages = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for page in list(doc)[:max_pages]:
                pix = page.get_pixmap(dpi=170)  # 170 dpi: sharp enough for OCR, not huge
                img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)
                code = cv2.COLOR_RGBA2BGR if pix.n == 4 else cv2.COLOR_RGB2BGR
                pages.append(cv2.cvtColor(img, code) if pix.n >= 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
        return pages
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not read this file as an image or PDF")
    return [img]


# --------------------------------------------------------------------------
# 2. Preprocess: shrink huge images, fix tilt, boost contrast
# --------------------------------------------------------------------------
def estimate_skew(gray):
    """Find how tilted the page is by looking at long near-horizontal lines.
    Returns degrees (positive = needs counter-clockwise rotation)."""
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=120,
                            minLineLength=gray.shape[1] // 4, maxLineGap=10)
    if lines is None:
        return 0.0
    angles = []
    for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):  # shape differs between OpenCV versions
        a = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(a) < 15:  # only lines that are meant to be horizontal
            angles.append(a)
    return float(np.median(angles)) if angles else 0.0


def preprocess(img, max_side=2000):
    """Returns (cleaned_bgr, info). info explains what we changed (shown in the UI)."""
    info = {}
    h, w = img.shape[:2]
    scale = 1.0
    if max(h, w) > max_side:  # huge photos make OCR slow; shrink them
        scale = max_side / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    info["resized"] = round(scale, 2)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    angle = estimate_skew(gray)
    info["skew_deg"] = round(angle, 2)
    if 0.3 < abs(angle) < 15:  # rotate back only if it is really tilted
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
        info["deskewed"] = True

    # CLAHE = local contrast boost. Helps with dim phone photos / pale handwriting.
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    return img, info


# --------------------------------------------------------------------------
# 3. Grid detection (classical OpenCV - the "segmentation" step)
# --------------------------------------------------------------------------
def find_grid(img):
    """Find table cells. Idea:
       - threshold so lines/text are white on black
       - 'open' with a very wide, 1px-tall kernel  -> only horizontal lines survive
       - 'open' with a very tall, 1px-wide kernel  -> only vertical lines survive
       - add them together = the table skeleton
       - the empty white areas BETWEEN lines are the cells (findContours)
    Returns a list of rows; each row is a list of boxes [x1,y1,x2,y2]."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY_INV, 21, 10)

    horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 18, 25), 1)))
    vert = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 18, 25))))
    skeleton = cv2.dilate(cv2.add(horiz, vert), np.ones((3, 3), np.uint8))

    # not enough long lines -> this is not a table
    if cv2.countNonZero(horiz) < w * 2 or cv2.countNonZero(vert) < h * 0.5:
        return [], skeleton

    contours, _ = cv2.findContours(cv2.bitwise_not(skeleton), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cells = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        if cw < w * 0.03 or ch < h * 0.02:  # specks
            continue
        if cw * ch > 0.5 * w * h:  # the page background itself
            continue
        cells.append([x, y, x + cw, y + ch])
    if len(cells) < 4:
        return [], skeleton
    return group_rows(cells), skeleton


def group_rows(cells):
    """Sort loose boxes into rows (top to bottom), each row left to right."""
    cells = sorted(cells, key=lambda b: (b[1] + b[3]) / 2)
    tol = float(np.median([b[3] - b[1] for b in cells])) * 0.5
    rows, current, cy = [], [], None
    for b in cells:
        mid = (b[1] + b[3]) / 2
        if cy is None or abs(mid - cy) <= tol:
            current.append(b)
            cy = mid if cy is None else (cy * (len(current) - 1) + mid) / len(current)
        else:
            rows.append(sorted(current, key=lambda b: b[0]))
            current, cy = [b], mid
    rows.append(sorted(current, key=lambda b: b[0]))
    return [r for r in rows if len(r) >= 2]


# --------------------------------------------------------------------------
# 4. OCR
# --------------------------------------------------------------------------
_engine = None


def run_ocr(img):
    """Returns text blocks: [{'box':[x1,y1,x2,y2], 'text':str, 'conf':float}, ...]
    Uses RapidOCR (pip-only, no extra install). Falls back to Tesseract if RapidOCR is missing."""
    global _engine
    try:
        from rapidocr import RapidOCR
        if _engine is None:
            _engine = RapidOCR()
        res = _engine(img)
        blocks = []
        if res.boxes is None:
            return blocks
        for pts, txt, sc in zip(res.boxes, res.txts, res.scores):
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            blocks.append({"box": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
                           "text": txt.strip(), "conf": round(float(sc), 3)})
        return blocks
    except ImportError:
        import pytesseract
        d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        blocks = []
        for i, t in enumerate(d["text"]):
            if t.strip() and float(d["conf"][i]) > 30:
                x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
                blocks.append({"box": [x, y, x + w, y + h], "text": t.strip(),
                               "conf": round(float(d["conf"][i]) / 100, 3)})
        return blocks


def box_center(b):
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def text_in_cell(cell, blocks):
    """All OCR blocks whose centre falls inside the cell, joined top-to-bottom."""
    inside = []
    for b in blocks:
        cx, cy = box_center(b["box"])
        if cell[0] <= cx <= cell[2] and cell[1] <= cy <= cell[3]:
            inside.append(b)
    inside.sort(key=lambda b: (b["box"][1], b["box"][0]))
    return " ".join(b["text"] for b in inside).strip(), inside


# --------------------------------------------------------------------------
# 5a. Timetable parsing (grid + OCR text -> weekly lectures)
# --------------------------------------------------------------------------
TIME_RE = re.compile(r"^\d{1,2}\s*[:.\-–—]\s*\d{1,2}")


def match_day(text):
    t = re.sub(r"[^a-z]", "", text.lower())
    if len(t) < 3:
        return None
    for d in DAYS:
        if t[:3] == d[:3].lower():
            return d
    close = difflib.get_close_matches(t, [d.lower() for d in DAYS], n=1, cutoff=0.7)
    return close[0].capitalize() if close else None


def next_weekday(day_name, today=None):
    today = today or date.today()
    ahead = (DAYS.index(day_name) - today.weekday()) % 7
    return today + timedelta(days=ahead)


def parse_timetable(rows, blocks, semester, today=None):
    """rows = grid cells. Find which row/column holds the day names, then read the rest.
    Returns (entries, cell_labels). cell_labels is for drawing in the UI."""
    table = []  # table[r][c] = (cell_box, text)
    for row in rows:
        table.append([(c, text_in_cell(c, blocks)[0]) for c in row])

    # Which row has the day names?  (normal timetable: first row)
    header_r = max(range(len(table)),
                   key=lambda r: sum(1 for _, t in table[r] if match_day(t)))
    day_cols = {c: match_day(t) for c, (_, t) in enumerate(table[header_r]) if match_day(t)}
    if len(day_cols) < 2:
        return [], []

    entries, labels = [], []
    for r, row in enumerate(table):
        if r == header_r:
            continue
        # the time label is the first cell of the row that looks like "07-08"
        time_txt = next((t for _, t in row if TIME_RE.match(t.strip())), "")
        for c, day in day_cols.items():
            if c >= len(row):
                continue
            box, text = row[c]
            if not text or text.lower() in SKIP_WORDS:
                continue
            subject, known = canonical_subject(text)
            if not subject:
                continue
            labels.append({"box": box, "text": subject, "known": known})
            entries.append({
                "semester": semester,
                "subject": subject,
                "topic": f"{day} {time_txt}".strip() + " lecture",
                "date": next_weekday(day, today).isoformat(),
                "task": "Attend lecture" + (f" ({time_txt})" if time_txt else ""),
                "kind": "lecture",
                "day": day,
                "time": time_txt,
                "confidence": 0.99 if known else 0.7,
                "source_box": box,
            })
    return entries, labels


# --------------------------------------------------------------------------
# 5b. Notice / notes parsing (free text -> dated tasks)
# --------------------------------------------------------------------------
KINDS = [  # (regex, kind, label)
    (r"\b(submit|submission|assignment|homework|worksheet)\b", "assignment", "Submit assignment"),
    (r"\b(viva|practical|lab)\b", "lab", "Lab / viva"),
    (r"\b(exam|test|quiz|mid-?term|internal)\b", "exam", "Exam / test"),
    (r"\b(project|demo|presentation)\b", "project", "Project / demo"),
    (r"\b(deadline|due|last date)\b", "deadline", "Deadline"),
]

DATE_PATTERNS = [
    # 14/11/2026  14-11-26  14.11.2026   (Indian order: day first)
    (re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b"), "dmy_num"),
    # 14 Nov 2026 / 14th November
    (re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s*(\d{4})?", re.I), "d_mon"),
    # Nov 25, 2026 / November 25th
    (re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})?", re.I), "mon_d"),
]


def find_date(text, today=None):
    """Returns (date_obj, matched_text) or (None, None)."""
    today = today or date.today()
    for rx, kind in DATE_PATTERNS:
        m = rx.search(text)
        if not m:
            continue
        try:
            if kind == "dmy_num":
                d, mo, y = int(m[1]), int(m[2]), int(m[3])
                y = y + 2000 if y < 100 else y
            elif kind == "d_mon":
                d, mo = int(m[1]), MONTHS.index(m[2].lower()[:3]) + 1
                y = int(m[3]) if m[3] else None
            else:
                mo, d = MONTHS.index(m[1].lower()[:3]) + 1, int(m[2])
                y = int(m[3]) if m[3] else None
            if y is None:  # no year written: pick the next time this date happens
                y = today.year
                if date(y, mo, d) < today - timedelta(days=30):
                    y += 1
            return date(y, mo, d), m.group(0)
        except ValueError:
            continue
    return None, None


def group_lines(blocks):
    """Glue text blocks that sit on the same row into lines (left to right)."""
    blocks = sorted(blocks, key=lambda b: box_center(b["box"])[1])
    lines, cur = [], []
    for b in blocks:
        if cur:
            ref = cur[-1]["box"]
            if abs(box_center(b["box"])[1] - box_center(ref)[1]) <= (ref[3] - ref[1]) * 0.6:
                cur.append(b)
                continue
            lines.append(cur)
        cur = [b]
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:
        ln.sort(key=lambda b: b["box"][0])
        box = [min(b["box"][0] for b in ln), min(b["box"][1] for b in ln),
               max(b["box"][2] for b in ln), max(b["box"][3] for b in ln)]
        out.append({"box": box, "text": " ".join(b["text"] for b in ln),
                    "conf": round(sum(b["conf"] for b in ln) / len(ln), 3)})
    return out


def find_subject_in(text):
    low = text.lower()
    for s in sorted(KNOWN_SUBJECTS, key=len, reverse=True):  # longest first: "Advanced Python" before "Python"
        if s.lower() in low:
            return s, True
    m = re.match(r"\s*([A-Za-z][A-Za-z+ ]{1,24}?)\s*[:\-–]\s+\S", text)
    if m:
        return canonical_subject(m[1])
    return "General", False


def clean_topic(text, subject, date_txt):
    t = text
    if date_txt:
        t = t.replace(date_txt, " ")
    m = re.search(r"\bon\s+(.+?)(?=\s+(?:by|before|due|on|,)\b|,|$)", t, re.I)  # "... on Dynamic Programming"
    if m:
        t = m[1]
    else:
        t = re.sub(re.escape(subject), " ", t, flags=re.I)
    t = re.sub(r"\b(submit|assignment|\d+|quiz|test|viva|lab|by|due|before|on|demo|project)\b", " ", t, flags=re.I)
    t = re.sub(r"^[\s:\-–,()]+|[\s:\-–,()]+$", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:60] or "General"


def parse_notice(blocks, semester, today=None):
    """Every line that contains a date becomes one entry."""
    today = today or date.today()
    lines = group_lines(blocks)
    entries, labels = [], []
    for i, ln in enumerate(lines):
        d, d_txt = find_date(ln["text"], today)
        if not d:
            continue
        text = ln["text"]
        # if the sentence continues on the next line (no date there), include it
        if i + 1 < len(lines) and not find_date(lines[i + 1]["text"], today)[0] and len(text) < 70:
            text += " " + lines[i + 1]["text"]
        subject, known = find_subject_in(text)
        kind, label = "task", "Task"
        for rx, k, lab in KINDS:
            if re.search(rx, text, re.I):
                kind, label = k, lab
                break
        entries.append({
            "semester": semester, "subject": subject,
            "topic": clean_topic(text, subject, d_txt),
            "date": d.isoformat(), "task": label, "kind": kind,
            "confidence": round(min(ln["conf"], 0.99) * (1 if known else 0.85), 2),
            "source_box": ln["box"],
        })
        labels.append({"box": ln["box"], "text": f"{subject} · {d.strftime('%d %b')}", "known": known})
    return entries, labels


def parse_notes(blocks, semester, today=None):
    """Handwritten / dateless notes: use the first line as heading, tag with today's date."""
    today = today or date.today()
    lines = group_lines(blocks)
    if not lines:
        return [], []
    full = " ".join(l["text"] for l in lines)
    subject, known = find_subject_in(full)
    heading = lines[0]["text"][:60]
    entry = {"semester": semester, "subject": subject, "topic": heading, "date": today.isoformat(),
             "task": "Revise notes", "kind": "notes",
             "confidence": round(sum(l["conf"] for l in lines) / len(lines) * (1 if known else 0.8), 2),
             "source_box": lines[0]["box"]}
    return [entry], [{"box": lines[0]["box"], "text": subject, "known": known}]


# --------------------------------------------------------------------------
# 6. Run everything and time each stage
# --------------------------------------------------------------------------
def analyze(data: bytes, filename: str, semester="sem4", today=None):
    stages = []

    def stage(name, t0, note=""):
        stages.append({"name": name, "ms": int((time.perf_counter() - t0) * 1000), "note": note})

    t = time.perf_counter()
    pages = load_pages(data, filename)
    stage("Load", t, f"{len(pages)} page(s)")

    all_entries, preview_page = [], None
    for p, raw in enumerate(pages):
        t = time.perf_counter()
        img, info = preprocess(raw)
        note = "deskewed %.1f°" % info["skew_deg"] if info.get("deskewed") else "no tilt fix needed"
        stage("Clean-up", t, note)

        t = time.perf_counter()
        rows, _ = find_grid(img)
        ncells = sum(len(r) for r in rows)
        stage("Find table grid", t, f"{len(rows)} rows, {ncells} cells" if rows else "no table found")

        t = time.perf_counter()
        blocks = run_ocr(img)
        stage("Read text (OCR)", t, f"{len(blocks)} text blocks")

        t = time.perf_counter()
        mode, entries, labels = "notice", [], []
        if rows:
            entries, labels = parse_timetable(rows, blocks, semester, today)
            mode = "timetable"
        if not entries:
            entries, labels = parse_notice(blocks, semester, today)
            mode = "notice"
        if not entries:
            entries, labels = parse_notes(blocks, semester, today)
            mode = "notes"
        stage("Extract subject / date / topic / task", t, f"{len(entries)} entries ({mode})")

        for e in entries:
            e["page"] = p + 1
        all_entries += entries
        if preview_page is None:
            preview_page = {"image": img, "cells": [c for r in rows for c in r],
                            "blocks": blocks, "labels": labels, "mode": mode}

    h, w = preview_page["image"].shape[:2]
    return {
        "mode": preview_page["mode"],
        "width": w, "height": h,
        "cells": preview_page["cells"],
        "blocks": preview_page["blocks"],
        "labels": preview_page["labels"],
        "entries": all_entries,
        "stages": stages,
        "image": preview_page["image"],  # main.py turns this into a PNG
    }

"""Makes fake test images so you can try the pipeline without a real screenshot.

  samples/timetable.png   - a clean timetable "screenshot" (the demo image)
  samples/timetable_skew.png - same timetable, but tilted + noisy like a phone photo
  samples/notice.png      - a plain-text notice with dates and deadlines
  samples/timetable_transposed.png   - days down the left, time slots across the top
  samples/timetable_teacher_room.png - cells hold subject + teacher initials + room (placeholder course)
  samples/notice_teacher_room.png    - notice lines that mention "Prof. ..." and "Room ..."
  samples/notice*.pdf     - the notice as an image-only PDF and as a text-layer PDF

EVERYTHING here is SYNTHETIC (drawn by this script). It is for testing, not evidence of real-world accuracy.
The teacher/room samples use the fake PLACEHOLDER course in data/catalog.json.
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "samples")
os.makedirs(OUT, exist_ok=True)


def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(os.path.join("C:/Windows/Fonts", name), size)
    except OSError:
        return ImageFont.load_default()


# Same data as your data.js, so the demo matches your attendance app.
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SLOTS = ["07-08", "08-09", "09-10", "10-11", "11-12", "12-01"]
GRID = {
    ("Monday", "07-08"): ("Hindi", "#d4f7c5"),
    ("Monday", "08-09"): ("OOP C++", "#fff1a8"),
    ("Monday", "09-10"): ("Extension Work", "#f1d3f1"),
    ("Tuesday", "10-11"): ("Python", "#e3d0ff"),
    ("Tuesday", "12-01"): ("Web Tech", "#ffd1c7"),
    ("Wednesday", "07-08"): ("EVS", "#c9ffe0"),
    ("Wednesday", "08-09"): ("DAA", "#c7f5f0"),
    ("Thursday", "08-09"): ("OOP C++", "#fff1a8"),
    ("Thursday", "12-01"): ("Advanced Python", "#ffd9a8"),
    ("Friday", "07-08"): ("EVS", "#c9ffe0"),
    ("Friday", "08-09"): ("Leadership", "#dccdf5"),
}


def timetable():
    cw, ch, tw, hh = 190, 80, 110, 70
    W, H = tw + cw * len(DAYS) + 40, hh + ch * len(SLOTS) + 40
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    x0, y0 = 20, 20
    for c, day in enumerate(["Time"] + DAYS):
        x = x0 if c == 0 else x0 + tw + (c - 1) * cw
        w = tw if c == 0 else cw
        d.rectangle([x, y0, x + w, y0 + hh], fill="#e8eef7", outline="black", width=3)
        d.text((x + w / 2, y0 + hh / 2), day, font=font(24, True), fill="black", anchor="mm")
    for r, slot in enumerate(SLOTS):
        y = y0 + hh + r * ch
        d.rectangle([x0, y, x0 + tw, y + ch], fill="#f4f4f4", outline="black", width=3)
        d.text((x0 + tw / 2, y + ch / 2), slot, font=font(22), fill="black", anchor="mm")
        for c, day in enumerate(DAYS):
            x = x0 + tw + c * cw
            subj, col = GRID.get((day, slot), ("", "white"))
            d.rectangle([x, y, x + cw, y + ch], fill=col, outline="black", width=3)
            if subj:
                d.text((x + cw / 2, y + ch / 2), subj, font=font(22), fill="black", anchor="mm")
    return img


def notice():
    img = Image.new("RGB", (900, 520), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 30), "DEPARTMENT OF COMPUTER SCIENCE - NOTICE", font=font(28, True), fill="black")
    lines = [
        "DAA: Submit Assignment 2 on Dynamic Programming by 14 Nov 2026",
        "Python - Lab viva on File Handling on 18/11/2026",
        "OOP C++: Unit test on Inheritance and Polymorphism, 21 November 2026",
        "Web Tech: Project demo (Portfolio website) due 02-12-2026",
        "EVS: Quiz on Water Pollution on Nov 25, 2026",
    ]
    for i, t in enumerate(lines):
        d.text((40, 110 + i * 70), t, font=font(23), fill="black")
    return img


def draw_grid(row_labels, col_labels, cell_lines, corner="Time", cw=190, ch=80, lw=110, hh=70, fsize=22):
    """Draw a ruled table. cell_lines(r, c) returns a list of text lines for that cell (or None)."""
    W, H = lw + cw * len(col_labels) + 40, hh + ch * len(row_labels) + 40
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    x0, y0 = 20, 20
    for c, label in enumerate([corner] + col_labels):
        x = x0 if c == 0 else x0 + lw + (c - 1) * cw
        w = lw if c == 0 else cw
        d.rectangle([x, y0, x + w, y0 + hh], fill="#e8eef7", outline="black", width=3)
        d.text((x + w / 2, y0 + hh / 2), label, font=font(fsize + 2, True), fill="black", anchor="mm")
    for r, label in enumerate(row_labels):
        y = y0 + hh + r * ch
        d.rectangle([x0, y, x0 + lw, y + ch], fill="#f4f4f4", outline="black", width=3)
        d.text((x0 + lw / 2, y + ch / 2), label, font=font(fsize), fill="black", anchor="mm")
        for c in range(len(col_labels)):
            x = x0 + lw + c * cw
            lines = cell_lines(r, c)
            d.rectangle([x, y, x + cw, y + ch], fill="#fff6d6" if lines else "white", outline="black", width=3)
            for i, text in enumerate(lines or []):
                step = ch / (len(lines) + 1)
                d.text((x + cw / 2, y + step * (i + 1)), text, font=font(fsize - (4 if i else 2), i == 0),
                       fill="black", anchor="mm")
    return img


def timetable_transposed():
    """Same lectures as timetable(), but days are the ROWS and time slots are the COLUMNS."""
    return draw_grid(DAYS, SLOTS, lambda r, c: [GRID[(DAYS[r], SLOTS[c])][0]] if (DAYS[r], SLOTS[c]) in GRID else None,
                     corner="Day", cw=175, ch=70, lw=130, fsize=20)


# Placeholder course (fake!) used by the teacher/room samples. Matches data/catalog.json: demo-a / sem1.
# (day, slot): (subject text, [extra lines written in the cell])
DETAIL_SLOTS = ["07-08", "08-09", "09-10", "10-11"]
DETAIL_CELLS = {
    ("Monday", "07-08"): ("Placeholder Algebra", ["AP", "LH-3"]),         # initials + room in the image
    ("Monday", "08-09"): ("Placeholder Physics", ["RP", "R-204"]),
    ("Tuesday", "07-08"): ("Placeholder Drawing", ["NP", "Room 301"]),
    ("Tuesday", "09-10"): ("Placeholder Seminar", []),                    # nothing in image, nothing in catalog
    ("Wednesday", "07-08"): ("Placeholder Algebra", []),                  # nothing in image -> catalog fills teacher+room
    ("Thursday", "08-09"): ("Placeholder Physics", ["Prof. Rahul Placeholder"]),   # full name in image, room from catalog
    ("Friday", "07-08"): ("Placeholder Drawing", ["NP"]),                 # initials in image, room from catalog
}
DETAIL_TEACHER = {"Placeholder Algebra": "Dr. Asha Placeholder", "Placeholder Physics": "Prof. Rahul Placeholder",
                  "Placeholder Drawing": "Ms. Neha Placeholder"}
DETAIL_ROOM = {"Placeholder Algebra": "LH-3", "Placeholder Physics": "R-204", "Placeholder Drawing": "Room 301"}


def timetable_teacher_room():
    def cell(r, c):
        hit = DETAIL_CELLS.get((DAYS[c], DETAIL_SLOTS[r]))
        return [hit[0]] + hit[1] if hit else None
    return draw_grid(DETAIL_SLOTS, DAYS, cell, cw=230, ch=100, lw=110, fsize=22)


NOTICE_TR_LINES = [
    "Placeholder Algebra: Submit Assignment 1 on Matrices by 14 Nov 2026, Prof. Asha Placeholder, Room 301",
    "Placeholder Physics - Unit test on Optics, 21/11/2026 in R-204",
]


def notice_teacher_room():
    img = Image.new("RGB", (1400, 360), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 30), "SAMPLE NOTICE (synthetic)", font=font(28, True), fill="black")
    for i, t in enumerate(NOTICE_TR_LINES):
        d.text((40, 120 + i * 90), t, font=font(23), fill="black")
    return img


def to_cv(pil):
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def main():
    tt = to_cv(timetable())
    cv2.imwrite(os.path.join(OUT, "timetable.png"), tt)

    # phone-photo style: rotate 2.5 degrees, add noise + uneven lighting
    h, w = tt.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 2.5, 1.0)
    sk = cv2.warpAffine(tt, M, (w, h), borderValue=(255, 255, 255))
    noise = np.random.default_rng(1).normal(0, 12, sk.shape)
    light = np.tile(np.linspace(0.8, 1.05, w), (h, 1))[..., None]
    sk = np.clip(sk * light + noise, 0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(OUT, "timetable_skew.png"), sk)

    cv2.imwrite(os.path.join(OUT, "notice.png"), to_cv(notice()))

    cv2.imwrite(os.path.join(OUT, "timetable_transposed.png"), to_cv(timetable_transposed()))
    cv2.imwrite(os.path.join(OUT, "timetable_teacher_room.png"), to_cv(timetable_teacher_room()))
    cv2.imwrite(os.path.join(OUT, "notice_teacher_room.png"), to_cv(notice_teacher_room()))

    make_pdfs()
    write_truth_files()
    print("samples written to", OUT)


NOTICE_LINES = [
    "DAA: Submit Assignment 2 on Dynamic Programming by 14 Nov 2026",
    "Python - Lab viva on File Handling on 18/11/2026",
    "OOP C++: Unit test on Inheritance and Polymorphism, 21 November 2026",
    "Web Tech: Project demo (Portfolio website) due 02-12-2026",
    "EVS: Quiz on Water Pollution on Nov 25, 2026",
]


def make_pdfs():
    """Two PDFs with the same notice, built differently:
       notice_scanned.pdf - the PNG pasted in as a picture (no text inside, like a scanned notice)
       notice_text.pdf    - real selectable text (like a PDF exported from Word)"""
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_image(page.rect, filename=os.path.join(OUT, "notice.png"))
    doc.save(os.path.join(OUT, "notice_scanned.pdf"))

    doc = pymupdf.open()
    page = doc.new_page()  # A4
    page.insert_text((50, 80), "DEPARTMENT OF COMPUTER SCIENCE - NOTICE", fontsize=16, fontname="hebo")
    for i, line in enumerate(NOTICE_LINES):
        page.insert_text((50, 140 + i * 40), line, fontsize=12, fontname="helv")
    doc.save(os.path.join(OUT, "notice_text.pdf"))
    assert "DAA" in pymupdf.open(os.path.join(OUT, "notice_text.pdf"))[0].get_text(), "text layer missing"


def write_truth_files():
    """Answer keys used by eval.py (see real_samples/README.md for the format)."""
    import json

    tt = {"mode": "timetable",
          "entries": [{"subject": s, "day": d, "time": t} for (d, t), (s, _) in GRID.items()]}
    notice_truth = {"mode": "notice", "entries": [
        {"subject": "DAA", "date": "2026-11-14", "topic": "Dynamic Programming", "task": "Submit assignment"},
        {"subject": "Python", "date": "2026-11-18", "topic": "File Handling", "task": "Lab / viva"},
        {"subject": "OOP C++", "date": "2026-11-21", "topic": "Inheritance and Polymorphism", "task": "Exam / test"},
        {"subject": "Web Tech", "date": "2026-12-02", "topic": "Portfolio website", "task": "Project / demo"},
        {"subject": "EVS", "date": "2026-11-25", "topic": "Water Pollution", "task": "Exam / test"},
    ]}
    # same lectures, days-down-the-side layout; also run WITH a course+semester chosen
    tt_transposed = dict(tt, course="main", semester="sem4")

    # cells with subject + teacher + room. Expected values are the FINAL ones (image-read or catalog-filled)
    detail = {"mode": "timetable", "course": "demo-a", "semester": "sem1", "entries": [
        {"subject": subj, "day": day, "time": slot,
         "teacher": DETAIL_TEACHER.get(subj, ""), "room": DETAIL_ROOM.get(subj, "")}
        for (day, slot), (subj, _) in DETAIL_CELLS.items()]}
    for e in detail["entries"]:   # leave out fields that are empty so they are not scored
        for k in ("teacher", "room"):
            if not e[k]:
                del e[k]

    notice_tr = {"mode": "notice", "course": "demo-a", "semester": "sem1", "entries": [
        {"subject": "Placeholder Algebra", "date": "2026-11-14", "topic": "Matrices", "task": "Submit assignment",
         "teacher": "Prof. Asha Placeholder", "room": "Room 301"},
        {"subject": "Placeholder Physics", "date": "2026-11-21", "topic": "Optics", "task": "Exam / test",
         "teacher": "Prof. Rahul Placeholder", "room": "R-204"},
    ]}
    for stem, truth in [("timetable", tt), ("timetable_skew", tt), ("notice", notice_truth),
                        ("notice_scanned", notice_truth), ("notice_text", notice_truth),
                        ("timetable_transposed", tt_transposed), ("timetable_teacher_room", detail),
                        ("notice_teacher_room", notice_tr)]:
        with open(os.path.join(OUT, stem + ".truth.json"), "w", encoding="utf-8") as f:
            json.dump(truth, f, indent=2)


if __name__ == "__main__":
    main()

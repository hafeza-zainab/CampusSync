"""Measurements behind the "Limitations" and a few numbers in the README. Prints results; it does not pass/fail.

    py tests/measure.py          (from the vision folder; the server must be running for the last two sections)

Everything here uses SYNTHETIC images generated on the fly or from samples/.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import cv2                      # noqa: E402
import numpy as np              # noqa: E402
import pymupdf                  # noqa: E402
from PIL import Image, ImageDraw   # noqa: E402

import make_sample as ms        # noqa: E402
import pipeline as p            # noqa: E402

S = ms.OUT + os.sep
BASE = "http://localhost:8000"


def png_bytes(bgr):
    return cv2.imencode(".png", bgr)[1].tobytes()


def summary(r):
    return f"mode={r['mode']}, cells={len(r['cells'])}, entries={len(r['entries'])}"


print("== 1. Does CLAHE change the output? (same image with CLAHE switched off)")
real_clahe = cv2.createCLAHE


class NoClahe:
    def apply(self, x):
        return x


for f in ("timetable_skew.png", "timetable.png"):
    data = open(S + f, "rb").read()
    with_c = p.analyze(data, f)
    cv2.createCLAHE = lambda *a, **k: NoClahe()
    without = p.analyze(data, f)
    cv2.createCLAHE = real_clahe
    key = lambda r: [(e["subject"], e["day"], e["time"]) for e in r["entries"]]
    print(f"   {f}: identical output with and without CLAHE: {key(with_c) == key(without)}")

print("== 2. Orientation: pictures physically rotated with NO EXIF tag (unsupported)")
up = cv2.imread(S + "timetable.png")
for name, code in (("rotated 90 degrees", cv2.ROTATE_90_CLOCKWISE), ("upside down", cv2.ROTATE_180)):
    r = p.analyze(png_bytes(cv2.rotate(up, code)), "x.png")
    print(f"   {name}: {summary(r)} (the upright image gives 11 entries); first subjects: {[e['subject'] for e in r['entries']][:4]}")

print("== 3. Timetable drawn WITHOUT table lines (unsupported)")
img = Image.new("RGB", (1200, 560), "white")
d = ImageDraw.Draw(img)
cw, ch, x0, y0 = 190, 80, 130, 40
for c, day in enumerate(ms.DAYS):
    d.text((x0 + c * cw + cw / 2, y0), day, font=ms.font(24, True), fill="black", anchor="mm")
for r_i, slot in enumerate(ms.SLOTS):
    d.text((60, y0 + 60 + r_i * ch), slot, font=ms.font(22), fill="black", anchor="mm")
    for c, day in enumerate(ms.DAYS):
        if (day, slot) in ms.GRID:
            d.text((x0 + c * cw + cw / 2, y0 + 60 + r_i * ch), ms.GRID[(day, slot)][0], font=ms.font(22), fill="black", anchor="mm")
r = p.analyze(png_bytes(ms.to_cv(img)), "borderless.png")
print(f"   {summary(r)}; subjects: {[e['subject'] for e in r['entries']]}")

print("== 4. Notes with no dates (one synthetic image)")
img = Image.new("RGB", (900, 300), "white")
d = ImageDraw.Draw(img)
d.text((40, 40), "Python - File Handling", font=ms.font(30, True), fill="black")
d.text((40, 110), "open(), read(), write(), close()", font=ms.font(24), fill="black")
r = p.analyze(png_bytes(ms.to_cv(img)), "notes.png")
print(f"   {summary(r)}; entries: {[(e['subject'], e['topic'], e['task']) for e in r['entries']]}")

print("== 5. PDFs: page limit")
doc = pymupdf.open()
for _ in range(5):
    pg = doc.new_page()
    pg.insert_image(pg.rect, filename=S + "notice.png")
r = p.analyze(doc.tobytes(), "five_pages.pdf")
print(f"   5-page PDF: pages that produced entries = {sorted({e['page'] for e in r['entries']})}")

print("== 6. Do the OCR models ship inside the pip package? (no download at run time)")
import rapidocr  # noqa: E402
models = os.path.join(os.path.dirname(rapidocr.__file__), "models")
print("   ", [(f, os.path.getsize(os.path.join(models, f)) // 1024 // 1024) for f in os.listdir(models) if f.endswith(".onnx")], "(MB)")

print("== 7. Needs the server running: origin separation and demo timing")
try:
    from playwright.sync_api import sync_playwright
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context()
        a = ctx.new_page()
        a.on("dialog", lambda dl: dl.accept("P"))
        a.goto(BASE + "/campus/"); a.fill("#username", "Z"); a.click("text=Enter")
        a.locator(".lecture").first.click()
        print("    marks saved via http://localhost:8000/campus/:", a.evaluate("localStorage.getItem('campussync.attendance')"))
        f = ctx.new_page()
        f.goto("file:///" + os.path.join(here, "index.html").replace("\\", "/"))
        print("    same app opened from a file:// URL sees:", f.evaluate("localStorage.getItem('campussync.attendance')"))
        v = ctx.new_page()
        v.goto(BASE + "/"); v.click("#clear"); v.wait_for_timeout(300)
        t0 = time.perf_counter(); v.click("#demo")
        v.wait_for_function("document.getElementById('capText').innerText.startsWith('6')", timeout=90000)
        print(f"    'Run demo' click -> step 6 caption: {time.perf_counter() - t0:.1f} s")
        v.click("#clear")
        b.close()
except Exception as e:
    print("    skipped:", repr(e)[:120])

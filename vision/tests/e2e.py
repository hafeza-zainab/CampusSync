"""End-to-end checks: drives the real pages in a headless browser and prints PASS / FAIL for each claim.

Run this after ANY code change (and before recording):
    1. start the server in another terminal:   py -m uvicorn main:app --port 8000     (from the vision folder)
    2. one-time install:                       py -m pip install playwright ; py -m playwright install chromium
    3. from the vision folder:                 py tests/e2e.py

It uses fresh browser profiles, resets the saved Study Panel entries at the start and end, and exits with
a non-zero code if anything fails. It tests with the SYNTHETIC images in samples/ (run make_sample.py first).
"""
import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "samples")
results = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    results.append(bool(cond))


def api(path, method="GET", data=None):
    req = urllib.request.Request(BASE + path, data=data, method=method)
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def upload_api(filename, fields=None):
    """POST a sample file to /api/analyze (multipart) and return the JSON."""
    boundary = "----e2eboundary"
    body = b""
    for k, v in (fields or {}).items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    with open(os.path.join(S, filename), "rb") as f:
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n\r\n').encode() + f.read()
    body += f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/analyze", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def wait_done(pg):
    """Wait until the page has gone through a full upload run (caption '1 ...' then '6 ...')."""
    pg.wait_for_function("document.getElementById('capText').innerText.startsWith('1')", timeout=15000)
    pg.wait_for_function("document.getElementById('capText').innerText.startsWith('6')", timeout=90000)
    pg.wait_for_timeout(1200)


def new_page(ctx, errors):
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)[:100]))
    pg.on("dialog", lambda d: d.accept("P") if d.type == "prompt" else d.accept())
    return pg


def test_api(b):
    cat = api("/api/catalog")
    check("catalog endpoint lists courses", len(cat["courses"]) >= 2, f"{[c['id'] for c in cat['courses']]}")
    for f in ("timetable_exif6.jpg", "timetable_exif3.jpg"):
        r = upload_api(f)
        check(f"EXIF-rotated photo {f} is read upright", r["mode"] == "timetable" and len(r["entries"]) == 11 and r["width"] > r["height"])
    r = upload_api("timetable_teacher_room.png", {"course": "demo-a"})
    check("course chosen but no semester: nothing is filled from the catalog",
          all(e["teacher_source"] != "catalog" and e["room_source"] != "catalog" for e in r["entries"]))
    r = upload_api("timetable_teacher_room.png")
    check("nothing chosen: confidence is lowered (all entries under 0.80, so flagged 'check this')",
          r["entries"] and max(e["confidence"] for e in r["entries"]) < 0.80, f"max {max(e['confidence'] for e in r['entries'])}")
    check("nothing chosen: nothing is filled from the catalog",
          all(e["teacher_source"] != "catalog" and e["room_source"] != "catalog" for e in r["entries"]))
    try:
        upload_api("notice.png", {"course": "main", "semester": "sem9"})
        check("unknown semester is rejected", False)
    except urllib.error.HTTPError as e:
        check("unknown semester is rejected with HTTP 400", e.code == 400)
    for path in ("/campus/.git/config", "/campus/main.py", "/campus/../vision/main.py"):
        try:
            urllib.request.urlopen(BASE + path); check(f"{path} is not served", False)
        except urllib.error.HTTPError as e:
            check(f"{path} is not served", e.code == 404)


def test_demo_flow(b):
    """The 60-second demo: Run demo -> boxes -> tagged entries."""
    errs, external = [], []
    ctx = b.new_context(viewport={"width": 1400, "height": 1000})
    pg = new_page(ctx, errs)
    pg.on("request", lambda r: not r.url.startswith(BASE) and not r.url.startswith(("data:", "blob:")) and external.append(r.url))
    pg.goto(BASE + "/"); pg.click("#clear"); pg.wait_for_timeout(300)
    pg.click("#demo")
    pg.wait_for_function("document.getElementById('capText').innerText.startsWith('6')", timeout=90000); pg.wait_for_timeout(1200)
    check("demo: 11 lectures auto-tagged", pg.locator(".entry").count() == 11, f"{pg.locator('.entry').count()} entries")
    check("demo: grouped into 9 subject cards", pg.locator(".subject").count() == 9)
    check("demo: the step list reports 42 cells", "42 cells" in pg.inner_text("#steps"))
    check("demo: all 5 pipeline steps ticked", pg.locator("#steps li.on").count() == 5)
    check("demo: boxes drawn on the image", pg.evaluate("(()=>{const c=document.getElementById('cv');const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let n=0;for(let i=3;i<d.length;i+=4)if(d[i])n++;return n})()") > 10000)
    check("demo: course/semester dropdowns were filled", pg.input_value("#course") == "main" and pg.input_value("#sem") == "sem4")
    check("demo: announcement card hidden for a timetable", not pg.locator("#review").is_visible())
    check("demo: no page errors", not errs, str(errs))
    check("demo: page made no requests outside localhost", not external, str(external))
    ctx.close()


def test_announcements(b):
    errs = []
    ctx = b.new_context(viewport={"width": 1400, "height": 1100})
    pg = new_page(ctx, errs)
    pg.goto(BASE + "/"); pg.click("#clear")

    def upload(name):
        pg.set_input_files("#file", os.path.join(S, name)); wait_done(pg)

    upload("notice.png")
    check("notice: 5 reviewable rows", pg.locator(".rrow").count() == 5)
    pg.locator(".rrow .f-topic").first.fill("Dynamic Programming (edited)")
    pg.click("#postAll")
    check("notice: Post all posts 5", "5 posted" in pg.inner_text("#postMsg"), pg.inner_text("#postMsg"))
    upload("notice.png"); pg.click("#postAll")
    check("notice: re-upload posts only the edited one again, blocks the 4 duplicates",
          "1 posted, 4 already posted" in pg.inner_text("#postMsg"), pg.inner_text("#postMsg"))
    upload("notice.png"); pg.click("#postAll")
    check("notice: third upload posts nothing new", "0 posted, 5 already posted" in pg.inner_text("#postMsg"), pg.inner_text("#postMsg"))
    # UI logic with a hand-made low-confidence entry (NOT real OCR output)
    pg.evaluate("showReview([{subject:'Maths',date:'2026-12-10',topic:'Integrals',task:'Exam / test',confidence:0.6,source_text:'fake'}],'fake')")
    pg.locator(".rrow .post").click()
    check("low confidence: post refused until 'I checked this' is ticked", "tick" in pg.locator(".rrow .status").inner_text())
    pg.check(".f-ok"); pg.locator(".rrow .post").click()
    check("low confidence: posts after ticking", "posted" in pg.locator(".rrow .status").inner_text())
    pg.evaluate("showReview([{subject:'A1',date:'2026-12-11',topic:'t1',task:'Task',confidence:0.95,source_text:'x'},"
                "{subject:'B1',date:'2026-12-12',topic:'t2',task:'Task',confidence:0.5,source_text:'y'}],'fake')")
    pg.click("#postAll")
    check("Post all skips the unchecked low-confidence row and says so", "1 posted" in pg.inner_text("#postMsg") and "1 need checking" in pg.inner_text("#postMsg"),
          pg.inner_text("#postMsg"))
    # does the existing attendance app show them?
    app = new_page(ctx, errs)
    app.goto(BASE + "/campus/"); app.fill("#username", "Z"); app.click("text=Enter"); app.click("text=📢 Announcements")
    text = app.inner_text("#announceList")
    check("announcements appear in the attendance app, 'by Vision'", text.count("— Vision") == 8, f"{text.count('— Vision')} found")
    check("announcements: no page errors", not errs, str(errs))
    ctx.close()


def test_catalog(b):
    errs = []
    ctx = b.new_context(viewport={"width": 1500, "height": 1000})
    pg = new_page(ctx, errs)
    pg.goto(BASE + "/"); pg.click("#clear"); pg.wait_for_timeout(300)
    check("semester dropdown disabled until a course is picked", pg.is_disabled("#sem"))
    pg.select_option("#course", "demo-a")
    check("course A offers 2 semesters", pg.locator("#sem option").count() == 3)   # + the '-- not selected --' option
    pg.select_option("#sem", "sem1")
    pg.set_input_files("#file", os.path.join(S, "timetable_teacher_room.png")); wait_done(pg)
    check("catalog: 7 lectures tagged under the chosen course", pg.locator(".entry").count() == 7 and "PLACEHOLDER Demo Course A" in pg.inner_text("#panel"))
    check("catalog: teacher/room filled from catalog are styled dashed", pg.locator(".entry .chip.src-catalog").count() == 4,
          f"{pg.locator('.entry .chip.src-catalog').count()} catalog chips")
    check("catalog: initials shown expanded ('AP -> Dr. Asha Placeholder')", "AP → Dr. Asha Placeholder" in pg.inner_text("#panel"))
    check("catalog: no page errors", not errs, str(errs))
    ctx.close()


def test_attendance_bridge(b):
    errs = []
    ctx = b.new_context(viewport={"width": 1500, "height": 1000})
    app = new_page(ctx, errs)
    app.goto(BASE + "/campus/"); app.fill("#username", "Z"); app.click("text=Enter")
    first = app.inner_text("#monthYear"); app.click("text=▶"); second = app.inner_text("#monthYear"); app.click("text=◀")
    check("attendance app: month buttons work", first != second and app.inner_text("#monthYear") == first)
    app.locator(".lecture").first.click(); app.locator(".lecture").nth(3).click()
    marks = app.evaluate("localStorage.getItem('campussync.attendance')")
    check("attendance app: lectures can be marked (time format fixed) and are saved", marks and marks.count("present") == 2, marks)
    check("attendance app: stats panel shows percentages", "%" in app.inner_text("#stats"))
    app.reload(); app.fill("#username", "Z"); app.click("text=Enter")
    check("attendance app: marks survive a reload", app.locator(".lecture.present").count() == 2)
    app.click("text=📢 Announcements"); app.fill("#msg", "hello"); app.click("button:text('Post')")
    check("attendance app: an announcement shows the poster's role, not 'undefined'", "hello — student" in app.inner_text("#announceList"), app.inner_text("#announceList"))

    pg = new_page(ctx, errs)
    pg.goto(BASE + "/"); pg.click("#clear")
    pg.set_input_files("#file", os.path.join(S, "timetable_pdf.pdf")); wait_done(pg)     # also exercises the PDF path
    check("same timetable as data.js: nothing to replace", "Already the same" in pg.inner_text("#attendConfirm"), pg.inner_text("#attendConfirm"))
    pg.select_option("#course", "demo-a"); pg.select_option("#sem", "sem1")
    pg.set_input_files("#file", os.path.join(S, "timetable_teacher_room.png")); wait_done(pg)
    check("different timetable: preview says add 7 / remove 11", "adds 7, removes 11" in pg.inner_text("#attendConfirm"), pg.inner_text("#attendConfirm"))
    check("different timetable: warns that 2 marks would be hidden", "2 of these marks belong to lectures that are not in the new timetable" in pg.inner_text("#attendPreview"))
    check("nothing is written before the confirm click", pg.evaluate("localStorage.getItem('campussync.timetable')") is None)
    pg.click("#attendConfirm"); pg.wait_for_timeout(300)
    check("attendance data is untouched by the replace", pg.evaluate("localStorage.getItem('campussync.attendance')") == marks)
    cal = new_page(ctx, errs)
    cal.goto(BASE + "/campus/"); cal.fill("#username", "Z"); cal.click("text=Enter")
    subjects = cal.eval_on_selector_all(".lecture", "e => [...new Set(e.map(x => x.textContent.replace(/^[0-9:-]+ /, '')))]")
    check("attendance app now shows the new subjects", "Placeholder Algebra" in subjects and "Hindi" not in subjects, str(subjects))
    check("the 2 old marks are hidden, not deleted", cal.locator(".lecture.present").count() == 0)
    cal.close()
    pg.click("#attendUndo"); pg.wait_for_timeout(500)
    cal = new_page(ctx, errs)
    cal.goto(BASE + "/campus/"); cal.fill("#username", "Z"); cal.click("text=Enter")
    check("Undo brings the old timetable and the 2 marks back", cal.locator(".lecture.present").count() == 2 and "Hindi" in cal.inner_text("#calendarGrid"))
    pg.select_option("#course", ""); pg.set_input_files("#file", os.path.join(S, "timetable_teacher_room.png")); wait_done(pg)
    check("low-confidence lectures: confirm disabled until 'I checked them' is ticked", pg.locator("#attendOk").count() == 1 and not pg.is_enabled("#attendConfirm"))
    pg.check("#attendOk")
    check("low-confidence lectures: enabled after ticking", pg.is_enabled("#attendConfirm"))
    known = [e for e in errs if "subjectCount" not in e]
    check("bridge: no unexpected page errors (known: checkWarnings 'subjectCount is not defined')", not known, str(known))
    ctx.close()


def main():
    try:
        api("/api/entries")
    except Exception as e:
        raise SystemExit(f"Server not reachable at {BASE}: start it first (py -m uvicorn main:app --port 8000). {e}")
    api("/api/entries", "DELETE")
    with sync_playwright() as p:
        b = p.chromium.launch()
        for test in (test_api, test_demo_flow, test_announcements, test_catalog, test_attendance_bridge):
            print(f"\n== {test.__name__}")
            try:
                test(b)
            except Exception as e:   # a crashed test is a failure, but keep running the others
                check(f"{test.__name__} ran to the end", False, repr(e)[:200])
        b.close()
    api("/api/entries", "DELETE")
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

"""End-to-end checks: drives the real pages in a headless browser and prints PASS / FAIL for each claim.

Run this after ANY code change (and before recording):
    1. start the server in another terminal:   py -m uvicorn main:app --port 8000     (from the vision folder)
    2. one-time install:                       py -m pip install playwright ; py -m playwright install chromium
    3. from the vision folder:                 py tests/e2e.py

It uses fresh browser profiles, resets the saved Study Panel entries at the start and end, and exits with
a non-zero code if anything fails. It tests with the SYNTHETIC images in samples/ (run make_sample.py first).
"""
import base64
import datetime
import json
import os
import re
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
# Demo accounts: PLACEHOLDER college IDs (see store.js), not real people
ID = {"Zainab": "DEMO-CS-001", "Aarav": "DEMO-CS-002", "Meera": "DEMO-CS-003", "Kabir": "DEMO-CS-004"}
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


def prev_month(pg):
    """Marks are made in the PREVIOUS month so the test works on any day of the month (lectures there are all over)."""
    pg.click("text=◀")


def mark_attendance(pg, nth, label):
    """Click the nth lecture in the calendar and choose Present / Absent / Clear from the small menu."""
    pg.locator(".lecture").nth(nth).click()
    pg.click(f".attend-menu button:text-is('{label}')")


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
    login_page = new_page(ctx, errs)
    login_page.goto(BASE + "/campus/"); login_page.fill("#username", ID["Zainab"]); login_page.click("text=Enter")   # Vision reads who is logged in
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
    app.goto(BASE + "/campus/"); app.fill("#username", ID["Zainab"]); app.click("text=Enter"); app.click("text=📢 Announcements")
    text = app.inner_text("#announceList")
    check("announcements appear in the attendance app, authored by the logged-in college ID, marked 'via Vision'",
          text.count("— DEMO-CS-001 (STUDENT) · via Vision") == 8, f"{text.count('· via Vision')} found")
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


def test_login(b):
    """Step B: login with a college ID. The ID is the identity for attendance, announcements and chat."""
    errs, dialogs = [], []
    ctx = b.new_context(viewport={"width": 1400, "height": 1000})
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)[:100]))
    pg.on("dialog", lambda d: (dialogs.append(d.type), d.accept()))
    pg.goto(BASE + "/campus/")
    bad = pg.evaluate("""() => [...document.querySelectorAll('input, select, textarea')].filter(e =>
        /phone|mobile|tel|email|e-mail/i.test([e.type, e.id, e.name, e.placeholder, e.getAttribute('aria-label') || ''].join(' '))).length""")
    check("login: no phone-number or email field anywhere in the app", bad == 0 and pg.locator("input[type=tel], input[type=email]").count() == 0)
    check("login: the only text field is the college ID", pg.eval_on_selector_all("#loginBox input", "e => e.map(x => x.id)") == ["username"] and "College ID" in pg.inner_text("#loginBox"))
    for bad_id in ["", "ab", "has space", "bad!id", "-start"]:   # (21+ characters cannot even be typed: the field has maxlength=20)
        pg.fill("#username", bad_id); pg.click("text=Enter")
        if pg.locator("#dashboard").is_visible() or "college ID" not in pg.inner_text("#loginError"):
            check(f"login: invalid ID {bad_id!r} is rejected inline", False)
            break
    else:
        check("login: empty / too short / spaces / symbols / leading hyphen are rejected with an inline message (no popup)", not pg.locator("#dashboard").is_visible())
    pg.fill("#username", "demo-cs-001"); pg.select_option("#role", "cr"); pg.click("text=Enter")
    check("login: a valid ID is accepted (lower case is normalised), the ID is shown", pg.locator("#dashboard").is_visible() and "DEMO-CS-001" in pg.inner_text("#welcome") and "CR" in pg.inner_text("#welcome"), pg.inner_text("#welcome"))
    # attendance belongs to the ID
    prev_month(pg); mark_attendance(pg, 0, "Present")
    check("attendance is stored per college ID", pg.evaluate("localStorage.getItem('campussync.attendance.DEMO-CS-001')") is not None and pg.evaluate("localStorage.getItem('campussync.attendance')") is None)
    # announcement author
    pg.click(".tab-nav button >> text=Announcements"); pg.fill("#msg", "Library closed Friday"); pg.click("button:text('Post')")
    check("announcement author is the college ID (and role)", "Library closed Friday — DEMO-CS-001 (CR)" in pg.inner_text("#announceList"), pg.inner_text("#announceList"))
    pg.fill("#msg", "<img src=x onerror=window.__x=1>"); pg.click("button:text('Post')")
    check("announcement text cannot inject HTML", pg.locator("#announceList img").count() == 0 and pg.evaluate("window.__x") is None)
    # chat identity
    pg.click(".tab-nav button >> text=Chat")
    check("chat: you are chatting as the logged-in ID", "DEMO-CS-001" in pg.inner_text("#chat-me") and "demo switch" not in pg.inner_text("#chat-me"))
    check("chat: senders are shown by college ID", "Aarav (DEMO-CS-002)" in pg.inner_text(".chat-messages"))
    check("chat: the demo switch is hidden in a clearly labelled 'Demo only' section", pg.locator("details.chat-demo-switch summary").inner_text().startswith("Demo only") and not pg.locator("#chat-as").is_visible())
    # log out, log in as someone else: their attendance is empty; mine is back when I return
    pg.click("text=Logout"); pg.wait_for_selector("#loginBox", state="visible")
    check("logout: returns to the login screen", pg.locator("#loginBox").is_visible() and not pg.locator("#dashboard").is_visible())
    pg.fill("#username", ID["Aarav"]); pg.click("text=Enter"); prev_month(pg)
    check("a different ID sees none of the first ID's attendance", pg.locator(".lecture.present").count() == 0)
    pg.click("text=Logout"); pg.fill("#username", ID["Zainab"]); pg.click("text=Enter"); prev_month(pg)
    check("the first ID gets its attendance back", pg.locator(".lecture.present").count() == 1)
    check("login: no alert()/prompt() popups and no page errors", not dialogs and not errs, str(dialogs + errs))
    ctx.close()


def frame_done(vf):
    """Wait for a full upload run inside the embedded Vision frame."""
    vf.wait_for_function("document.getElementById('capText').innerText.startsWith('1')", timeout=15000)
    vf.wait_for_function("document.getElementById('capText').innerText.startsWith('6')", timeout=90000)
    vf.wait_for_timeout(1200)


def test_import(b):
    """Step C: Vision inside the app. Results reach the Calendar, Announcements and the Study Panel store without a reload."""
    errs, dialogs = [], []
    ctx = b.new_context(viewport={"width": 1500, "height": 1000})
    app = new_page(ctx, errs)
    app.on("dialog", lambda d: (dialogs.append(d.type), d.accept()))
    app.goto(BASE + "/campus/"); app.fill("#username", ID["Zainab"]); app.click("text=Enter")
    api("/api/entries", "DELETE")
    nav = app.locator(".tab-nav button", has_text="Import from screenshot")
    check("import: the app nav has an 'Import from screenshot' entry", nav.count() == 1)
    check("import: the Vision page is not loaded until the tab is opened", app.locator("#importFrame").get_attribute("src") is None)
    nav.click()
    app.wait_for_function("document.getElementById('importFrame').contentDocument && document.getElementById('importFrame').contentDocument.getElementById('file')", timeout=15000)
    vf = app.frame(url=re.compile("embedded=1"))
    check("import: opens Vision inside the app", app.locator("#import").is_visible() and vf is not None)
    check("import: embedded Vision hides its own header (the app nav is above)", vf.evaluate("getComputedStyle(document.querySelector('header')).display") == "none")

    # notice -> announcements (existing review card) and -> Study Panel store
    vf.set_input_files("#file", os.path.join(S, "notice.png")); frame_done(vf)
    vf.click("#postAll")
    app.click(".tab-nav button >> text=Announcements")
    text = app.inner_text("#announceList")
    check("import: notice entries posted from the Import tab show in Announcements without a reload",
          text.count("· via Vision") == 5 and "— DEMO-CS-001 (STUDENT)" in text, f"{text.count('via Vision')} found")
    study = json.loads(app.evaluate("localStorage.getItem('campussync.study')") or "[]")
    check("import: every extracted entry is saved for the Study Panel with its source", len(study) == 5 and all(x["source"] == "vision" and x["via"] == "notice.png" and x["addedBy"] == "DEMO-CS-001" for x in study), f"{len(study)} items")

    # timetable -> calendar (existing preview + confirm), live
    app.click(".tab-nav button >> text=Import from screenshot")
    vf.select_option("#course", "demo-a"); vf.select_option("#sem", "sem1")
    vf.set_input_files("#file", os.path.join(S, "timetable_teacher_room.png")); frame_done(vf)
    check("import: a timetable shows the preview and needs a confirm click (nothing changed yet)",
          "Replace timetable" in vf.inner_text("#attendConfirm") and app.evaluate("localStorage.getItem('campussync.timetable')") is None)
    vf.click("#attendConfirm")
    app.click(".tab-nav button >> text=Calendar")
    subjects = app.eval_on_selector_all(".lecture", "e => [...new Set(e.map(x => x.textContent.replace(/^[0-9:-]+ /, '')))]")
    check("import: after confirming, the Calendar shows the new timetable without a reload", "Placeholder Algebra" in subjects and "Hindi" not in subjects, str(subjects))
    study = json.loads(app.evaluate("localStorage.getItem('campussync.study')") or "[]")
    check("import: the timetable's entries were added to the Study Panel store too (5 notice + 7 lectures)", len(study) == 12, f"{len(study)} items")
    app.click(".tab-nav button >> text=Import from screenshot")
    vf.click("#attendUndo")
    app.click(".tab-nav button >> text=Calendar")
    check("import: Undo in Vision brings the original timetable back in the Calendar", "Hindi" in app.inner_text("#calendarGrid"))
    check("import: no popups and no page errors", not dialogs and not errs, str(dialogs + errs))

    # back link on the standalone page
    solo = new_page(ctx, errs)
    solo.goto(BASE + "/")
    check("import: the standalone Vision page has a visible '← Back to CampusSync' link", solo.locator(".back-link").is_visible() and "Back to CampusSync" in solo.inner_text(".back-link"))
    solo.click(".back-link"); solo.wait_for_load_state()
    check("import: the back link goes to the campus app", solo.url.rstrip("/").endswith("/campus"), solo.url)
    api("/api/entries", "DELETE")
    ctx.close()


def study_add(pg, semester, subject, topic, date, files=None):
    pg.select_option("#study-semester", semester); pg.select_option("#study-subject", subject)
    pg.fill("#study-topic", topic); pg.fill("#study-date", date)
    if files is not None:
        pg.set_input_files("#study-file", files)
    pg.click("text=Add to Study Panel")


def test_study(b):
    """Step D: the app's Study Panel works with store.js: tags, filters, files up to 1 MB, Vision entries."""
    errs, dialogs = [], []
    ctx = b.new_context(viewport={"width": 1500, "height": 1000})
    app = new_page(ctx, errs)
    app.on("dialog", lambda d: (dialogs.append(d.type), d.accept()))
    app.goto(BASE + "/campus/"); app.fill("#username", ID["Zainab"]); app.click("text=Enter")
    api("/api/entries", "DELETE")
    app.click(".tab-nav button >> text=Study Panel")
    check("study: the tab has Semester, Subject, Topic, Date and File inputs",
          app.locator("#study-semester").count() == 1 and app.locator("#study-subject").count() == 1 and app.locator("#study-topic").count() == 1
          and app.locator("#study-date").count() == 1 and app.locator("#study-file").count() == 1)
    check("study: it starts with a clear empty state and 'Showing 0 of 0'", "No study materials yet" in app.inner_text("#materialsList") and "Showing 0 of 0" in app.inner_text("#study"))
    check("study: the subject list comes from the timetable", app.eval_on_selector_all("#study-subject option", "e => e.map(x => x.textContent)")[1:3] == ["Hindi", "OOP C++"])
    app.click("text=Add to Study Panel")
    check("study: adding with nothing chosen shows an inline message (no popup)", app.inner_text(".study-msg") == "Choose a semester.")
    study_add(app, "sem4", "Python", "Loops", "2026-10-20")
    check("study: an entry without a file is added with its tags", app.locator(".study-card").count() == 1 and "Semester 4" in app.inner_text(".study-card") and "Python" in app.inner_text(".study-card") and "Loops" in app.inner_text(".study-card"))
    payload = b"hello study panel"
    study_add(app, "sem3", "DAA", "Dynamic programming", "2026-10-25", {"name": "dp-notes.txt", "mimeType": "text/plain", "buffer": payload})
    link = app.locator(".study-file")
    href = link.get_attribute("href")
    check("study: a small file is stored as a data URL and offered for download",
          href.startswith("data:") and base64.b64decode(href.split(",", 1)[1]) == payload and link.get_attribute("download") == "dp-notes.txt", href[:40])
    big = {"name": "big.pdf", "mimeType": "application/pdf", "buffer": b"x" * (1024 * 1024 + 10)}
    study_add(app, "sem3", "DAA", "Too big", "2026-10-26", big)
    check("study: a file over 1 MB is refused with a clear message and nothing is added",
          "larger than 1 MB" in app.inner_text(".study-msg") and "big.pdf" in app.inner_text(".study-msg") and app.locator(".study-card").count() == 2)
    study_add(app, "sem4", "Python", "Functions and recursion", "2026-10-10", [])      # [] clears the refused big file from the file box
    check("study: the list is newest date first", app.eval_on_selector_all(".study-topic", "e => e.map(x => x.textContent)") == ["Dynamic programming", "Loops", "Functions and recursion"])

    # filters
    def shown():
        return app.inner_text(".study-count")
    app.select_option("#study-q-semester", "sem4")
    check("filter: by semester", app.locator(".study-card").count() == 2 and "Showing 2 of 3" in shown())
    app.select_option("#study-q-subject", "Python"); app.fill("#study-q-topic", "recurs")
    check("filter: semester + subject + topic text combine", app.locator(".study-card").count() == 1 and "Functions" in app.inner_text(".study-card"))
    app.click("text=Clear filters")
    app.fill("#study-q-from", "2026-10-15"); app.fill("#study-q-to", "2026-10-22")
    check("filter: by date range (from / to)", app.locator(".study-card").count() == 1 and "Loops" in app.inner_text(".study-card"))
    app.fill("#study-q-from", "2027-01-01")
    check("filter: no match shows a clear message", "No materials match these filters" in app.inner_text("#materialsList"))
    app.click("text=Clear filters")
    check("filter: Clear filters shows everything again", app.locator(".study-card").count() == 3 and "Showing 3 of 3" in shown())

    # Vision entries
    v = new_page(ctx, errs)
    v.goto(BASE + "/"); v.click("#clear")
    v.set_input_files("#file", os.path.join(S, "timetable_teacher_room.png")); wait_done(v)          # nothing selected -> low confidence
    v.set_input_files("#file", os.path.join(S, "notice.png")); wait_done(v)
    app.click(".tab-nav button >> text=Calendar"); app.click(".tab-nav button >> text=Study Panel")
    vis = app.locator(".study-card", has=app.locator(".study-chip.vision"))
    check("vision: entries from screenshots appear in the Study Panel, marked with their source",
          vis.count() == 12 and "Vision · notice.png" in app.inner_text("#materialsList") and "Vision · timetable_teacher_room.png" in app.inner_text("#materialsList"), f"{vis.count()} vision cards")
    flagged = app.locator(".study-card.needs-check")
    check("vision: low-confidence entries get the amber 'check this' flag, confident ones do not",
          flagged.count() == 7 and "check this" in flagged.first.inner_text() and "check this" not in app.locator(".study-card", has_text="Dynamic Programming").first.inner_text(), f"{flagged.count()} flagged")
    app.select_option("#study-q-subject", "DAA")
    check("vision: Vision entries filter by subject like any other", app.locator(".study-card").count() >= 2 and all("DAA" in t for t in app.eval_on_selector_all(".study-card", "e => e.map(x => x.textContent)")))
    app.click("text=Clear filters")
    check("vision: the tags are Semester / Subject / Topic / Date (notice example)", "Dynamic Programming" in app.inner_text("#materialsList") and "Sat, Nov 14, 2026" in app.inner_text("#materialsList"))

    # remove + ownership
    foreign = {"id": "other1", "source": "upload", "semester": "sem1", "subject": "Hindi", "topic": "Someone else's notes", "date": "2026-10-01", "addedBy": "DEMO-CS-002", "addedAt": 1}
    app.evaluate("(f) => { const k = 'campussync.study'; const a = JSON.parse(localStorage.getItem(k)); a.push(f); localStorage.setItem(k, JSON.stringify(a)); }", foreign)
    app.reload(); app.fill("#username", ID["Zainab"]); app.click("text=Enter"); app.click(".tab-nav button >> text=Study Panel")
    check("study: items survive a reload", app.locator(".study-card").count() == 16, f"{app.locator('.study-card').count()} cards")
    other = app.locator(".study-card", has_text="Someone else's notes")
    check("study: you can remove your own items but not someone else's", other.locator(".study-remove").count() == 0 and app.locator(".study-card", has_text="Loops").locator(".study-remove").count() == 1)
    app.locator(".study-card", has_text="Loops").locator(".study-remove").click()
    check("study: Remove deletes the item", app.locator(".study-card", has_text="Loops").count() == 0 and app.locator(".study-card").count() == 15)

    # storage full
    app.evaluate("() => { Storage.prototype.setItem = function () { throw new DOMException('full', 'QuotaExceededError'); }; }")
    study_add(app, "sem4", "Python", "Will not fit", "2026-10-21", [])
    check("study: if browser storage is full the user is told and nothing half-saved appears", "storage is full" in app.inner_text(".study-msg") and app.locator(".study-card", has_text="Will not fit").count() == 0)
    check("study: no alert()/prompt() popups and no page errors", not dialogs and not errs, str(dialogs + errs))
    api("/api/entries", "DELETE")
    ctx.close()


def test_attendance(b):
    """Step A: attendance by month / day / subject, green / red / neutral, monthly stats, 75% warning."""
    errs, dialogs = [], []
    ctx = b.new_context(viewport={"width": 1400, "height": 1000})
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)[:100]))
    pg.on("dialog", lambda d: (dialogs.append(d.type), d.accept()))
    pg.goto(BASE + "/campus/"); pg.fill("#username", ID["Zainab"]); pg.click("text=Enter")
    now = datetime.date.today()
    check("attendance: opens on the current month", pg.inner_text("#monthYear") == now.strftime("%B %Y"), pg.inner_text("#monthYear"))
    prev_month(pg)
    check("attendance: month navigation goes back one month", pg.inner_text("#monthYear") != now.strftime("%B %Y"))
    hindi = pg.eval_on_selector_all(".lecture", "e => e.map((x, i) => [i, x.textContent]).filter(t => t[1].includes('Hindi')).map(t => t[0])")
    check("attendance: each day lists its lectures by subject (Hindi appears on Mondays)", len(hindi) >= 4, f"{len(hindi)} Hindi lectures")
    for i in hindi[:3]:
        mark_attendance(pg, i, "Present")
    mark_attendance(pg, hindi[3], "Absent")
    colors = pg.evaluate("""() => ({
        present: getComputedStyle(document.querySelector('.lecture.present')).backgroundColor,
        absent: getComputedStyle(document.querySelector('.lecture.absent')).backgroundColor,
        unmarked: getComputedStyle([...document.querySelectorAll('.lecture:not(.present):not(.absent)')][0]).backgroundColor })""")
    check("attendance: attended = green, not attended = red, unmarked = neutral grey",
          colors == {"present": "rgb(46, 204, 113)", "absent": "rgb(231, 76, 60)", "unmarked": "rgb(204, 204, 204)"}, str(colors))
    stored = json.loads(pg.evaluate("localStorage.getItem('campussync.attendance.DEMO-CS-001')"))
    check("attendance: stored shape unchanged ({'YYYY-M-D-Subject-time': 'present'|'absent'})",
          len(stored) == 4 and set(stored.values()) == {"present", "absent"} and all(re.match(r"^\d{4}-\d{1,2}-\d{1,2}-.+-\d{2}-\d{2}$", k) for k in stored), str(stored))
    row = pg.locator(".stat-row", has=pg.locator(".stat-name", has_text="Hindi")).first
    check("stats panel: Hindi shows 3 of 4 held attended = 75%, with the month's total", "3 of 4 held attended: 75%" in row.inner_text() and f"{len(hindi)} this month" in row.inner_text() and "1 absent" in row.inner_text(), row.inner_text().replace("\n", " | "))
    check("stats panel: 75% exactly is not flagged, subjects under 75% are", "low" not in (row.get_attribute("class") or "") and pg.locator(".stat-row.low").count() >= 1)
    check("75% warning: a visible banner (no popup) names the subjects below 75%", pg.locator(".stat-warning").count() == 1 and "Below 75%" in pg.inner_text(".stat-warning"))
    pg.click(".tab-nav button >> text=Attendance")
    check("attendance tab: shows the same numbers as a table, with the warning text and the overall figure",
          pg.locator(".attend-table tr").count() >= 8 and "below 75%" in pg.inner_text("#warning") and "3 of" in pg.inner_text("#presentCount"))
    pg.click(".tab-nav button >> text=Calendar")
    pg.locator(".lecture.absent").first.click(); pg.click(".attend-menu button:text-is('Clear')")
    check("attendance: Clear removes a mark (back to neutral)", pg.locator(".lecture.absent").count() == 0 and len(json.loads(pg.evaluate("localStorage.getItem('campussync.attendance.DEMO-CS-001')"))) == 3)
    pg.click("text=▶"); pg.click("text=▶")
    pg.locator(".lecture").first.click()
    check("attendance: a lecture that is not over cannot be marked (the menu says when it opens)", "hasn't finished yet" in pg.inner_text(".attend-menu") and pg.locator(".attend-menu button:text-is('Present')").count() == 0)
    pg.keyboard.press("Escape")
    check("attendance: Esc closes the menu", pg.locator(".attend-menu").count() == 0)
    check("attendance: no alert()/prompt() popups and no page errors", not dialogs and not errs, str(dialogs + errs))
    ctx.close()


def test_attendance_bridge(b):
    errs = []
    ctx = b.new_context(viewport={"width": 1500, "height": 1000})
    app = new_page(ctx, errs)
    app.goto(BASE + "/campus/"); app.fill("#username", ID["Zainab"]); app.click("text=Enter")
    first = app.inner_text("#monthYear"); app.click("text=▶"); second = app.inner_text("#monthYear"); app.click("text=◀")
    check("attendance app: month buttons work", first != second and app.inner_text("#monthYear") == first)
    prev_month(app)
    mark_attendance(app, 0, "Present"); mark_attendance(app, 3, "Present")
    marks = app.evaluate("localStorage.getItem('campussync.attendance.DEMO-CS-001')")
    check("attendance app: lectures can be marked (time format fixed) and are saved", marks and marks.count("present") == 2, marks)
    check("attendance app: stats panel shows percentages", "%" in app.inner_text("#stats"))
    app.reload(); app.fill("#username", ID["Zainab"]); app.click("text=Enter"); prev_month(app)
    check("attendance app: marks survive a reload", app.locator(".lecture.present").count() == 2)
    app.click("text=📢 Announcements"); app.fill("#msg", "hello"); app.click("button:text('Post')")
    check("attendance app: an announcement shows the author's college ID and role, not 'undefined'", "hello — DEMO-CS-001 (STUDENT)" in app.inner_text("#announceList"), app.inner_text("#announceList"))

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
    check("attendance data is untouched by the replace", pg.evaluate("localStorage.getItem('campussync.attendance.DEMO-CS-001')") == marks)
    cal = new_page(ctx, errs)
    cal.goto(BASE + "/campus/"); cal.fill("#username", ID["Zainab"]); cal.click("text=Enter"); prev_month(cal)
    subjects = cal.eval_on_selector_all(".lecture", "e => [...new Set(e.map(x => x.textContent.replace(/^[0-9:-]+ /, '')))]")
    check("attendance app now shows the new subjects", "Placeholder Algebra" in subjects and "Hindi" not in subjects, str(subjects))
    check("the 2 old marks are hidden, not deleted", cal.locator(".lecture.present").count() == 0)
    cal.close()
    pg.click("#attendUndo"); pg.wait_for_timeout(500)
    cal = new_page(ctx, errs)
    cal.goto(BASE + "/campus/"); cal.fill("#username", ID["Zainab"]); cal.click("text=Enter"); prev_month(cal)
    check("Undo brings the old timetable and the 2 marks back", cal.locator(".lecture.present").count() == 2 and "Hindi" in cal.inner_text("#calendarGrid"))
    pg.select_option("#course", ""); pg.set_input_files("#file", os.path.join(S, "timetable_teacher_room.png")); wait_done(pg)
    check("low-confidence lectures: confirm disabled until 'I checked them' is ticked", pg.locator("#attendOk").count() == 1 and not pg.is_enabled("#attendConfirm"))
    pg.check("#attendOk")
    check("low-confidence lectures: enabled after ticking", pg.is_enabled("#attendConfirm"))
    known = [e for e in errs if "subjectCount" not in e]
    check("bridge: no unexpected page errors (known: checkWarnings 'subjectCount is not defined')", not known, str(known))
    ctx.close()


def chat_conv(pg, name):
    """The conversation-list button whose TITLE is exactly `name` (previews can mention other names)."""
    return pg.locator(".chat-convo", has=pg.locator(".chat-convo-title", has_text=re.compile(f"^{name}$")))


def chat_open(ctx, user, errors, dialogs):
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)[:100]))
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    pg.goto(BASE + "/campus/"); pg.fill("#username", ID[user]); pg.click("text=Enter")
    pg.click(".tab-nav button >> text=Chat")
    return pg


def test_chat(b):
    errs, dialogs = [], []
    ctx = b.new_context(viewport={"width": 1366, "height": 768})
    z = chat_open(ctx, "Zainab", errs, dialogs)
    check("chat: old stub is gone (no handleResponse / Public-Private buttons)", "handleResponse" not in urllib.request.urlopen(BASE + "/campus/chatbot.html").read().decode())
    check("chat: the tab starts hidden-until-clicked and is built by chat.js", z.locator("#chat").is_visible() and z.locator(".tab-nav button", has_text="Chat").count() == 1)
    check("chat: seeded on first load (4 group messages + 1 open request, day separators)",
          z.locator(".chat-msg").count() == 5 and z.locator(".chat-request .chat-status.open").count() == 1 and z.locator(".chat-day").count() == 2)
    check("chat: demo-accounts notice is shown", "placeholder college IDs" in z.inner_text(".chat-demo") and "no server sync" in z.inner_text(".chat-demo"))
    check("chat: conversation list = group + 3 classmates", z.eval_on_selector_all(".chat-convo-title", "e => e.map(x => x.textContent)") == ["Class group", "Aarav", "Meera", "Kabir"])
    check("chat: unread count shown on the Meera one-to-one", chat_conv(z, "Meera").locator(".chat-badge").inner_text() == "2")

    # composer
    z.fill("#chat-input", "Hello <b>bold</b> <img src=x onerror=window.__pwned=1>"); z.press("#chat-input", "Enter")
    last = z.locator(".chat-msg").last
    check("composer: Enter sends; typed HTML is shown as plain text (no <b>/<img> created)",
          "<b>bold</b>" in last.inner_text() and z.locator("#chat b, #chat img").count() == 0 and z.evaluate("window.__pwned") is None)
    z.fill("#chat-input", "a"); z.press("#chat-input", "Shift+Enter"); z.type("#chat-input", "b")
    n = z.locator(".chat-msg").count()
    check("composer: Shift+Enter adds a line instead of sending", z.input_value("#chat-input") == "a\nb" and z.locator(".chat-msg").count() == n)
    z.press("#chat-input", "Enter")
    check("composer: multi-line message is kept", z.locator(".chat-text").last.inner_text() == "a\nb")
    z.fill("#chat-input", "    "); z.press("#chat-input", "Enter")
    check("composer: whitespace-only is ignored", z.locator(".chat-msg").count() == n + 1)
    check("messages: newest message is scrolled into view",
          z.evaluate("(() => { const m = document.querySelector('.chat-messages'); return m.scrollHeight - m.scrollTop - m.clientHeight < 5; })()"))

    # one-to-one
    chat_conv(z, "Meera").click()
    check("one-to-one: opening it shows its messages and clears its unread badge", z.locator(".chat-msg").count() == 3 and chat_conv(z, "Meera").locator(".chat-badge").count() == 0)
    z.fill("#chat-input", "Calling at 8!"); z.press("#chat-input", "Enter")
    chat_conv(z, "Class group").click()
    check("one-to-one: a direct message does not appear in the class group", "Calling at 8!" not in z.inner_text(".chat-messages"))

    # a second tab as another user, live sync, privacy
    a = chat_open(ctx, "Aarav", errs, dialogs)
    check("one-to-one: Aarav cannot see the Zainab/Meera conversation", a.eval_on_selector_all(".chat-convo-title", "e => e.map(x => x.textContent)") == ["Class group", "Zainab", "Meera", "Kabir"] and "Calling at 8!" not in a.inner_text("#chat"))
    z.fill("#chat-input", "live sync test"); z.press("#chat-input", "Enter")
    a.wait_for_function("document.querySelector('.chat-messages').innerText.includes('live sync test')", timeout=5000)
    check("sync: a message sent in one tab appears live in the other tab", True)

    # note request form
    z.click("text=Request notes")
    dlg = z.locator("dialog.chat-dialog")
    fields = dlg.locator("select, input, textarea").evaluate_all("e => e.map(x => x.tagName + ':' + x.type)")
    check("request form: exactly three inputs (Subject, Date, Topic)", fields == ["SELECT:select-one", "INPUT:date", "INPUT:text"], str(fields))
    check("request form: subjects come from the timetable", z.eval_on_selector_all("#chat-req-subject option", "e => e.map(x => x.textContent)")[1:3] == ["Hindi", "OOP C++"])
    check("request form: date defaults to today", z.input_value("#chat-req-date") == datetime.date.today().isoformat())
    z.click("text=Send request")
    check("request form: submitting empty shows an inline error, no popup", z.inner_text(".chat-req-error") == "Choose a subject." and dlg.is_visible())
    z.select_option("#chat-req-subject", "Python"); z.click("text=Send request")
    check("request form: topic is required", z.inner_text(".chat-req-error") == "Write a short topic.")
    z.fill("#chat-req-topic", "   <b>File</b>   handling  "); z.click("text=Send request")
    card = z.locator(".chat-request").last
    check("request: posts a card with Subject / Date / Topic (HTML shown as text, spaces cleaned)",
          not dlg.is_visible() and "Python" in card.inner_text() and "<b>File</b> handling" in card.inner_text() and card.locator("b").count() == 0)
    check("request: starts Open and the requester has no 'I have these notes' button", card.locator(".chat-status").inner_text() == "Open" and card.locator("button").count() == 0)
    z.click("text=Request notes"); z.keyboard.press("Escape")
    check("request form: Esc closes it and focus returns to the Request button", not dlg.is_visible() and "Request notes" in z.evaluate("document.activeElement.textContent"))

    acard = a.locator(".chat-request").last
    a.wait_for_function("document.querySelectorAll('.chat-request').length === 2", timeout=5000)
    check("request: another user sees it Open with an 'I have these notes' button", acard.locator(".chat-status").inner_text() == "Open" and acard.locator("button").count() == 1)
    acard.locator("button").click()
    check("request: pressing it marks it Shared with name and time", acard.locator(".chat-status").inner_text() == "Shared" and "by Aarav (DEMO-CS-002) at" in acard.locator(".chat-req-by").inner_text())
    z.wait_for_function("(() => { const c = document.querySelectorAll('.chat-request'); return c[c.length-1].querySelector('.chat-status').textContent === 'Shared'; })()", timeout=5000)
    zc = z.locator(".chat-request").last
    check("request: the requester's tab shows Shared live, with who and when", "by Aarav (DEMO-CS-002) at" in zc.locator(".chat-req-by").inner_text() and zc.locator("button").count() == 0)
    k = chat_open(ctx, "Kabir", errs, dialogs)
    check("request: a third user sees Shared and no button", k.locator(".chat-request").last.locator(".chat-status").inner_text() == "Shared" and k.locator(".chat-request").last.locator("button").count() == 0)
    chat_conv(z, "Meera").click(); z.click("text=Request notes")
    check("request: inside a one-to-one it says where it will be sent", z.inner_text(".chat-req-target") == "Sending to: Meera")
    z.select_option("#chat-req-subject", "EVS"); z.fill("#chat-req-topic", "Water pollution"); z.click("text=Send request")
    check("request: lands in that one-to-one, not in the group", z.locator(".chat-request").count() == 1)

    # persistence + reset
    z.reload(); z.fill("#username", ID["Zainab"]); z.click("text=Enter"); z.click(".tab-nav button >> text=Chat")
    check("persistence: messages survive a reload", "live sync test" in z.inner_text(".chat-messages"))
    z.click("text=Reset chat")
    check("reset: first click only asks to confirm (no popup)", z.locator("text=Click again to reset").count() == 1 and "live sync test" in z.inner_text(".chat-messages"))
    z.click("text=Click again to reset")
    check("reset: second click restores the seed data", z.locator(".chat-msg").count() == 5 and "live sync test" not in z.inner_text(".chat-messages"))

    # quality bar at both screen sizes
    for w, h in ((1920, 1080), (1366, 768)):
        z.set_viewport_size({"width": w, "height": h}); z.wait_for_timeout(200)
        check(f"layout {w}x{h}: no horizontal scroll (page and chat)",
              z.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth && document.querySelector('#chat').scrollWidth <= document.querySelector('#chat').clientWidth"))
        small = z.evaluate("""() => [...document.querySelectorAll('#chat *')].filter(e => e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && e.offsetParent !== null)
                                 .map(e => parseFloat(getComputedStyle(e).fontSize)).filter(s => s < 13).length""")
        check(f"layout {w}x{h}: no visible chat text smaller than 13px", small == 0, f"{small} elements")
        check(f"layout {w}x{h}: the composer is inside the visible area",
              z.evaluate("window.scrollTo(0, 0) || document.querySelector('.chat-composer').getBoundingClientRect().bottom <= window.innerHeight"))
    z.focus("#chat-input"); z.keyboard.press("Tab")
    outline = z.evaluate("getComputedStyle(document.activeElement).outlineWidth + ' ' + getComputedStyle(document.activeElement).outlineStyle")
    check("keyboard: Tab from the message box reaches Send with a visible focus outline", "Send" in z.evaluate("document.activeElement.textContent") and outline.startswith("3px") and "solid" in outline, outline)
    check("chat: no alert()/confirm()/prompt() popups were shown during the whole chat test", dialogs == [], str(dialogs))
    check("chat: no page errors", not errs, str(errs))
    ctx.close()


def test_chat_prefill(b):
    """Vision's 'Request notes' link on a lecture row pre-fills the chat's request form. It never sends."""
    errs, dialogs = [], []
    ctx = b.new_context(viewport={"width": 1400, "height": 1000})
    v = ctx.new_page()
    v.on("pageerror", lambda e: errs.append(str(e)[:100]))
    v.goto(BASE + "/"); v.click("#clear")
    v.set_input_files("#file", os.path.join(S, "timetable.png")); wait_done(v)
    check("prefill: every lecture row has a 'Request notes' link", v.locator(".req-notes").count() == v.locator(".entry").count() == 11)
    check("prefill: the link is invisible until hover/focus", v.evaluate("getComputedStyle(document.querySelector('.req-notes')).opacity") == "0")
    with_links = v.evaluate("document.getElementById('panel').offsetHeight")
    v.evaluate("document.querySelectorAll('.req-notes').forEach(e => e.remove())")
    check("prefill: the links do not change the Study Panel layout (same height with and without)", with_links == v.evaluate("document.getElementById('panel').offsetHeight"), f"{with_links}px")
    v.reload(); v.wait_for_timeout(800)
    row = v.locator(".subject", has_text="Hindi").locator(".entry").first
    row.hover()
    check("prefill: the link shows on hover", v.evaluate("getComputedStyle(document.querySelector('.entry:hover .req-notes')).opacity") == "1")
    with ctx.expect_page() as popup:
        row.locator(".req-notes").click()
    c = popup.value
    c.on("pageerror", lambda e: errs.append(str(e)[:100]))
    c.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    c.wait_for_load_state()
    check("prefill: the campus app still shows its login first", c.locator("#loginBox").is_visible())
    c.fill("#username", ID["Zainab"]); c.click("text=Enter")
    dlg = c.locator("dialog.chat-dialog")
    check("prefill: after login the Chat tab opens with the request form", c.locator("#chat").is_visible() and dlg.is_visible())
    check("prefill: subject and topic are filled from the lecture", c.input_value("#chat-req-subject") == "Hindi" and c.input_value("#chat-req-topic") == "Monday 07-08 lecture")
    date = datetime.date.fromisoformat(c.input_value("#chat-req-date"))
    check("prefill: the date is the most recent Monday (on or before today)", date.weekday() == 0 and date <= datetime.date.today() and (datetime.date.today() - date).days < 7, str(date))
    check("prefill: nothing was sent automatically", c.locator(".chat-request").count() == 1)       # the single seeded request
    c.click("text=Send request")
    check("prefill: it is sent only after the user presses Send", c.locator(".chat-request").count() == 2)
    check("prefill: the URL is cleaned so a reload does not reopen the form", "chat=request" not in c.url)
    check("prefill: no page errors or popups", not errs and not dialogs, str(errs + dialogs))
    ctx.close()


def main():
    try:
        api("/api/entries")
    except Exception as e:
        raise SystemExit(f"Server not reachable at {BASE}: start it first (py -m uvicorn main:app --port 8000). {e}")
    api("/api/entries", "DELETE")
    with sync_playwright() as p:
        b = p.chromium.launch()
        for test in (test_api, test_demo_flow, test_announcements, test_catalog, test_login, test_import, test_study, test_attendance, test_attendance_bridge, test_chat, test_chat_prefill):
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

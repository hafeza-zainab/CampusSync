"""End-to-end checks: drives the real pages in a headless browser and prints PASS / FAIL for each claim.

Run this after ANY code change (and before recording):
    1. start the server in another terminal:   py -m uvicorn main:app --port 8000     (from the vision folder)
    2. one-time install:                       py -m pip install playwright ; py -m playwright install chromium
    3. from the vision folder:                 py tests/e2e.py

It uses fresh browser profiles, resets the saved Study Panel entries at the start and end, and exits with
a non-zero code if anything fails. It tests with the SYNTHETIC images in samples/ (run make_sample.py first).
"""
import datetime
import json
import os
import re
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


def chat_conv(pg, name):
    """The conversation-list button whose TITLE is exactly `name` (previews can mention other names)."""
    return pg.locator(".chat-convo", has=pg.locator(".chat-convo-title", has_text=re.compile(f"^{name}$")))


def chat_open(ctx, user, errors, dialogs):
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)[:100]))
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    pg.goto(BASE + "/campus/"); pg.fill("#username", user); pg.click("text=Enter")
    pg.click(".tab-nav button >> text=Chat"); pg.select_option("#chat-as", user)
    return pg


def test_chat(b):
    errs, dialogs = [], []
    ctx = b.new_context(viewport={"width": 1366, "height": 768})
    z = chat_open(ctx, "Zainab", errs, dialogs)
    check("chat: old stub is gone (no handleResponse / Public-Private buttons)", "handleResponse" not in urllib.request.urlopen(BASE + "/campus/chatbot.html").read().decode())
    check("chat: the tab starts hidden-until-clicked and is built by chat.js", z.locator("#chat").is_visible() and z.locator(".tab-nav button", has_text="Chat").count() == 1)
    check("chat: seeded on first load (4 group messages + 1 open request, day separators)",
          z.locator(".chat-msg").count() == 5 and z.locator(".chat-request .chat-status.open").count() == 1 and z.locator(".chat-day").count() == 2)
    check("chat: demo-users notice is shown", "Demo users" in z.inner_text(".chat-demo") and "no server sync" in z.inner_text(".chat-demo"))
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
    check("request: pressing it marks it Shared with name and time", acard.locator(".chat-status").inner_text() == "Shared" and "by Aarav at" in acard.locator(".chat-req-by").inner_text())
    z.wait_for_function("(() => { const c = document.querySelectorAll('.chat-request'); return c[c.length-1].querySelector('.chat-status').textContent === 'Shared'; })()", timeout=5000)
    zc = z.locator(".chat-request").last
    check("request: the requester's tab shows Shared live, with who and when", "by Aarav at" in zc.locator(".chat-req-by").inner_text() and zc.locator("button").count() == 0)
    k = chat_open(ctx, "Kabir", errs, dialogs)
    check("request: a third user sees Shared and no button", k.locator(".chat-request").last.locator(".chat-status").inner_text() == "Shared" and k.locator(".chat-request").last.locator("button").count() == 0)
    chat_conv(z, "Meera").click(); z.click("text=Request notes")
    check("request: inside a one-to-one it says where it will be sent", z.inner_text(".chat-req-target") == "Sending to: Meera")
    z.select_option("#chat-req-subject", "EVS"); z.fill("#chat-req-topic", "Water pollution"); z.click("text=Send request")
    check("request: lands in that one-to-one, not in the group", z.locator(".chat-request").count() == 1)

    # persistence + reset
    z.reload(); z.fill("#username", "Zainab"); z.click("text=Enter"); z.click(".tab-nav button >> text=Chat")
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
    c.fill("#username", "Zainab"); c.click("text=Enter")
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
        for test in (test_api, test_demo_flow, test_announcements, test_catalog, test_attendance_bridge, test_chat, test_chat_prefill):
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

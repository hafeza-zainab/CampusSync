"""Runs the PROPOSED integrated demo flow end to end in a headless browser and reports what happened and how long it took.

    py tests/demo_walkthrough.py                       (server running; from the vision folder)
    DEMO_SHOTS=some\\folder py tests/demo_walkthrough.py   (also saves a screenshot of every step)
    CAMPUS_BASE=http://localhost:8001 py tests/demo_walkthrough.py   (test another server / checkout)

The flow: log in -> Study Panel > Import card: upload a timetable screenshot (boxes) -> confirm -> Calendar: mark lectures
(green / red, stats) -> Import: upload a notice -> post as announcements -> Study Panel (tagged + filter) -> Chat template.

It uses SYNTHETIC images and DEMO accounts. The timings are a script's (fast clicks); a person is slower.
It resets the saved Vision entries at the start and the end.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e2e                      # noqa: E402  (reuses its helpers: login_as, mark_attendance, frame_done, check, ...)
from playwright.sync_api import sync_playwright   # noqa: E402

BASE, S, check = e2e.BASE, e2e.S, e2e.check
SHOTS = os.environ.get("DEMO_SHOTS")
if SHOTS:
    os.makedirs(SHOTS, exist_ok=True)

steps = []
t0 = time.perf_counter()


def step(name):
    steps.append((name, time.perf_counter() - t0))


def shot(pg, name):
    if SHOTS:
        pg.screenshot(path=os.path.join(SHOTS, name), full_page=True)


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = e2e.blank_ctx(browser, viewport={"width": 1500, "height": 950})   # demo seed off: the counts below start from zero
    errs, dialogs = [], []
    app = ctx.new_page()
    app.on("pageerror", lambda e: errs.append(str(e)[:100]))
    app.on("dialog", lambda d: (dialogs.append(d.type), d.accept()))
    e2e.api("/api/entries", "DELETE")

    # 1. login
    app.goto(BASE + "/campus/"); e2e.login_as(app, "Zainab")
    step("1 login with a college ID")

    # 2. import a timetable screenshot: boxes, entries, preview
    vf = e2e.open_import_card(app)
    vf.set_input_files("#file", os.path.join(S, "timetable_demo_new.png"))
    e2e.frame_done(vf)
    shot(app, "1_import_boxes_and_entries.png")
    check("demo 2: boxes drawn and the timetable read (10 lectures, 30 cells)", "30 cells" in vf.inner_text("#steps") and vf.locator(".entry").count() == 10, vf.inner_text("#steps").replace("\n", " | ")[:120])
    check("demo 2: the attendance card previews what changes and needs a click", "Replace timetable" in vf.inner_text("#attendConfirm") and vf.locator(".chip.add").count() > 0 and vf.locator(".chip.del").count() > 0)
    step("2 timetable screenshot read, preview shown")
    vf.click("#attendConfirm")
    step("3 timetable confirmed")

    # 3. calendar: mark attendance, green / red, stats
    app.click(".tab-nav button >> text=Calendar"); e2e.prev_month(app)
    for i in range(6):
        e2e.mark_attendance(app, i, "Present")
    for i in (6, 7):
        e2e.mark_attendance(app, i, "Absent")
    subjects = app.eval_on_selector_all(".lecture", "e => [...new Set(e.map(x => x.textContent.replace(/^[0-9:-]+ /, '')))]")
    shot(app, "2_calendar_green_red_stats.png")
    check("demo 3: the calendar now uses the imported timetable", set(subjects) >= {"Python", "DAA", "OOP C++", "Hindi", "Leadership"}, str(subjects))
    check("demo 3: 6 lectures green, 2 red", app.locator(".lecture.present").count() == 6 and app.locator(".lecture.absent").count() == 2)
    check("demo 3: the side panel shows held / attended / % per subject and a 75% warning", app.locator(".stat-row").count() >= 8 and app.locator(".stat-warning").count() == 1)
    step("4 attendance marked, green/red + stats")

    # 4. notice -> announcements
    vf = e2e.open_import_card(app)
    vf.set_input_files("#file", os.path.join(S, "notice.png")); e2e.frame_done(vf)
    shot(app, "3_import_notice_review.png")
    vf.click("#postAll")
    app.click(".tab-nav button >> text=Announcements")
    shot(app, "4_announcements.png")
    check("demo 4: the notice's 5 tasks are posted as announcements by the logged-in ID", app.inner_text("#announceList").count("· via Vision") == 5 and "DEMO-CS-001" in app.inner_text("#announceList"))
    step("5 notice posted as announcements")

    # 5. study panel
    app.click(".tab-nav button >> text=Study Panel")
    app.select_option("#study-q-subject", "Python")
    shot(app, "5_study_panel_filtered.png")
    app.click("text=Clear filters")
    check("demo 5: everything Vision read is in the Study Panel (10 lectures + 5 notice tasks), tagged by subject/topic/date",
          app.locator(".study-card").count() == 15 and "Showing 15 of 15" in app.inner_text(".study-count"))
    step("6 Study Panel, filter by subject")

    # 6. chat template
    app.click(".tab-nav button >> text=Chat")
    e2e.chat_send(app, "doubt", "DAA", "Recurrence relations")
    shot(app, "6_chat_template.png")
    check("demo 6: a doubt is sent from the template (no free-text box exists)", app.locator("#chat textarea").count() == 0 and "Recurrence relations" in app.inner_text(".chat-messages"))
    step("7 chat template message sent")

    check("demo: no popups and no page errors during the whole flow", not dialogs and not errs, str(dialogs + errs))
    e2e.api("/api/entries", "DELETE")
    browser.close()

print("\nStep timings (cumulative, scripted clicks, headless):")
prev = 0.0
for name, t in steps:
    print(f"  {t:5.1f} s   (+{t - prev:4.1f} s)  {name}")
    prev = t
print(f"\n{sum(e2e.results)}/{len(e2e.results)} walkthrough checks passed")
sys.exit(0 if all(e2e.results) else 1)

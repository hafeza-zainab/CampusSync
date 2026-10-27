"""Smoke test of the CURRENT CampusSync app: password login with roles, Import card inside the Study Panel,
template-only chat, semester-aware calendar.

    py tests/smoke_app.py        (server running; from the vision folder; needs playwright + chromium)

It uses synthetic images and the demo accounts, with the demo seed ON. tests/e2e.py is the longer suite (most of it
runs with the seed off).
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "samples") + os.sep
B = os.environ.get("CAMPUS_BASE", "http://localhost:8000")
res = []


def ck(name, ok, detail=""):
    res.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def login(pg, who, pw):
    pg.fill("#username", who)
    pg.fill("#password", pw)
    pg.click("button:text-is('Enter')")


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1500, "height": 1000})
    errs, dialogs = [], []
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)[:120]))
    pg.on("dialog", lambda d: (dialogs.append(d.message[:50]), d.accept()))
    pg.goto(B + "/campus/")
    ck("login screen: ID + password, no phone/email field", pg.locator("#loginBox input[type=tel], #loginBox input[type=email]").count() == 0 and pg.locator("#password").count() == 1)
    pg.fill("#username", "DEMO-CS-001"); pg.fill("#password", "wrong"); pg.click("button:text-is('Enter')")
    ck("wrong password is rejected inline", "Wrong" in pg.inner_text("#loginError") and not pg.locator("#dashboard").is_visible(), pg.inner_text("#loginError"))
    login(pg, "DEMO-CS-001", "cr-demo")
    ck("correct login shows the ID and the CR role", "DEMO-CS-001" in pg.inner_text("#welcome") and "CR" in pg.inner_text("#welcome"), pg.inner_text("#welcome"))
    tabs = pg.eval_on_selector_all(".tab-nav button", "e => e.map(x => x.textContent.trim())")
    ck("nav tabs: Calendar, Attendance, Study Panel, Announcements, Chat", tabs == ["📅 Calendar", "📝 Attendance", "📚 Study Panel", "📢 Announcements", "💬 Chat"], str(tabs))
    pg.click(".tab-nav button >> text=Announcements")
    ck("the CR sees the announcement box", pg.locator(".announce-input").is_visible())
    pg.click(".tab-nav button >> text=Calendar")
    ck("seeded demo data: the stats panel has subjects", pg.locator(".stat-row").count() >= 1, str(pg.locator(".stat-row").count()))

    pg.click(".tab-nav button >> text=Study Panel")
    card = pg.locator("details.import-card")
    ck("Import from screenshot is a card inside the Study Panel", card.count() == 1)
    card.locator("summary").click(); pg.wait_for_timeout(1500)
    vf = pg.frame(url=re.compile("embedded"))
    ck("the embedded Vision page loads", vf is not None)
    vf.set_input_files("#file", S + "notice.png")
    vf.wait_for_function("document.getElementById('capText').innerText.startsWith('6')", timeout=60000); vf.wait_for_timeout(1000)
    vf.click("#postAll")
    pg.click(".tab-nav button >> text=Announcements")
    t = pg.inner_text("#announceList")
    ck("notice -> 5 announcements by the logged-in ID, marked via Vision", t.count("via Vision") == 5 and "DEMO-CS-001" in t, f"{t.count('via Vision')} via Vision")
    pg.click(".tab-nav button >> text=Study Panel")
    ck("Vision entries appear in the Study Panel with their source", pg.locator(".study-card", has=pg.locator(".study-chip.vision")).count() >= 5)
    vf = pg.frame(url=re.compile("embedded"))
    vf.set_input_files("#file", S + "timetable_demo_new.png")
    vf.wait_for_function("document.getElementById('capText').innerText.startsWith('6')", timeout=60000); vf.wait_for_timeout(1000)
    txt = vf.inner_text("#attendConfirm")
    ck("timetable: a preview and a confirm button (nothing changes before the click)", "Replace" in txt, txt)
    vf.click("#attendConfirm")
    pg.click(".tab-nav button >> text=Calendar"); pg.wait_for_timeout(500)
    subjects = pg.eval_on_selector_all(".lecture", "e => [...new Set(e.map(x => x.textContent.replace(/^[0-9:-]+ /, '')))]")
    ck("after confirming, the calendar shows the imported timetable", "Python" in subjects and "DAA" in subjects, str(subjects))

    pg.click("text=Logout"); pg.wait_for_selector("#loginBox", state="visible"); pg.wait_for_timeout(500)
    login(pg, "DEMO-CS-003", "student-demo")
    pg.click(".tab-nav button >> text=Announcements")
    ck("a student cannot post announcements (the box is hidden and a note explains)", not pg.locator(".announce-input").is_visible() and pg.locator("#announceNote").is_visible())
    pg.click(".tab-nav button >> text=Chat")
    ck("chat has no free-text box and shows the logged-in ID", pg.locator("#chat textarea").count() == 0 and "DEMO-CS-003" in pg.inner_text("#chat-me"))
    ck("no page errors and no popups", not errs and not dialogs, str(errs + dialogs))
    b.close()

    b = p.chromium.launch()
    q = b.new_page(viewport={"width": 1400, "height": 900})
    q.on("dialog", lambda d: d.accept())
    q.goto(B + "/campus/")
    login(q, "DEMO-CS-001", "cr-demo")
    rows = []
    for _ in range(8):
        rows.append((q.inner_text("#monthYear"), q.locator(".lecture").count(),
                     q.eval_on_selector_all(".lecture", "e => e.filter(x => getComputedStyle(x).backgroundColor === 'rgb(204, 204, 204)').length"),
                     q.locator(".stat-row").count()))
        q.click(".calendar-header button >> nth=1")
    ck("semester calendar: Semester 5 months have lectures and stats; Semester 6 (not started) is greyed with no stats; months after the last semester are empty",
       rows[0][1] > 0 and rows[0][3] > 0 and rows[2][1] > 0 and rows[2][2] == rows[2][1] and rows[2][3] == 0 and rows[7][1] == 0, str(rows))
    b.close()

print(f"\n{sum(res)}/{len(res)} checks passed")
sys.exit(0 if all(res) else 1)

"""Playwright tests for demo-tour.js, using example.html.

    py demo-tour/test_demo_tour.py          (needs: pip install playwright; playwright install chromium)

It starts its own throwaway static server on port 8766. Nothing here touches CampusSync or its server.
Pace is set to 0.1 (pauses ten times shorter) so the whole file runs in a few seconds.
"""
import json
import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8766
URL = f"http://localhost:{PORT}/example.html"
failed = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failed.append(name)


def todos(pg):
    return json.loads(pg.evaluate("localStorage.getItem('example.todos') || '[]'"))


def fresh(browser, query="?pace=0.1", visitor=None):
    """A new browser context, so each test starts with its own localStorage. `visitor` = the user's own saved tasks."""
    ctx = browser.new_context()
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL.replace("example.html", "example.html") + query)
    if visitor is not None:
        pg.evaluate("v => localStorage.setItem('example.todos', JSON.stringify(v))", visitor)
        pg.reload()
    pg.errs = errs
    return pg


def watch_captions(pg):
    """Record every caption the bar shows (a MutationObserver, so a fast tour cannot be missed)."""
    pg.evaluate("""() => { window.__caps = [];
      new MutationObserver(() => { const t = document.querySelector('#demoTourBar .dt-text');
        if (t && t.textContent && window.__caps[window.__caps.length - 1] !== t.textContent) window.__caps.push(t.textContent); })
        .observe(document.body, { childList: true, subtree: true, characterData: true }); }""")


srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--directory", HERE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        visitor = [{"text": "My own task", "done": True}, {"text": "Another of mine", "done": False}]

        # 1. a full run
        pg = fresh(browser, visitor=visitor)
        watch_captions(pg)
        pg.click("[data-tour=start]")
        pg.wait_for_selector("#demoTourBar")
        check("bar appears and Start is disabled while running", pg.is_disabled("[data-tour=start]"))
        seen_mid = []
        pg.wait_for_function("document.getElementById('list').textContent.includes('Water the plants')", timeout=10000)
        seen_mid = [t["text"] for t in todos(pg)]
        check("the tour really typed and added a task through the page's own UI (visible mid-run)", "Water the plants (demo)" in seen_mid, str(seen_mid))
        pg.wait_for_selector("#demoTourBar", state="detached", timeout=15000)
        caps = pg.evaluate("window.__caps")
        check("all 7 captions were shown, in order", len(caps) == 7 and caps[0].startswith("A to-do page") and caps[-1].startswith("That is the demo"), str(caps))
        check("seed ran once, then reset once, in that order", pg.evaluate("window.__log") == ["seed", "reset"], str(pg.evaluate("window.__log")))
        check("the visitor's own data is exactly as before (even though the tour pressed 'Clear finished')", todos(pg) == visitor, str(todos(pg)))
        check("Start is enabled again and the focus outline is gone", pg.is_enabled("[data-tour=start]") and pg.locator(".demo-tour-focus").count() == 0)
        check("no page errors", pg.errs == [], str(pg.errs))

        # 2. run it a second time on the same page (re-runnable)
        pg.click("[data-tour=start]")
        pg.wait_for_selector("#demoTourBar")
        pg.wait_for_selector("#demoTourBar", state="detached", timeout=15000)
        check("a second run works and leaves the data unchanged", todos(pg) == visitor and pg.evaluate("window.__log") == ["seed", "reset", "seed", "reset"])

        # 3. Stop button, at normal speed (pace 1) so the tour is still in a long pause when we click
        pg = fresh(browser, query="", visitor=visitor)
        pg.click("[data-tour=start]")
        pg.wait_for_function("document.getElementById('list').textContent.includes('Sample task')")   # seed has run
        t0 = time.time()
        pg.click("#demoTourStop")
        pg.wait_for_selector("#demoTourBar", state="detached", timeout=5000)
        check("Stop ends the tour within about a second", time.time() - t0 < 2, f"{time.time() - t0:.2f}s")
        check("Stop still runs reset: the visitor's data is back", todos(pg) == visitor and pg.evaluate("window.__log") == ["seed", "reset"], str(todos(pg)))

        # 4. a step whose element does not exist (a renamed data-tour attribute)
        pg = fresh(browser, visitor=visitor)
        pg.evaluate("document.querySelector('[data-tour=add]').removeAttribute('data-tour')")
        pg.click("[data-tour=start]")
        pg.wait_for_function("document.querySelector('#demoTourBar .dt-text') && document.querySelector('#demoTourBar .dt-text').textContent.startsWith('Demo stopped')", timeout=10000)
        msg = pg.inner_text("#demoTourBar .dt-text")
        check("a missing element is reported in the bar, naming the selector", 'no element for "add"' in msg, msg)
        pg.wait_for_selector("#demoTourBar", state="detached", timeout=10000)
        check("after the error reset still ran and the page is usable again", todos(pg) == visitor and pg.is_enabled("[data-tour=start]"))

        # 5. a second start() while running is ignored
        pg = fresh(browser, query="", visitor=visitor)
        pg.click("[data-tour=start]")
        pg.wait_for_selector("#demoTourBar")
        second = pg.evaluate("tour.start()")
        check("start() while running returns false and does not stack a second bar", second is False and pg.locator("#demoTourBar").count() == 1)
        pg.click("#demoTourStop")
        pg.wait_for_selector("#demoTourBar", state="detached", timeout=5000)

        browser.close()
finally:
    srv.terminate()

print()
print("FAILED: " + ", ".join(failed) if failed else "All checks passed.")
sys.exit(1 if failed else 0)

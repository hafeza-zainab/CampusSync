"""Takes the chat screenshots (group chat, one-to-one, request form, request marked Shared from a second tab)
at 1920x1080 and 1366x768 and saves them in ../chat_screenshots/.

    py tests/chat_screenshots.py        (server running; from the vision folder)

The images show DEMO users and seeded demo messages, not real conversations.
"""
import os
import re

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "chat_screenshots")
os.makedirs(OUT, exist_ok=True)


def conv(pg, name):
    return pg.locator(".chat-convo", has=pg.locator(".chat-convo-title", has_text=re.compile(f"^{name}$")))


def open_chat(ctx, user):
    pg = ctx.new_page()
    pg.goto(BASE + "/campus/"); pg.fill("#username", user); pg.click("text=Enter")
    pg.click(".tab-nav button >> text=Chat"); pg.select_option("#chat-as", user)
    return pg


with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in ((1920, 1080), (1366, 768)):
        tag = f"{w}x{h}"
        ctx = b.new_context(viewport={"width": w, "height": h})
        z = open_chat(ctx, "Zainab")
        z.evaluate("localStorage.clear()"); z.reload(); z.fill("#username", "Zainab"); z.click("text=Enter"); z.click(".tab-nav button >> text=Chat")
        z.screenshot(path=os.path.join(OUT, f"1_group_chat_{tag}.png"))

        conv(z, "Meera").click()
        z.screenshot(path=os.path.join(OUT, f"2_one_on_one_{tag}.png"))

        conv(z, "Class group").click(); z.click("text=Request notes")
        z.select_option("#chat-req-subject", "Python"); z.fill("#chat-req-topic", "File handling lab notes")
        z.screenshot(path=os.path.join(OUT, f"3_request_form_{tag}.png"))
        z.click("text=Send request")

        a = open_chat(ctx, "Aarav")
        a.locator(".chat-request").last.locator("button").click()
        a.screenshot(path=os.path.join(OUT, f"4b_shared_second_tab_Aarav_{tag}.png"))
        z.wait_for_function("(() => { const c = document.querySelectorAll('.chat-request'); return c[c.length-1].querySelector('.chat-status').textContent === 'Shared'; })()")
        z.screenshot(path=os.path.join(OUT, f"4_shared_seen_by_requester_{tag}.png"))
        ctx.close()
    b.close()
print("saved to", OUT)
for f in sorted(os.listdir(OUT)):
    print("  ", f)

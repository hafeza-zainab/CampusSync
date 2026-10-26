"""Takes the chat screenshots (group chat, one-to-one, template form, a request answered from a second tab)
at 1920x1080 and 1366x768 and saves them in ../chat_screenshots/.

    py tests/chat_screenshots.py        (server running; from the vision folder)

The images show DEMO accounts (placeholder college IDs) and seeded demo messages, not real conversations.
"""
import os
import re

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "chat_screenshots")
os.makedirs(OUT, exist_ok=True)
ID = {"Zainab": "DEMO-CS-001", "Aarav": "DEMO-CS-002"}


def conv(pg, name):
    return pg.locator(".chat-convo", has=pg.locator(".chat-convo-title", has_text=re.compile(f"^{name}$")))


def open_chat(ctx, user):
    pg = ctx.new_page()
    pg.goto(BASE + "/campus/"); pg.fill("#username", ID[user]); pg.click("text=Enter")
    pg.click(".tab-nav button >> text=Chat")
    return pg


with sync_playwright() as p:
    b = p.chromium.launch()
    for old in os.listdir(OUT):
        if old.endswith(".png"):
            os.remove(os.path.join(OUT, old))       # replace the previous set (they showed the old free-text chat)
    for w, h in ((1920, 1080), (1366, 768)):
        tag = f"{w}x{h}"
        ctx = b.new_context(viewport={"width": w, "height": h})
        z = open_chat(ctx, "Zainab")
        z.screenshot(path=os.path.join(OUT, f"1_group_chat_{tag}.png"))

        conv(z, "Meera").click()
        z.screenshot(path=os.path.join(OUT, f"2_one_on_one_{tag}.png"))

        conv(z, "Class group").click(); z.click("#chat-new-request")
        z.select_option("#chat-req-subject", "Python"); z.fill("#chat-req-topic", "File handling lab notes")
        z.screenshot(path=os.path.join(OUT, f"3_template_form_{tag}.png"))
        z.click("dialog.chat-dialog button[type=submit]")

        a = open_chat(ctx, "Aarav")
        a.locator(".chat-request").last.locator("button").click()
        a.screenshot(path=os.path.join(OUT, f"4b_answered_second_tab_Aarav_{tag}.png"))
        z.wait_for_function("(() => { const c = document.querySelectorAll('.chat-request'); return c[c.length-1].querySelector('.chat-status').textContent === 'Shared'; })()")
        z.screenshot(path=os.path.join(OUT, f"4_answered_seen_by_requester_{tag}.png"))
        ctx.close()
    b.close()
print("saved to", OUT)
for f in sorted(os.listdir(OUT)):
    print("  ", f)

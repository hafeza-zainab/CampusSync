"""Checks of the server's own rules over real HTTP: upload limits and file types (and, below, the admin token,
/health and the request log).

    py tests/api_checks.py                 (from the vision folder; starts its own server on a spare port)
    CAMPUS_BASE=http://localhost:8000 CAMPUS_ADMIN_TOKEN=<its token> py tests/api_checks.py
                                       (use a server that is already running instead: Docker, EC2, ...; it WILL delete that
                                        server's saved entries, and the 'no token configured' checks are skipped)

When it starts its own server it uses a temporary entries file and a known admin token, so it never
touches data/entries.json. Only standard-library modules plus the project's own dependencies are used (no httpx / requests).
"""
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VISION = os.path.join(HERE, "..")
SAMPLES = os.path.join(VISION, "samples")
sys.path.insert(0, VISION)

from PIL import Image   # noqa: E402
import pymupdf          # noqa: E402

results = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   [{detail}]"))
    results.append(bool(ok))


# ---- server: use CAMPUS_BASE, or start our own -------------------------------------------------------------------
TOKEN = os.environ.get("CAMPUS_ADMIN_TOKEN") or "test-admin-token"      # for an external server, pass its token in CAMPUS_ADMIN_TOKEN
tmp = tempfile.TemporaryDirectory()
STORE = os.path.join(tmp.name, "entries.json")
servers = []


def start_server(env_extra, store):
    """Start uvicorn on a free port with the given environment; return its base URL."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {k: v for k, v in os.environ.items() if k != "CAMPUS_ADMIN_TOKEN"}
    env.update(env_extra, CAMPUS_STORE=store)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(port), "--log-level", "warning"],
                            cwd=VISION, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    servers.append(proc)
    url = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            urllib.request.urlopen(url + "/api/catalog", timeout=2).read()
            return url
        except Exception:
            if proc.poll() is not None:
                sys.exit("server did not start:\n" + proc.stdout.read().decode(errors="replace"))
            time.sleep(1)
    sys.exit("server did not start in 120 s")


OWN_SERVER = not os.environ.get("CAMPUS_BASE")
BASE = os.environ.get("CAMPUS_BASE") or start_server({"CAMPUS_ADMIN_TOKEN": TOKEN}, STORE)


def http(method, path, data=None, headers=None, base=None):
    """Return (status, parsed JSON or text). Non-2xx answers are returned, not raised."""
    req = urllib.request.Request((base or BASE) + path, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body, status = r.read(), r.status
    except urllib.error.HTTPError as e:
        body, status = e.read(), e.code
    try:
        return status, json.loads(body)
    except ValueError:
        return status, body.decode(errors="replace")


def post(name, data, **form):
    boundary = "----apichecks"
    body = b""
    for k, v in form.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
    body += data + f"\r\n--{boundary}--\r\n".encode()
    return http("POST", "/api/analyze", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})


def detail(r):
    return r[1].get("detail", "") if isinstance(r[1], dict) else str(r[1])


def pdf_bytes(pages):
    doc = pymupdf.open()
    for _ in range(pages):
        doc.new_page()
    out = doc.tobytes()
    doc.close()
    return out


def png_bytes(w, h):
    buf = io.BytesIO()
    Image.new("L", (w, h), 255).save(buf, "PNG")
    return buf.getvalue()


def sample(name):
    with open(os.path.join(SAMPLES, name), "rb") as f:
        return f.read()


MAX_BYTES = 10 * 1024 * 1024
PNG_SIG = b"\x89PNG\r\n\x1a\n"

try:
    print("== upload size")
    r = post("big.png", PNG_SIG + b"\0" * MAX_BYTES)
    check("a file over the size cap is refused with 413 and says the limit", r[0] == 413 and "10 MB" in detail(r), f"{r[0]} {detail(r)[:120]}")
    r = post("edge.png", PNG_SIG + b"\0" * (MAX_BYTES - 8))
    check("a file of exactly the cap is NOT refused for size (it fails later, as a damaged image)", r[0] == 400, f"{r[0]} {detail(r)[:120]}")
    r = post("empty.png", b"")
    check("an empty file is refused with 400", r[0] == 400 and "empty" in detail(r), f"{r[0]} {detail(r)[:120]}")

    print("== file type")
    r = post("pic.gif", b"GIF89a" + b"\0" * 50)
    check("a .gif is refused with 415 and the message names the allowed types", r[0] == 415 and "PNG, JPG or PDF" in detail(r) and ".gif" in detail(r), f"{r[0]} {detail(r)[:160]}")
    r = post("notes", png_bytes(10, 10))
    check("a file with no extension is refused with 415", r[0] == 415, f"{r[0]} {detail(r)[:120]}")
    r = post("run.exe", b"MZ" + b"\0" * 100)
    check("an .exe is refused with 415", r[0] == 415, f"{r[0]} {detail(r)[:120]}")
    r = post("disguised.png", b"MZ\x90\x00" + b"\0" * 100)
    check("an .exe renamed to .png is refused with 415 (content is checked, not just the name)", r[0] == 415 and "content" in detail(r), f"{r[0]} {detail(r)[:160]}")
    r = post("script.pdf", b"<html><script>alert(1)</script></html>")
    check("an HTML file renamed to .pdf is refused with 415", r[0] == 415, f"{r[0]} {detail(r)[:160]}")
    r = post("wrongname.pdf", png_bytes(10, 10))
    check("a PNG named .pdf is refused with 415 and the mismatch is explained", r[0] == 415 and "PNG" in detail(r), f"{r[0]} {detail(r)[:160]}")
    r = post("UPPER.PNG", b"\xff\xd8\xff" + b"\0" * 50)
    check("a JPEG named .PNG is refused (extension and content must agree)", r[0] == 415, f"{r[0]} {detail(r)[:160]}")

    print("== PDF pages")
    r = post("long.pdf", pdf_bytes(11))
    check("a PDF over the page cap (11 pages) is refused with 413 and the message gives both numbers", r[0] == 413 and "11 pages" in detail(r) and "limit is 10" in detail(r), f"{r[0]} {detail(r)[:160]}")
    r = post("ok.pdf", pdf_bytes(10))
    check("a PDF of exactly 10 pages passes validation (it is analysed; a blank page has nothing to extract)", r[0] == 200 and r[1]["entries"] == [], f"{r[0]} {str(r[1])[:120]}")
    r = post("broken.pdf", b"%PDF-1.7\n" + b"garbage" * 20)
    check("a damaged PDF is refused with 400, not a server error", r[0] == 400 and "PDF" in detail(r), f"{r[0]} {detail(r)[:120]}")

    print("== image size and damage")
    r = post("huge.png", png_bytes(7000, 7000))
    check("an image over the pixel cap (7000x7000) is refused with 413 although the file is small", r[0] == 413 and "7000x7000" in detail(r), f"{r[0]} {detail(r)[:120]}")
    r = post("broken.png", PNG_SIG + b"garbage" * 20)
    check("a damaged PNG is refused with 400, not a server error", r[0] == 400 and "image" in detail(r), f"{r[0]} {detail(r)[:120]}")
    if OWN_SERVER:
        check("none of the refused uploads wrote anything to the entries file", not os.path.exists(STORE) or json.load(open(STORE)) == [])

    print("== good files still work")
    r = post("notice.png", sample("notice.png"))
    check("a valid PNG is accepted and read (5 entries from the sample notice)", r[0] == 200 and len(r[1]["entries"]) == 5, f"{r[0]} {str(r[1])[:120]}")
    r = post("timetable_pdf.pdf", sample("timetable_pdf.pdf"))
    check("a valid PDF is accepted and read (timetable, 11 entries)", r[0] == 200 and len(r[1]["entries"]) == 11, f"{r[0]} {str(r[1])[:120]}")
    r = post("timetable_exif6.jpg", sample("timetable_exif6.jpg"))
    check("a valid JPG is accepted and read (11 entries)", r[0] == 200 and len(r[1]["entries"]) == 11, f"{r[0]} {str(r[1])[:120]}")
    print("== admin token (DELETE /api/entries)")
    before = http("GET", "/api/entries")[1]
    check("setup: there are saved entries to protect", isinstance(before, list) and len(before) > 0, str(before)[:80])
    r = http("DELETE", "/api/entries")
    check("DELETE without a token is refused with 401", r[0] == 401, f"{r[0]} {r[1]}")
    r = http("DELETE", "/api/entries", headers={"X-Admin-Token": "wrong-token"})
    check("DELETE with a wrong token is refused with 401", r[0] == 401, f"{r[0]} {r[1]}")
    r = http("DELETE", "/api/entries", headers={"X-Admin-Token": ""})
    check("DELETE with an empty token is refused with 401", r[0] == 401, f"{r[0]} {r[1]}")
    r = http("DELETE", "/api/entries?admin_token=" + TOKEN)
    check("the token in the URL is not accepted (it would end up in logs)", r[0] == 401, f"{r[0]} {r[1]}")
    r = http("DELETE", "/api/entries", headers={"Authorization": "Bearer " + TOKEN})
    check("the token in an Authorization header is not accepted (only X-Admin-Token)", r[0] == 401, f"{r[0]} {r[1]}")
    check("none of the refused DELETEs removed anything", http("GET", "/api/entries")[1] == before)
    check("reading entries needs no token (GET is public by design)", http("GET", "/api/entries")[0] == 200)
    r = http("DELETE", "/api/entries", headers={"X-Admin-Token": TOKEN})
    check("DELETE with the right token succeeds", r[0] == 200 and r[1] == {"ok": True}, f"{r[0]} {r[1]}")
    check("... and the entries are gone", http("GET", "/api/entries")[1] == [])
    if OWN_SERVER:
        store2 = os.path.join(tmp.name, "entries2.json")
        json.dump([{"subject": "keep me"}], open(store2, "w"))
        base2 = start_server({}, store2)             # a server started WITHOUT CAMPUS_ADMIN_TOKEN
        r = http("DELETE", "/api/entries", base=base2)
        check("a server with no CAMPUS_ADMIN_TOKEN set refuses DELETE with 403 (fails closed)", r[0] == 403 and "CAMPUS_ADMIN_TOKEN" in str(r[1]), f"{r[0]} {r[1]}")
        r = http("DELETE", "/api/entries", headers={"X-Admin-Token": ""}, base=base2)
        check("... even with an empty token header (empty must not match an unset token)", r[0] == 403, f"{r[0]} {r[1]}")
        check("... and the entries were not deleted", http("GET", "/api/entries", base=base2)[1] == [{"subject": "keep me"}])
finally:
    for proc in servers:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
    tmp.cleanup()

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)

"""Checks of the server's own rules over real HTTP: upload limits and file types (and, below, the admin token,
/health and the request log).

    py tests/api_checks.py                 (from the vision folder; starts its own server on a spare port)
    CAMPUS_BASE=http://localhost:8000 py tests/api_checks.py     (use a server that is already running instead:
                                                                  Docker, EC2, ...; the log checks are skipped then)

When it starts its own server it uses a temporary entries file, a known admin token and a temporary log file, so it never
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
TOKEN = "test-admin-token"
tmp = tempfile.TemporaryDirectory()
STORE = os.path.join(tmp.name, "entries.json")
server = None
BASE = os.environ.get("CAMPUS_BASE")
if not BASE:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    BASE = f"http://127.0.0.1:{port}"
    env = dict(os.environ, CAMPUS_STORE=STORE, CAMPUS_ADMIN_TOKEN=TOKEN)
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(port), "--log-level", "warning"],
                              cwd=VISION, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(120):
        try:
            urllib.request.urlopen(BASE + "/api/catalog", timeout=2).read()
            break
        except Exception:
            if server.poll() is not None:
                sys.exit("server did not start:\n" + server.stdout.read().decode(errors="replace"))
            time.sleep(1)
    else:
        server.kill()
        sys.exit("server did not start in 120 s")
OWN_SERVER = server is not None


def http(method, path, data=None, headers=None):
    """Return (status, parsed JSON or text). Non-2xx answers are returned, not raised."""
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers or {})
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
finally:
    if server:
        server.terminate()
        try:
            server.wait(10)
        except subprocess.TimeoutExpired:
            server.kill()
    tmp.cleanup()

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)

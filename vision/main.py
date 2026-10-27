"""FastAPI server - the thin layer between the browser and pipeline.py.

Run:   py -m uvicorn main:app --port 8000      (from inside the vision folder)
Open:  http://localhost:8000

Endpoints
  GET    /api/catalog   courses / semesters / subjects (data/catalog.json)
  POST   /api/analyze   upload PNG/JPG/PDF, max 10 MB / 10 PDF pages (+ optional course, semester) -> detections + entries, auto-saved
  GET    /api/entries   everything saved so far (the Study Panel reads this)
  DELETE /api/entries   clear all (handy before re-recording the demo)
"""
import base64
import io
import json
import os

import cv2
from PIL import Image
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import catalog
import pipeline

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.environ.get("CAMPUS_STORE") or os.path.join(HERE, "data", "entries.json")   # CAMPUS_STORE: tests / Docker volume
os.makedirs(os.path.dirname(STORE), exist_ok=True)

app = FastAPI(title="CampusSync Vision")

# Limits for /api/analyze (override with environment variables if needed)
MAX_UPLOAD_BYTES = int(os.environ.get("CAMPUS_MAX_UPLOAD_BYTES", 10 * 1024 * 1024))   # 10 MB
MAX_PDF_PAGES = int(os.environ.get("CAMPUS_MAX_PDF_PAGES", 10))
MAX_IMAGE_PIXELS = int(os.environ.get("CAMPUS_MAX_IMAGE_PIXELS", 40_000_000))         # e.g. 8000 x 5000
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}


def sniff_type(data: bytes):
    """What the bytes really are (the file name can lie): 'png', 'jpg', 'pdf' or None."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"%PDF-"):
        return "pdf"
    return None


def validate_upload(data: bytes, filename: str):
    """Reject anything that is not a reasonably sized PNG / JPG / PDF, with a message the user can act on."""
    if not data:
        raise HTTPException(400, "The file is empty.")
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"Unsupported file type '{ext or 'none'}'. Upload a PNG, JPG or PDF.")
    kind = sniff_type(data)
    if kind is None:
        raise HTTPException(415, "The file content is not a PNG, JPG or PDF (it may have been renamed). Upload a PNG, JPG or PDF.")
    if {"png": ".png", "jpg": ".jpg", "pdf": ".pdf"}[kind] != (".jpg" if ext == ".jpeg" else ext):
        raise HTTPException(415, f"The file name says '{ext}' but the content is a {kind.upper()}. Rename it or upload the original file.")
    if kind == "pdf":
        import pymupdf
        try:
            with pymupdf.open(stream=data, filetype="pdf") as doc:
                pages = doc.page_count
        except Exception:
            raise HTTPException(400, "Could not read this PDF (it may be damaged or password-protected).")
        if pages > MAX_PDF_PAGES:
            raise HTTPException(413, f"This PDF has {pages} pages; the limit is {MAX_PDF_PAGES}.")
    else:
        try:
            w, h = Image.open(io.BytesIO(data)).size       # reads only the header
        except Exception:
            raise HTTPException(400, "Could not read this file as an image.")
        if w * h > MAX_IMAGE_PIXELS:
            raise HTTPException(413, f"This image is {w}x{h} pixels; the limit is {MAX_IMAGE_PIXELS // 1_000_000} million pixels.")


def load_entries():
    try:
        with open(STORE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def save_entries(entries):
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), course: str = Form(""), semester: str = Form("")):
    data = await file.read(MAX_UPLOAD_BYTES + 1)         # never hold more than the limit (+1 byte to detect "over") in memory
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File too large (limit {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).")
    validate_upload(data, file.filename or "upload")
    try:
        result = pipeline.analyze(data, file.filename or "upload", semester=semester, course=course)
    except ValueError as e:
        raise HTTPException(400, str(e))

    ok, png = cv2.imencode(".png", result.pop("image"))
    result["image"] = "data:image/png;base64," + base64.b64encode(png.tobytes()).decode()

    # auto-tag: save new entries, skip ones we already have (same course/semester/subject/date/topic)
    def entry_key(e):
        return (e.get("course", ""), e.get("semester", ""), e["subject"], e["date"], e["topic"])

    saved = load_entries()
    seen = {entry_key(e) for e in saved}
    added = 0
    for e in result["entries"]:
        e["source"] = file.filename
        key = entry_key(e)
        e["is_new"] = key not in seen
        if e["is_new"]:
            saved.append({k: v for k, v in e.items() if k not in ("source_box", "is_new")})
            seen.add(key)
            added += 1
    save_entries(saved)
    result["added"] = added
    return result


@app.get("/api/catalog")
def get_catalog():
    """Courses -> semesters -> subjects, for the dropdowns. (Edit data/catalog.json to change it.)"""
    return catalog.load_catalog()


@app.get("/api/entries")
def entries():
    return load_entries()


@app.delete("/api/entries")
def clear():
    save_entries([])
    return {"ok": True}


@app.get("/")
def home():
    """CampusSync is one product: the front door is the app. Vision (the screenshot reader) is inside it."""
    return RedirectResponse("/campus/")


@app.get("/vision")
def vision_page():
    """The screenshot reader page. The app embeds it (Study Panel > Import from screenshot); it also works on its own."""
    return FileResponse(os.path.join(HERE, "static", "index.html"))


# The attendance app (../index.html etc.) is served from the same server at /campus/, so it and
# the Vision page share one origin = one localStorage (see ../store.js). Only these files are
# served, so nothing else in the project folder (.git, data/, ...) is exposed.
CAMPUS_DIR = os.path.dirname(HERE)
CAMPUS_FILES = {"index.html", "app.js", "data.js", "store.js", "style.css", "studypanel.html", "chatbot.html", "chat.js", "chat.css", "import.js", "import.css", "study.js", "study.css", "demo.js", "tour.js"}


@app.get("/campus")
def campus_redirect():
    return RedirectResponse("/campus/")


@app.get("/campus/")
@app.get("/campus/{name}")
def campus(name: str = "index.html"):
    if name not in CAMPUS_FILES:
        raise HTTPException(404, "Not found")
    # no-cache: the browser re-checks every file, so edits to the app show up on a normal refresh
    return FileResponse(os.path.join(CAMPUS_DIR, name), headers={"Cache-Control": "no-cache"})


app.mount("/samples", StaticFiles(directory=os.path.join(HERE, "samples")), name="samples")


@app.on_event("startup")
def warm_up():
    """Load the OCR model once at boot so the first upload (and the demo) is fast."""
    import numpy as np
    pipeline.run_ocr(np.full((64, 256, 3), 255, np.uint8))

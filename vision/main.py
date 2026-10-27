"""FastAPI server - the thin layer between the browser and pipeline.py.

Run:   py -m uvicorn main:app --port 8000      (from inside the vision folder)
Open:  http://localhost:8000

Endpoints
  GET    /api/catalog   courses / semesters / subjects (data/catalog.json)
  POST   /api/analyze   upload image/PDF (+ optional course, semester) -> detections + entries, auto-saved
  GET    /api/entries   everything saved so far (the Study Panel reads this)
  DELETE /api/entries   clear all (handy before re-recording the demo)
"""
import base64
import json
import os

import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import catalog
import pipeline

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "data", "entries.json")
os.makedirs(os.path.dirname(STORE), exist_ok=True)

app = FastAPI(title="CampusSync Vision")


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
    data = await file.read()
    if len(data) > 15_000_000:
        raise HTTPException(413, "File too large (15 MB max)")
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

# CampusSync

A college app with **attendance** (by month, day and subject, with green/red marks and monthly stats), **announcements**, a **Study Panel** (upload and filter materials by semester, subject, topic and date), and a **template-only chat**. A built-in screenshot reader (computer vision: OpenCV + OCR) turns a timetable screenshot or a notice into attendance, announcements and Study Panel entries, so nothing has to be typed by hand.

It is **one product**: you open one address and everything is inside it.

## How to run

**You need:** Windows, Python 3.10 or newer (the `py` launcher), and an internet connection once to install packages.

1. **Install (first time only).** Open a terminal in this folder and run:
   ```
   py -m pip install -r requirements.txt
   ```
2. **Start.** Double-click **`run.bat`**, or run:
   ```
   cd vision
   py -m uvicorn main:app --port 8000
   ```
   Wait about 15 seconds (it loads the text-reading model first).
3. **Open** `http://localhost:8000/` (`run.bat` opens it for you). It goes straight to the app.
4. On the login screen click **▶ Run 60-second demo** to watch a guided tour, or log in yourself.

| Demo account (placeholder IDs, not real people) | Password | Role |
|---|---|---|
| `DEMO-CS-001` | `cr-demo` | CR (can post announcements) |
| `DEMO-CS-002` | `acr-demo` | ACR (can post announcements) |
| `DEMO-CS-003` | `student-demo` | Student (read-only announcements) |
| `DEMO-CS-004` | `student-demo` | Student |

**Try the screenshot reader:** log in, open **Study Panel**, open the **📷 Import from screenshot** card and upload `vision/samples/timetable_demo_new.png` (a timetable) or `vision/samples/notice.png` (a notice). To see it on its own, open `http://localhost:8000/vision`.

**Stop** with Ctrl+C in the terminal. After you change any Python file, stop and start again.

**If something does not work:** the app must be opened through the server (`http://localhost:8000/`), not by double-clicking `index.html`. If a button seems dead, restart the server. If `py` is not found, install Python from python.org and tick "Add to PATH".

## Build, run and test

All commands are run from this folder (Windows; `py` is the Python launcher).

| Step | Command |
|---|---|
| **Install** (exact tested versions) | `py -m pip install -r requirements.txt` |
| Install everything exactly as tested, including indirect packages | `py -m pip install -r requirements.lock.txt` |
| **Run** | `run.bat`, or `cd vision` then `py -m uvicorn main:app --port 8000` |
| Check the OpenCV version | `py -c "import cv2; print(cv2.__version__)"` prints `5.0.0` |
| **Unit tests** (44 checks, includes "runs on OpenCV 5"; no server needed) | `cd vision` then `py tests/unit.py` |
| **Accuracy tool** on the synthetic images (12 images) | `cd vision` then `py eval.py --dir samples` |
| **Browser smoke test** (16 checks; server must be running) | `py -m pip install -r vision/requirements-dev.txt`, `py -m playwright install chromium`, then `cd vision` and `py tests/smoke_app.py` |

The dependencies are pinned to the versions that passed these tests on Windows with Python 3.14 (OpenCV 5.0.0 via `opencv-python-headless==5.0.0.93`). Other Python versions and other operating systems have not been tested. `vision/tests/e2e.py` and `vision/tests/demo_walkthrough.py` were written for an earlier version of the app and no longer match it.

## What is in this folder
| Path | What it is |
|---|---|
| `index.html`, `app.js`, `data.js`, `style.css`, `store.js` | The app: login, calendar, attendance, announcements |
| `study.js`, `chat.js`, `import.js`, `demo.js`, `tour.js` | Study Panel, chat, the Import card, demo data, the 60-second tour |
| `vision/` | The server and the screenshot reader (Python, FastAPI, OpenCV, OCR), its tests and samples |

## Read before you rely on it
- This is a **front-end demo**: data is stored in your browser (localStorage), not on a server database.
- The demo passwords are written in plain text in `store.js`; this is **not secure authentication**.
- The chat uses **simulated users in one browser** with no server sync. It is not real-time chat between different computers.
- The screenshot reader has been tested on **synthetic images only**; accuracy on real student screenshots has not been measured.

**Full details, test results and limits:** [`vision/README.md`](vision/README.md).

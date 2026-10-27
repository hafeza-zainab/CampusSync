# Architecture

This diagram shows the data flow that exists in the code. Every box is a real function, file or store; nothing planned or hypothetical is drawn. **There is no cloud component: the project runs locally and is not deployed on AWS.**

```mermaid
flowchart TD
    subgraph Browser["Browser (CampusSync app at /campus/)"]
        APP["App: calendar, attendance, announcements, Study Panel, chat<br/>index.html, app.js, study.js, chat.js, store.js"]
        CARD["Import from screenshot card (import.js)<br/>iframe of the Vision page /vision"]
        VIS["Vision page: upload, boxes overlay, review card<br/>vision/static/index.html"]
        LS[("localStorage<br/>announcements, timetable (+ backup), study,<br/>attendance per ID, chat, session")]
    end

    subgraph Server["Server (FastAPI, vision/main.py, runs locally)"]
        API["POST /api/analyze<br/>file + optional course and semester"]
        subgraph Pipe["pipeline.analyze (vision/pipeline.py)"]
            LOAD["load_pages / decode_image<br/>Pillow EXIF rotation, PyMuPDF renders PDF pages"]
            PRE["preprocess<br/>resize, deskew (Canny + HoughLinesP + warpAffine), CLAHE"]
            GRID["find_grid (OpenCV)<br/>adaptiveThreshold, morphologyEx OPEN, findContours,<br/>drop_containers, group_rows"]
            OCR["run_ocr<br/>RapidOCR on onnxruntime (CPU)"]
            TT["parse_timetable<br/>header and layout detection, cell to text, day and time"]
            NT["parse_notice / parse_notes<br/>date regexes, task keywords, topic"]
            MATCH["subject matching, teacher and room extraction,<br/>confidence = OCR score x match x scope factor"]
        end
        CAT[("data/catalog.json<br/>courses, semesters, subjects, teachers, rooms<br/>(catalog.py)")]
        ENT[("data/entries.json<br/>extracted entries only, no images")]
    end

    APP --- CARD --- VIS
    VIS -->|"1. upload"| API
    API --> LOAD --> PRE
    PRE --> GRID
    PRE --> OCR
    GRID -->|"table found"| TT
    OCR --> TT
    GRID -->|"no table"| NT
    OCR --> NT
    TT --> MATCH
    NT --> MATCH
    CAT --> MATCH
    MATCH -->|"entries + boxes + annotated image + stage timings"| API
    API -->|"entries"| ENT
    API -->|"JSON response"| VIS

    VIS -->|"2. human review: edit fields, low confidence (< 0.80) must be ticked"| REVIEW{"User confirms"}
    REVIEW -->|"post as announcements"| LS
    REVIEW -->|"timetable: preview, confirm, Undo"| LS
    VIS -->|"every entry, with source and check-this flag"| LS
    LS -->|"storage event, no reload"| APP
```

## How to read it
1. **Upload.** The Vision page (shown inside the app's Study Panel, or alone at `/vision`) sends the file to `POST /api/analyze`. Nothing leaves the machine: the server is local and contains no outbound network calls.
2. **Pipeline.** The image is loaded (EXIF rotation for photos, page rendering for PDFs), deskewed and contrast-corrected, then two things happen on the cleaned image: OpenCV finds table cells (`find_grid`), and RapidOCR reads text blocks (`run_ocr`). If a table was found, `parse_timetable` assigns text to day and time columns; otherwise `parse_notice` (and `parse_notes` as a last resort) read dated lines. Subjects are matched to `data/catalog.json` (limited to the chosen course and semester when one is chosen), teacher and room are extracted and marked as read from the image or filled from the catalog, and every entry gets a confidence value.
3. **Response and server storage.** The response carries the entries, the detected boxes, the cleaned image (as base64, for the overlay) and stage timings. The server saves only the extracted entries (with the source file name and, for notices, the original sentence) to `data/entries.json`. It does not save the uploaded file or the image.
4. **Review.** Nothing reaches the app on its own. For notices, a review card lets the user edit each entry; entries under 80% confidence must be ticked as checked before they can be posted. For timetables, a preview shows lectures added and removed and a warning for attendance marks that would be hidden; replacing needs a click, and Undo restores the old timetable.
5. **Storage.** The app has no database. Approved results are written to the browser's `localStorage`; every extracted entry is also added to the Study Panel store, with its source and a "check this" flag when confidence is under 0.80. The app reads these keys and updates through the browser's `storage` event.

## What is not in the diagram because it does not exist
No AWS service, no container, no load balancer, no database server, no user accounts on a server, no message queue. See [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md), section "Deployment".

# CampusSync (the app + the screenshot reader) in one container.
#
# STATUS: never built on the author's machine (no Docker there). The CI job 'docker' in .github/workflows/ci.yml builds and
# runs it on a GitHub Ubuntu runner (see docs/TECHNICAL_REPORT.md section 8 for the result). Not deployed on AWS.
# Set CAMPUS_ADMIN_TOKEN to allow DELETE /api/entries; without it that call is refused.
#
#   docker build -t campussync .
#   docker run -d -p 8000:8000 -e CAMPUS_ADMIN_TOKEN=<secret> --name campussync campussync
#   open http://localhost:8000/
FROM python:3.14-slim

# onnxruntime (used by the OCR) needs the OpenMP runtime on Linux
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install the exact tested versions first, so this layer is cached when only code changes
COPY vision/requirements.txt vision/requirements.txt
RUN pip install --no-cache-dir -r vision/requirements.txt

COPY . .

# the server must start from the vision folder (it serves the app files from the folder above it)
WORKDIR /app/vision
EXPOSE 8000

# the text-recognition model loads at start-up, so give the server time before the first check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

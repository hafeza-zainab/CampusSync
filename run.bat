@echo off
rem Starts CampusSync (the app and its screenshot reader) and opens it in your browser.
rem First time only:  py -m pip install -r requirements.txt
cd /d "%~dp0vision"
rem the server loads its text-reading model first (about 15 seconds), so the browser opens after a short wait
start "" cmd /c "timeout /t 20 /nobreak >nul & start http://localhost:8000/"
py -m uvicorn main:app --port 8000

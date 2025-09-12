@echo off
echo Building frontend and updating container...
cd frontend
call npm run build
cd ..
echo Frontend updated! Refresh your browser.
pause

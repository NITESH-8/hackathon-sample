@echo off
echo Starting Development Environment...
echo.

echo 1. Building frontend...
cd frontend
call npm run build
cd ..

echo.
echo 2. Starting Docker containers...
docker compose -f docker-compose.dev.yml up -d

echo.
echo 3. Development setup complete!
echo.
echo Frontend changes workflow:
echo - Make changes in src/ folder
echo - Run: cd frontend ^&^& npm run build
echo - Refresh browser (no Docker rebuild needed!)
echo.
echo Backend changes still require: docker compose -f docker-compose.dev.yml up -d --build app
echo.
echo App is running at: http://localhost:5000
pause

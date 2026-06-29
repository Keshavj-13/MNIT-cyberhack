@echo off
REM build.bat — Native Windows Docker Desktop build script
REM Run from the project root: .\build.bat

echo === AURA Platform Build (Native Docker Desktop) ===

REM Build qwen-base only if it doesn't exist (one-time ~2GB download)
docker image inspect mnit-qwen-base:latest >nul 2>&1
if %errorlevel% neq 0 (
    echo === Building qwen-base image (first time only - downloads Qwen3.5-0.8B ~2GB) ===
    docker build -f Dockerfile.qwen-base -t mnit-qwen-base:latest .
    if %errorlevel% neq 0 ( echo Build failed && exit /b 1 )
) else (
    echo === qwen-base already cached, skipping ===
)

echo === Building all app images ===
docker compose build --parallel
if %errorlevel% neq 0 ( echo Build failed && exit /b 1 )

echo === Seeding demo data ===
docker compose run --rm customer-api python /app/seed_demo.py

echo === Starting all services ===
docker compose up -d

echo.
echo === Services started ===
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo.
echo  Customer Portal:  http://localhost:3001
echo  Admin Dashboard:  http://localhost:3002
echo  Attacker Console: http://localhost:3003
echo  Showcase:         http://localhost:3004

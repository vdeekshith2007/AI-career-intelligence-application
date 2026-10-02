@echo off
echo ============================================================
echo AI Career Intelligence - Starting Local Environment
echo ============================================================

REM 1. Start Docker PostgreSQL in WSL if needed
wsl -d Ubuntu -u root docker compose -f /mnt/c/Users/vatap/OneDrive/Desktop/AI-Career-Intelligence/docker-compose.yml up -d db

REM 2. Run unified dev runner
node scripts\dev.js
pause

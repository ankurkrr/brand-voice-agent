@echo off
echo [BACKUP] Starting database backup...

:: Create backups directory if not exists
if not exist "backups" mkdir backups

:: Generate filename with timestamp
set filename=backups\backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.sql
set filename=%filename: =0%

:: Run pg_dump
:: Assumes PGPASSWORD is set in env or .pgpass, or user will be prompted
echo [BACKUP] Dumping insights_db to %filename%...
pg_dump -U postgres -h localhost -d insights_db -f "%filename%"

if %ERRORLEVEL% equ 0 (
    echo [BACKUP] SUCCESS: Saved to %filename%
) else (
    echo [BACKUP] FAILURE: pg_dump returned error code %ERRORLEVEL%
)
pause

@echo off
echo ============================================================
echo Starting Celery Worker
echo ============================================================
echo.
echo Worker will process background tasks (ingestion, ideation)
echo Press Ctrl+C to stop
echo.

set ENV=local
celery -A core.worker.celery_app worker --loglevel=info --pool=solo

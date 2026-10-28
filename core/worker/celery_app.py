import os
from celery import Celery
from dotenv import load_dotenv


# Load appropriate .env file based on environment
if os.getenv("ENV") == "local":
    load_dotenv(".env.local")
else:
    load_dotenv()

# Redis connection string
# Default to localhost for local dev, or use container name 'redis' via env var
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
BACKEND_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

celery_app = Celery(
    "voice_meta_worker",
    broker=BROKER_URL,
    backend=BACKEND_URL,
    include=["core.worker.tasks"]  # Auto-discover tasks in this module
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

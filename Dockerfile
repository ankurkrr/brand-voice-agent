# --- Stage 1: Builder ----
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# ---- Stage 2: Runtime ----
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

CMD ["sh", "-c", "uvicorn adapters.api.main:app --host 0.0.0.0 --port ${PORT}"]
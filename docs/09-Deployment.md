# Deployment

The Voice Meta-Agent is packaged as a Docker container, designed to be deployed on Google Cloud Run for auto-scaling, with a managed Cloud SQL instance for persistence.

## 1. Containerization

The `Dockerfile` packages the FastAPI application and its LangChain dependencies.

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Cloud Run requires port 8080 by default
EXPOSE 8080

CMD ["uvicorn", "adapters.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## 2. Infrastructure Setup (GCP)

- **Compute:** Google Cloud Run (Fully managed, scales to zero).
- **Database:** Google Cloud SQL (MySQL 8.0).
- **Vector Store:** ChromaDB requires a persistent file system. We utilize Cloud Run's native support for **Google Cloud Storage (GCS) FUSE** to mount a bucket to the container at `/app/chroma_data_volume`, ensuring vector embeddings survive container restarts.

## 3. Environment Variables

Strict separation of configuration from code. Required variables:
- `GOOGLE_API_KEY`: Gemini API Access.
- `TAVILY_API_KEY`: Web Search API Access.
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: Cloud SQL credentials.
- `CHROMA_DB_DIR`: Set to `/app/chroma_data_volume`.
- `LANGCHAIN_TRACING`: Set to `true` for LangSmith observability in production.

## 4. CI/CD Pipeline

Deployment is automated via Google Cloud Build (`cloudbuild.yaml`).
1. Triggered on push to the `main` branch.
2. Runs unit tests (`pytest`).
3. Builds the Docker image and pushes to Artifact Registry.
4. Deploys the new revision to Cloud Run.

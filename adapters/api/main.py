"""
FastAPI Application Entry Point - Cloud Run Compatible

Endpoints:
- GET /health - Container health check
- GET / - Health check + router listing
- POST /ingest - Agent 1 (Brand Voice)
- POST /ideation/ideate - Agent 2 (Content Strategy)
- POST /execute - Agent 3 (Multi-Platform Copy)
- POST /brands/create - Brand management
- POST /profiles/{id}/feedback - User feedback loop
"""
import os
from dotenv import load_dotenv

# Load appropriate .env file based on environment
if os.getenv("ENV") == "local":
    load_dotenv(".env.local")
else:
    load_dotenv()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import os
import logging
from pathlib import Path

# Absolute Minimum Guard
if os.getenv("ENV") == "local" and os.getenv("DB_PORT") == "3307":
    raise RuntimeError("Local mode cannot use Cloud DB")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from adapters.api.routers.ingest_router import router as ingest_router
from adapters.api.routers.brand_router import router as brand_router
from adapters.api.routers.profile_router import router as profile_router
from adapters.api.routers.ideation_router import router as ideation_router
from adapters.api.routers.feedback_router import router as feedback_router
from adapters.api.routers.execution_router import router as execution_router
from adapters.api.routers.orchestration_router import router as orchestration_router
from adapters.api.routers.voice_refinement_router import router as voice_refinement_router


app = FastAPI()


def _validate_environment():
    """Validate required environment variables. Non-blocking."""
    required_vars = {
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_NAME": os.getenv("DB_NAME"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
    }
    
    missing = [k for k, v in required_vars.items() if not v]
    
    if missing:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing)}")
        logger.error("Application will fail on database or LLM operations")
    else:
        logger.info("✅ All required environment variables present")
    
    instance_conn = os.getenv("INSTANCE_CONNECTION_NAME")
    if instance_conn:
        logger.info(f"☁️  Cloud SQL mode: {instance_conn}")
    else:
        logger.info("🖥️  Local/TCP database mode")


def _ensure_chroma_directory():
    """Ensure ChromaDB directory exists. Non-blocking."""
    chroma_dir = Path(os.getenv("CHROMA_DB_DIR", "./chroma_data"))
    if not chroma_dir.exists():
        try:
            chroma_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Created ChromaDB directory: {chroma_dir}")
        except Exception as e:
            logger.warning(f"⚠️  Could not create ChromaDB directory: {e}")
    
    logger.warning("⚠️  Vector data is ephemeral in Cloud Run test deployment")


@app.on_event("startup")
async def startup_event():
    """Non-blocking startup validation - Never crashes on missing dependencies"""
    logger.info("🚀 Starting Brand Voice & Persona Ingestion...")
    
    # Validate environment (non-blocking)
    _validate_environment()
    
    # Create ChromaDB directory (non-blocking)
    _ensure_chroma_directory()
    
    # Test database connection (non-blocking, logs only)
    try:
        from data.db.session import test_connection
        connected = await test_connection()
        if connected:
            logger.info("✅ Database connection verified")
        else:
            logger.error("❌ Database connection test failed")
            logger.error("Application started but DB operations will fail. Check /ready endpoint.")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {type(e).__name__}: {str(e)}")
        logger.error("Application started but DB operations will fail. Check /ready endpoint.")
    
    logger.info("✅ Application startup complete (check /ready for full health)")


@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown - close database pool"""
    from data.db.session import close_pool
    await close_pool()
    logger.info("🛑 Application shutdown complete")


@app.get("/health")
async def health():
    """Container health check endpoint - Always returns 200 OK (no dependencies)"""
    return {"status": "ok"}


app.include_router(brand_router)
app.include_router(ingest_router, prefix="")
app.include_router(ideation_router, prefix="")
app.include_router(feedback_router, prefix="")
app.include_router(execution_router, prefix="")
app.include_router(orchestration_router)
app.include_router(profile_router, prefix="")
app.include_router(voice_refinement_router)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    templates_dir = Path(__file__).parent.parent.parent / "templates"
    index_file = templates_dir / "index.html"
    
    try:
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return JSONResponse(
            status_code=503,
            content={"error": "Frontend not available", "path": str(index_file)}
        )


@app.get("/results", response_class=HTMLResponse)
async def read_results():
    templates_dir = Path(__file__).parent.parent.parent / "templates"
    results_file = templates_dir / "results.html"
    
    try:
        with open(results_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return JSONResponse(
            status_code=503,
            content={"error": "Results page not available"}
        )


@app.get("/ideation", response_class=HTMLResponse)
async def read_ideation():
    templates_dir = Path(__file__).parent.parent.parent / "templates"
    ideation_file = templates_dir / "ideation.html"
    
    try:
        with open(ideation_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return JSONResponse(
            status_code=503,
            content={"error": "Ideation page not available"}
        )


@app.get("/execution", response_class=HTMLResponse)
async def read_execution():
    templates_dir = Path(__file__).parent.parent.parent / "templates"
    execution_file = templates_dir / "execution.html"
    
    try:
        with open(execution_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return JSONResponse(
            status_code=503,
            content={"error": "Execution page not available"}
        )


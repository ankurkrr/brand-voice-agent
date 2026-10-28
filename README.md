# Brand Voice Agent 🎯

> **Personalized Marketing Content Meta-Agent**  
> A 3-agent AI system that learns your brand voice, researches your topic, and generates platform-native marketing content.

---

## 🏗️ Architecture Overview

The system operates as a linear pipeline where each agent has a strictly defined role:

### Agent 1: Brand Voice Profiler (The Style Police)
- **Role**: Ingests brand assets (PDFs, URLs, past content) to extract your unique voice
- **Output**: A "Golden Record" Voice Profile with tone, rules, and examples
- **Tech**: LangChain + Gemini 2.5 Flash, ChromaDB for vector storage

### Agent 2: Content Strategist (The Researcher)
- **Role**: Analyzes the topic, researches competitors, builds a strategic content brief
- **Output**: Content Brief JSON (target audience, SEO keywords, H2 outline, key messages)
- **Tech**: Tavily API for web research, normalizer for data quality

### Agent 3: Multi-Channel Executor (The Writer)
- **Role**: Takes Voice Profile + Content Brief → generates platform-native copy
- **Output**: Blog posts, LinkedIn posts, Twitter threads, Email campaigns
- **Tech**: Strict compliance validation, rewrite loop, platform rules enforcement

---

## ⚡ Quick Start (Windows)

### Option 1: One-Click Startup (Recommended)

```bash

# Start the main API server (auto-runs DB init)
start_local.bat

```

This will:
1. ✅ Check MySQL connection and initialize database
2. ✅ Install/update dependencies
3. ✅ Start FastAPI server on `http://localhost:8082`

### Option 2: Start Background Worker (Optional)

If you want async task processing:

```bash
# In a separate terminal
start_worker.bat
```

---

## 🛠️ Manual Setup

### Prerequisites

- **Python**: 3.10 or higher
- **MySQL**: Running on `localhost:3306`
- **API Keys**:
  - Google Gemini API Key ([Get it here](https://aistudio.google.com/app/apikey))
  - Tavily API Key ([Get it here](https://tavily.com))

### 1. Environment Setup

Create a `.env` file in the project root:

```ini
# AI Models
GOOGLE_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# MySQL Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=voice_meta

# Optional: MySQL Root Password (for auto DB creation)
MYSQL_ROOT_PASSWORD=your_root_password

# Vector Store
CHROMA_DB_DIR=./chroma_data

# LangChain (optional)
LANGCHAIN_TRACING=false
```

### 2. Install Dependencies

```bash
# Activate virtual environment (if using one)
# .conda\Scripts\activate  OR  .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Initialize Database

The database will auto-initialize when you run `start_local.bat`, but you can also run it manually:

```bash
python scripts\init_database.py
```

This creates 4 tables:
- `brands` - Brand registry
- `voice_profiles` - Agent 1 outputs
- `content_briefs` - Agent 2 outputs  
- `generated_content` - Agent 3 outputs

### 4. Start the API Server

```bash
python -m uvicorn adapters.api.main:app --reload --port 8082
```

**API Docs**: http://localhost:8082/docs

### 5. Start the Frontend

```bash
python -m http.server 5500
```

**UI**: http://localhost:5500/templates/index.html

---

## 📖 Usage Guide

### Workflow: Agent 1 → Agent 2 → Agent 3

#### Step 1: Ingest Brand Voice
1. Navigate to `/templates/index.html`
2. Upload a brand PDF or provide a URL
3. System extracts tone, rules, examples → saves Voice Profile

#### Step 2: Generate Content Brief
1. Navigate to `/templates/ideation.html`
2. Select your brand (from Agent 1)
3. Enter a topic (e.g., "AI in Healthcare")
4. System researches and generates strategic brief

#### Step 3: Execute Copy Generation
1. Navigate to `/templates/execution.html`
2. Use **"Quick Mode"** (auto-fetches Voice + Brief by Brand ID)
3. Select platforms (Blog, LinkedIn, Twitter, Email)
4. Click **Generate**
5. System outputs platform-native content that strictly follows your brand voice
 
---
 
## 🔌 Platform Integration (Release 1.0)
 
The system is ready for platform team integration. All contracts are frozen.
 
### 📚 Key Documentation
*   **[API Directory & Source Map](docs/API_DIRECTORY.md)** 🗺️ (Find all endpoints here)
*   **[API Contracts (Frozen)](docs/platform/api_contracts.md)** 📜 (Request/Response schemas)
*   **[Integration Checklist](docs/platform/integration_checklist.md)** ✅ (Go-Live validation)
*   **[Known Issues](docs/platform/known_issues.md)** ⚠️ (Non-blocking limitations)
 
### ⚠️ Critical Integration Rules
1.  **Null Safety**: `dimensional_scores` may be null (V1 profiles). Frontend **MUST** check before rendering charts.
2.  **Versioning**: 
    *   `version: "v1"` -> Legacy profile (Text-based).
    *   `version: "v2"` -> Enhanced profile (Dimensional Scores + Implicit Rules).
3.  **Manual Hydration**: The `/execute` endpoint has specific data requirements. See [API Contracts](docs/platform/api_contracts.md).
 
---

## 🧪 Testing

### Run Unit Tests

```bash
pytest tests/ -v
```

### Manual Testing Checklist

- [ ] Agent 1: Upload PDF → Voice Profile created
- [ ] Agent 2: Enter topic → Content Brief generated
- [ ] Agent 3: Quick Mode → All platforms generate correctly
- [ ] Database: All 4 tables exist and data persists

---

## 📁 Project Structure

```
brand-voice-agent/
├── adapters/
│   └── api/              # FastAPI routers, main.py
├── core/
│   ├── agents/           # agent1.py, agent2.py, agent3.py
│   ├── voice/            # Voice extraction logic
│   ├── ideation/         # Research & brief building
│   └── execution/        # Copy generation, validation
├── data/
│   ├── db/               # schema.sql, connection pooling
│   └── repos/            # Database repositories
├── domain/
│   └── models/           # Pydantic schemas (requests/responses)
├── scripts/
│   └── init_database.py  # Auto DB setup
├── templates/            # HTML/JS frontend
├── tests/                # Unit tests
├── .env                  # Environment variables (DO NOT COMMIT)
├── requirements.txt      # Python dependencies
├── start_local.bat       # Quick startup script
└── start_worker.bat      # Celery worker (async tasks)
```

---

## 🔧 API Endpoints

### Agent 1 (Voice)
- `POST /ingest` - Upload brand assets
- `GET /ingest/profile/{profile_id}` - Fetch voice profile

### Agent 2 (Ideation)
- `POST /ideation` - Generate content brief
- `GET /briefs/brand/{brand_id}` - Fetch all briefs for a brand

### Agent 3 (Execution)
- `POST /execute` - Generate platform content
- `GET /execute/health` - Health check

### Utilities
- `POST /brands` - Create a brand
- `GET /brands` - List all brands

---

## 🐛 Troubleshooting

### Database Connection Failed
```
ERROR: Database initialization failed!
```
**Fix**: Ensure MySQL is running on `localhost:3306` and credentials in `.env` are correct.

### Import Error: `ModuleNotFoundError`
```
ModuleNotFoundError: No module named 'adapters'
```
**Fix**: Run commands from the project root directory, not subdirectories.

### ChromaDB Error
```
Could not connect to ChromaDB
```
**Fix**: ChromaDB is file-based. Ensure `CHROMA_DB_DIR` path in `.env` is writable.

### API Key Invalid
```
google.api_core.exceptions.InvalidArgument
```
**Fix**: Verify your `GOOGLE_API_KEY` in `.env` is valid and active.

---

## 🚀 Production Deployment

1. **Database**: Migrate from MySQL to PostgreSQL for better JSON support
2. **Environment**: Set `LANGCHAIN_TRACING=true` for monitoring
3. **Server**: Use `gunicorn` instead of `uvicorn --reload`
4. **Secrets**: Use environment variable injection (not `.env` files)
5. **Scaling**: Run Celery workers on separate instances

---

## 📝 Contributing

1. Create a feature branch
2. Run tests: `pytest tests/ -v`
3. Update this README if adding new features
4. Submit PR with description

---

## 📄 License

Proprietary - All rights reserved

---

**Built with ❤️ for marketing teams who demand precision.**

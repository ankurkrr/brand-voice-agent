# Error Fix Log

This document tracks technical errors encountered during development and their corresponding fixes to maintain a record of resolved issues.

## 2025-12-22

### 1. ModuleNotFoundError: asyncpg (Win32 / Interpreter Mismatch)
**Error:** 
The application failed to start on Windows with `ModuleNotFoundError: asyncpg`, properly installed in the virtual environment.
```text
ModuleNotFoundError: No module named 'asyncpg'
```

**Cause:**
Running the `uvicorn` command directly (e.g., `uvicorn api.server:app`) on Windows often resolves to the global system Python interpreter or a different path than the active virtual environment, even if the venv is activated in the shell.

**Fix:**
Enforce running Uvicorn as a module of the *current* Python interpreter.
- **Changed file:** `README.md`
- **Change:**
```bash
# Old (Risky on Windows)
uvicorn api.server:app --reload

# New (Safe)
python -m uvicorn api.server:app --reload
```

---

### 2. ImportError: cannot import name 'score_text_quality'
**Error:**
The application crashed or would crash on startup due to a missing import in `services/voice/example_selector.py`.
```text
ImportError: cannot import name 'score_text_quality' from 'services.voice.style_analysis'
```

**Cause:**
`example_selector.py` contained an import statement for a function that had not yet been implemented in the target module.

**Fix:**
Implemented the missing logic in `services/voice/style_analysis.py`.
- **Changed file:** `services/voice/style_analysis.py`
- **Change:** Added `score_text_quality(text: str) -> float` function implementing heuristics for:
    - Sentence length variance (Standard Deviation)
    - Passive voice ratio
    - Flesch-Kincaid Readability score
    - Text length penalties

---

### 3. Logic Update: Example Selection Ranking
**Issue:**
Examples were being selected solely based on vector cosine similarity, missing the requirement to prioritize "high quality" writing.

**Fix:**
Updated the selection strategy to use a two-step process.
- **Changed file:** `services/voice/example_selector.py`
- **Change:**
    1. Filter candidates by Cosine Similarity (retrieve top `2 * k`).
    2. Re-rank the filtered pool by `score_text_quality` (descending).
    3. Return top `k`.

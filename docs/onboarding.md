# Developer Onboarding Guide

Welcome to the Brand Voice Agent Platform.

This guide explains how to set up your dev environment.

---

# 1. Requirements

* Python 3.10+
* Docker + Docker Compose
* Postman or cURL
* Gemini API key (required)

Create `.env`:

<pre class="overflow-visible!" data-start="7339" data-end="7445"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>GOOGLE_API_KEY</span><span>=your_key_here
</span><span>DATABASE_URL</span><span>=postgresql://postgres:postgres@localhost:</span><span>5432</span><span>/voice_meta
</span></span></code></div></div></pre>

---

# 2. Start Postgres

<pre class="overflow-visible!" data-start="7473" data-end="7635"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>docker run --name voice-meta-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=voice_meta \
  -p </span><span>5432</span><span>:</span><span>5432</span><span> -d postgres
</span></span></code></div></div></pre>

---

# 3. Start API

<pre class="overflow-visible!" data-start="7658" data-end="7709"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>uvicorn api.</span><span>server</span><span>:app </span><span>--reload --port 8082</span><span>
</span></span></code></div></div></pre>

---

# 4. Test Ingestion

Use Postman:

<pre class="overflow-visible!" data-start="7751" data-end="7799"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>POST http://localhost:8082/ingest/upload
</span></span></code></div></div></pre>

form-data:

| key      | value      |
| -------- | ---------- |
| file     | select PDF |
| brand_id | `<uuid>` |

---

# 5. Test Ideation

<pre class="overflow-visible!" data-start="7916" data-end="7936"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>POST /ideate
</span></span></code></div></div></pre>

---

# 6. Test Generation

<pre class="overflow-visible!" data-start="7965" data-end="7987"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>POST /generate
</span></span></code></div></div></pre>

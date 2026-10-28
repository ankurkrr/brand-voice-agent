# API Contracts — Brand Voice Agent Platform

This document defines the REST API interfaces used by the platform.

---

# 1. `/ingest/upload` — Create Voice Profile

### **POST** `/ingest/upload`

Uploads a brand guideline PDF/DOCX/URL and generates a voice profile.

### Request (form-data)

| Field    | Type          | Required |
| -------- | ------------- | -------- |
| file     | File          | Yes      |
| brand_id | string (UUID) | Yes      |

---

### Response Example

<pre class="overflow-visible!" data-start="4880" data-end="4989"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"profile_id"</span><span>:</span><span></span><span>"c4f584ba-482a-4acb-bd55-123abc889932"</span><span>,</span><span>
  </span><span>"collection"</span><span>:</span><span></span><span>"brand_5d5b1b10-2a45"</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

---

# 2. `/profiles/{id}` — Fetch Voice Profile

### **GET** `/profiles/{profile_id}`

Response:

<pre class="overflow-visible!" data-start="5090" data-end="5308"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"profile_id"</span><span>:</span><span></span><span>"..."</span><span>,</span><span>
  </span><span>"brand_id"</span><span>:</span><span></span><span>"..."</span><span>,</span><span>
  </span><span>"profile_data"</span><span>:</span><span></span><span>{</span><span>
    </span><span>"system_prompt"</span><span>:</span><span></span><span>"..."</span><span>,</span><span>
    </span><span>"rules"</span><span>:</span><span></span><span>{</span><span>...</span><span>}</span><span>,</span><span>
    </span><span>"style_metrics"</span><span>:</span><span></span><span>{</span><span>...</span><span>}</span><span>,</span><span>
    </span><span>"example_snippets"</span><span>:</span><span></span><span>[</span><span>...</span><span>]</span><span>,</span><span>
    </span><span>"embedding_meta"</span><span>:</span><span></span><span>{</span><span>...</span><span>}</span><span>
  </span><span>}</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

---

# 3. `/ideate` — Generate Content Brief

### **POST** `/ideate`

Request:

<pre class="overflow-visible!" data-start="5390" data-end="5455"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"topic"</span><span>:</span><span></span><span>"AI in finance"</span><span>,</span><span>
  </span><span>"profile_id"</span><span>:</span><span></span><span>"..."</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

Response:

<pre class="overflow-visible!" data-start="5468" data-end="5612"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"topic"</span><span>:</span><span></span><span>"AI in finance"</span><span>,</span><span>
  </span><span>"target_audience"</span><span>:</span><span></span><span>"..."</span><span>,</span><span>
  </span><span>"seo_keywords"</span><span>:</span><span></span><span>[</span><span>...</span><span>]</span><span>,</span><span>
  </span><span>"h2_outline"</span><span>:</span><span></span><span>[</span><span>...</span><span>]</span><span>,</span><span>
  </span><span>"key_takeaways"</span><span>:</span><span></span><span>[</span><span>...</span><span>]</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

---

# 4. `/generate` — Produce Multi-Channel Copy

### **POST** `/generate`

Request:

<pre class="overflow-visible!" data-start="5702" data-end="5785"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"profile_id"</span><span>:</span><span></span><span>"..."</span><span>,</span><span>
  </span><span>"brief"</span><span>:</span><span></span><span>{</span><span> ... </span><span>}</span><span>,</span><span>
  </span><span>"platform"</span><span>:</span><span></span><span>"linkedin"</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

Response:

{
  "platform": "linkedin",
  "content": "..."
}

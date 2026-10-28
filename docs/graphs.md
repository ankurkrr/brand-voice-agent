# LangGraph Flow Definitions

This document describes the LangGraph graphs used to orchestrate the 3 Super Agents.

---

# 1. Voice Model Graph (Super Agent 1)

Nodes:

* `load_documents`
* `preprocess`
* `chunk`
* `embed_chunks`
* `extract_rules`
* `style_analysis`
* `select_examples`
* `compose_profile`
* `store_profile`

Edges:

<pre class="overflow-visible!" data-start="6282" data-end="6432"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>load_documents</span><span> → preprocess → chunk → embed → extract_rules
extract_rules → style_analysis → select_examples → compose_profile → store_profile
</span></span></code></div></div></pre>

State keys:

<pre class="overflow-visible!" data-start="6447" data-end="6576"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"docs"</span><span>:</span><span></span><span>[</span><span>]</span><span>,</span><span>
  </span><span>"chunks"</span><span>:</span><span></span><span>[</span><span>]</span><span>,</span><span>
  </span><span>"embeddings"</span><span>:</span><span></span><span>[</span><span>]</span><span>,</span><span>
  </span><span>"rules"</span><span>:</span><span></span><span>{</span><span>}</span><span>,</span><span>
  </span><span>"style"</span><span>:</span><span></span><span>{</span><span>}</span><span>,</span><span>
  </span><span>"examples"</span><span>:</span><span></span><span>[</span><span>]</span><span>,</span><span>
  </span><span>"profile"</span><span>:</span><span></span><span>{</span><span>}</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

---

# 2. Ideation Graph (Super Agent 2)

Nodes:

* `serp_search`
* `keyword_extraction`
* `competitor_summarization`
* `brief_writer`

Edges:

<pre class="overflow-visible!" data-start="6721" data-end="6803"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>serp_search</span><span> → keyword_extraction → competitor_summarization → brief_writer
</span></span></code></div></div></pre>

Final output:

`ContentBrief(JSON)`

---

# 3. Copy Generation Graph (Super Agent 3)

Nodes:

* `load_profile`
* `merge_with_brief`
* `apply_platform_rules`
* `llm_generate`
* `post_editing`

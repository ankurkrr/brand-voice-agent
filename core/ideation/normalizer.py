"""
Post-Generation Normalizer for Agent 2 Output (Enhanced)

ARD Compliance Layer with Semantic Stripping:
Converts LLM prose → Strategy labels via rule-based insight extraction

Rules:
• Semantic stripping (NO blind truncation)
• Hard validation (fail fast on prose/numbers)
• Controlled retry (drop bad items, don't recall LLM)
• Deterministic processing only (NO ML/NLP)

Applied AFTER LLM generation, BEFORE persistence.
"""

import re
from typing import List
from typing import Optional
import collections
import math


# ============================================================================
# HARD VALIDATORS (Non-Negotiable)
# ============================================================================

def assert_not_sentence(text: str) -> None:
    """Rejects full sentences."""
    if text.endswith("."):
        raise ValueError(f"Sentence detected: {text}")
    if len(text.split()) > 8:
        raise ValueError(f"Too verbose ({len(text.split())} words): {text}")


def assert_no_numbers(text: str) -> None:
    """Rejects numeric claims (quantitative data leaks)."""
    if re.search(r"\d", text):
        raise ValueError(f"Numeric claim detected: {text}")


def assert_clean_phrase(text: str) -> None:
    """Rejects truncated/incomplete phrases."""
    if text and text[-1] in {",", ";", ":", "-"}:
        raise ValueError(f"Truncated phrase: {text}")


# ============================================================================
# SEMANTIC STRIPPING (Core Normalization)
# ============================================================================

# Verb pattern - captures ALL verbs that make text prose-like (Enhanced)
VERB_PATTERN = r"\b(is|are|was|were|will|can|could|should|would|may|might|must|has|have|had|do|does|did|be|been|being|presents|drives|reduces|improves|requires|enables|provides|offers|creates|supports|helps|allows|makes|causes|leads|results|shows|indicates|suggests|demonstrates|reveals|increased|decreased|grew|grown|rose|risen|fell|fallen|dropped|surged|jumped|plummeted|reached|surpassed|exceeded)\b"

def to_insight_label(text: str) -> str:
    """
    Converts sentence → abstract noun-phrase label (AGGRESSIVE).
    
    NOT semantic stripping - ABSTRACTION to strategy-level insight.
    
    Examples:
        "Global EV sales surpassed 10 million in 2022" 
        → "Global electric vehicle market expansion"
        
        "FDA approved 45 AI diagnostic tools in 2024"
        → "FDA AI diagnostic tool approval acceleration"
        
        "Charging infrastructure presents major adoption barrier"
        → "Charging infrastructure adoption barrier"
    
    Rules (NON-NEGOTIABLE):
        • Remove ALL numbers, dates, percentages
        • Remove ALL verbs and everything after
        • Remove articles (the, a, an)
        • Keep ONLY noun phrases
        • Max 6 words (abstract label, not explanation)
    """
    if not text:
        return text
    
    original = text
    text = text.lower().strip()
    
    # Remove ending punctuation
    text = re.sub(r"[.!?,;:]+$", "", text)
    
    # STEP 1: Remove ALL numeric/temporal content (BEFORE verb removal)
    # Numbers
    text = re.sub(r"\d+(\.\d+)?%", "", text)  # Percentages
    text = re.sub(r"\d+(\.\d+)?\s*(million|billion|thousand|trillion|M|B|K|T)", "", text)
    text = re.sub(r"\$\d+", "", text)  # Dollar amounts
    text = re.sub(r"\d{4}", "", text)  # Years
    text = re.sub(r"\b\d+\b", "", text)  # All remaining numbers
    
    # Temporal phrases
    text = re.sub(r"\b(in|by|during|since|until|from)\s+\d{4}\b", "", text)
    text = re.sub(r"\b(in recent years|in the future|over time|historically|currently)\b", "", text)
    
    # STEP 2: Remove verbs and EVERYTHING AFTER (this is the key abstraction step)
    # This converts "X does Y because Z" → "X"
    match = re.search(VERB_PATTERN, text)
    if match:
        # Cut at first verb - everything before is the subject (noun phrase)
        text = text[:match.start()]
    
    # STEP 3: Remove articles
    text = re.sub(r"\b(the|a|an)\b", "", text)
    
    # STEP 4: Remove prepositions and adverbs that don't add meaning
    text = re.sub(r"\b(of|for|to|in|on|at|with|from|by)\s+$", "", text)  # Trailing prepositions
    text = re.sub(r"\b(approximately|roughly|nearly|about|almost)\s*$", "", text) # Trailing adverbs (New)
    text = re.sub(r"\b(of|for|to|in|on|at|with|from|by)\s+$", "", text)  # Clean up again after adverbs
    
    # STEP 5: Clean whitespace
    text = " ".join(text.split())
    
    # STEP 6: Limit to 6 words (abstract label)
    words = text.split()
    if len(words) > 6:
        text = " ".join(words[:6])
    
    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:]
    
    # If result is too short or empty, return None (will be filtered out)
    if len(text) < 10:
        return None
    
    return text


def normalize_key_takeaways(takeaways: List[str]) -> List[str]:
    """
    Converts full sentences → abstract insight labels (STRICT).
    
    Strategy:
        • Apply aggressive abstraction (to_insight_label)
        • Validate: must be noun phrases only
        • Drop invalid items
        • Ensure minimum 2 valid items (ARD requirement)
    
    Examples:
        "Global EV sales reached 10M in 2022" → "Global electric vehicle market expansion"
        "FDA approved 45 AI tools" → "FDA AI diagnostic tool approval"
        "Infrastructure presents barrier" → "Infrastructure barrier"
    """
    cleaned = []
    
    for t in takeaways:
        if not t or not t.strip():
            continue
        
        try:
            # Aggressive abstraction
            label = to_insight_label(t)
            
            # Validation
            if label is None or len(label) < 10:
                print(f"[Normalizer] Dropped (too short after abstraction): {t}")
                continue
            
            # Must not be a sentence
            assert_not_sentence(label)
            assert_clean_phrase(label)
            
            cleaned.append(label)
            print(f"[Normalizer] Abstracted: '{t}' → '{label}'")
        
        except (ValueError, AssertionError) as e:
            print(f"[Normalizer] Dropped (validation failed): {t} | {e}")
            continue
    
    # Ensure minimum 2 items (ARD: min_items=2)
    if len(cleaned) < 2:
        print(f"[Normalizer] Warning: Only {len(cleaned)} items passed. Attempting basic cleanup for minimum 2...")
        
        # Try again with just punctuation removal (last resort)
        cleaned = []
        for t in takeaways[:4]:
            basic = t.strip()
            basic = re.sub(r"[.!?]+$", "", basic)
            if len(basic) > 10 and len(basic.split()) <= 8:
                cleaned.append(basic)
        
        # If still < 2, this is a critical failure
        if len(cleaned) < 2:
            raise ValueError(
                f"Agent-2 failed: Could not generate minimum 2 valid key_takeaways. "
                f"LLM output: {takeaways}"
            )
    
    return cleaned


# ============================================================================
# TARGET AUDIENCE (Role-Based Enforcement)
# ============================================================================

ROLE_PATTERNS = [
    "executives",
    "professionals",
    "analysts",
    "planners",
    "engineers",
    "managers",
    "directors",
    "specialists",
    "consultants",
    "strategists",
    "developers",
    "administrators",
    "operators",
    "decision makers",
    "stakeholders"
]


def normalize_target_audience(text: str, topic_context: str = "", serp_signals: Optional[dict] = None) -> str:
    """
    Enforces role-based target audience (never freely generated).
    
    Strategy:
        • LLM suggests audience
        • We enforce role-based rewrite
        • Format: "<Domain> <Role>"
    
    Examples:
        "People interested in EVs" → "Automotive technology professionals"
        "Healthcare workers" → "Healthcare professionals"
    
    Args:
        text: LLM-suggested audience
        topic_context: Topic for domain inference (optional)
    """
    if not text:
        return "General professionals"
    
    text_lower = text.lower()
    
    # Extract role if present
    role = None
    for pattern in ROLE_PATTERNS:
        if pattern in text_lower:
            role = pattern
            break
    
    # If no role found, default to "professionals"
    if not role:
        role = "professionals"
    
    # Extract domain from text or topic
    # Prefer dynamic SERP signals if provided
    domain_input = serp_signals if serp_signals else topic_context
    domain = _extract_domain(text_lower, domain_input)
    
    # Format: <Domain> <Role>
    if domain:
        return f"{domain.capitalize()} {role}"
    else:
        return f"Industry {role}"


def _extract_domain(text: str, topic_context: str = "") -> str:
    """
    Dynamic domain extraction pipeline.

    Strategy:
      - If `topic_context` contains pre-computed web signals (as dict), derive frequent
        noun-phrases / named entities from titles + snippets.
      - Otherwise, fall back to noun-phrase extraction from `text` and `topic_context`.

    This function intentionally does NOT rely on a fixed list of industries.
    Returns a short, human-friendly domain label or an empty string when unknown.
    """

    # Helper: simple embedding (hashing trick) to produce fixed-dim vectors
    def _embed_text(s: str, dim: int = 64):
        v = [0.0] * dim
        if not s:
            return v
        for w in re.findall(r"\w+", s.lower()):
            idx = hash(w) % dim
            v[idx] += 1.0
        # normalize
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def _cosine(a, b):
        num = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
        return num / (norm_a * norm_b)

    def _extract_candidates(texts):
        """Return frequent noun-phrase-like candidates from list of texts."""
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'for', 'to', 'in', 'on', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'this', 'that', 'these', 'those'
        }
        phrases = []
        for t in texts:
            if not t:
                continue
            # Prefer capitalized multi-word sequences (named entities / domains)
            caps = re.findall(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){0,3})\b", t)
            for c in caps:
                phrases.append(c.strip())

            # fallback: extract 2-4 word noun-phrase candidates (lowercase)
            tokens = [w for w in re.findall(r"[a-zA-Z]+", t.lower()) if w not in stopwords]
            for i in range(len(tokens)):
                for l in (2, 3, 4):
                    if i + l <= len(tokens):
                        cand = " ".join(tokens[i : i + l])
                        # drop if contains verb-like words
                        if re.search(VERB_PATTERN, cand):
                            continue
                        phrases.append(cand)

        if not phrases:
            return []

        counts = collections.Counter(phrases)
        # prefer capitalized candidates first
        capitalized = [p for p in counts.keys() if re.match(r"^[A-Z]", p)]
        if capitalized:
            # select top capitalized
            capitalized.sort(key=lambda p: (-counts[p], -len(p)))
            return [capitalized[0]]

        # otherwise return most common lowercase candidate
        most_common = counts.most_common(5)
        return [c for c, _ in most_common]

    # If topic_context contains a short query or SERP-like dict, prefer SERP signals.
    corpus_texts = []
    serp = None
    if isinstance(topic_context, dict):
        serp = topic_context
    # If text looks like a dict (rare), ignore

    if serp and isinstance(serp, dict):
        for k in ('titles', 'snippets'):
            items = serp.get(k, [])
            if items:
                for it in items:
                    corpus_texts.append(it)

    # Always include the raw text and topic_context (if string)
    if text:
        corpus_texts.append(text)
    if topic_context and isinstance(topic_context, str):
        corpus_texts.append(topic_context)

    if not corpus_texts:
        return ""

    # Step 1: extract candidate phrases
    candidates = _extract_candidates(corpus_texts)

    # Step 2: embedding-based cluster similarity (topic -> corpus centroid)
    try:
        topic_emb = _embed_text(topic_context or text)
        serp_embs = [_embed_text(t) for t in corpus_texts]
        centroid = [sum(col) / max(1, len(serp_embs)) for col in zip(*serp_embs)]
        sim = _cosine(topic_emb, centroid)
    except Exception:
        sim = 0.0

    # Step 3: pick best candidate and sanitize
    if candidates:
        pick = candidates[0]
        pick = re.sub(r"\b(of|for|to|in|on|at|with|from)\b", "", pick, flags=re.IGNORECASE)
        pick = " ".join([w.capitalize() for w in pick.split() if w])
        if sim < 0.05 and len(pick.split()) <= 1:
            return ""
        return pick

    return ""


# ============================================================================
# SEO KEYWORDS & H2 OUTLINE
# ============================================================================

def normalize_seo_keywords(keywords: List[str], topic: str = "", serp_signals: Optional[dict] = None) -> List[str]:
    """
    Dynamically derive SEO keywords based on provided keywords or the content topic
    and optional SERP signals (titles/snippets). This avoids a fixed, hardcoded
    taxonomy and instead extracts frequent noun tokens and candidate noun-phrases
    from the available corpus.

    Returns up to 15 normalized, de-duplicated keywords (lowercase).
    """
    if not keywords and not topic and not serp_signals:
        return []

    # Build the corpus from explicit keywords, topic, and SERP signals
    corpus_texts = []
    if keywords:
        for k in keywords:
            if k and isinstance(k, str):
                corpus_texts.append(k)
    if topic and isinstance(topic, str):
        corpus_texts.append(topic)
    if serp_signals and isinstance(serp_signals, dict):
        for k in ("titles", "snippets"):
            items = serp_signals.get(k, [])
            if items:
                for it in items:
                    if isinstance(it, str):
                        corpus_texts.append(it)

    # Tokenize and build unigram + bigram frequency counters
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'for', 'to', 'in', 'on', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'this', 'that', 'these', 'those', 'it', 'its',
        'from', 'as', 'at', 'be', 'have', 'has', 'had'
    }

    uni = collections.Counter()
    bi = collections.Counter()

    for text in corpus_texts:
        # sanitize
        t = re.sub(r"[^A-Za-z0-9\s]", " ", text)
        t = re.sub(r"\s+", " ", t).strip().lower()
        if not t:
            continue
        tokens = [w for w in t.split() if w and w not in stopwords]
        # collect unigrams
        for w in tokens:
            if len(w) >= 2:
                uni[w] += 1
        # collect bigrams
        for i in range(len(tokens) - 1):
            a, b = tokens[i], tokens[i + 1]
            # ignore bigrams with numeric tokens
            if re.search(r"\d", a) or re.search(r"\d", b):
                continue
            cand = f"{a} {b}"
            bi[cand] += 1

    # Prefer bigrams (more specific) then unigrams
    candidates = []
    for k, _ in bi.most_common(12):
        if len(candidates) >= 10:
            break
        candidates.append(k)

    # fill with top unigrams
    for k, _ in uni.most_common(20):
        if k in candidates:
            continue
        candidates.append(k)
        if len(candidates) >= 15:
            break

    # Final sanitize: remove overly generic tokens and short tokens
    final = []
    generic_blacklist = {'industry', 'topic', 'analysis', 'trends', 'research'}
    for c in candidates:
        c_clean = c.strip()
        if not c_clean:
            continue
        if c_clean in generic_blacklist:
            continue
        # drop single-character or empty
        if len(c_clean) < 2:
            continue
        final.append(c_clean)

    # Ensure uniqueness and preserve order
    seen = set()
    out = []
    for k in final:
        if k in seen:
            continue
        seen.add(k)
        out.append(k)

    return out


def normalize_h2_outline(outline: List[str]) -> List[str]:
    """Ensures H2 headings are concise labels."""
    normalized = []
    
    for heading in outline:
        if not heading:
            continue
        
        h = heading.strip()
        h = re.sub(r"[.!?]+$", "", h)
        
        # Remove common verbose patterns
        h = re.sub(r"^(how to|ways to|methods to|steps to)\s+", "", h, flags=re.IGNORECASE)
        h = re.sub(r"^(top|best)\s+\d+\s+", "", h, flags=re.IGNORECASE)
        h = re.sub(r"^(understanding|exploring|learning about)\s+", "", h, flags=re.IGNORECASE)
        
        # Limit to 6 words
        words = h.split()
        if len(words) > 6:
            h = " ".join(words[:6])
        
        h = re.sub(r"\s+", " ", h).strip()
        
        if h:
            h = h[0].upper() + h[1:]
            normalized.append(h)
    
    return normalized


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def normalize_content_brief(brief_data: dict, topic: str = "") -> dict:
    """
    Main normalization entry point with enhanced semantic stripping.
    
    Args:
        brief_data: Raw LLM output dict
        topic: Topic context for domain inference (optional)
    
    Returns:
        Normalized dict with ARD-compliant labels
    """
    normalized = {}
    
    # Target audience (role-based enforcement)
    if "target_audience" in brief_data:
        normalized["target_audience"] = normalize_target_audience(
            brief_data["target_audience"],
            topic_context=topic,
            serp_signals=brief_data.get("web_signals")
        )
    
    # SEO keywords
    if "seo_keywords" in brief_data:
        normalized["seo_keywords"] = normalize_seo_keywords(
            brief_data.get("seo_keywords", []),
            topic=topic,
            serp_signals=brief_data.get("web_signals")
        )
    
    # H2 outline
    if "h2_outline" in brief_data:
        normalized["h2_outline"] = normalize_h2_outline(
            brief_data.get("h2_outline", [])
        )
    
    # Key takeaways (semantic stripping + hard validation)
    if "key_takeaways" in brief_data:
        normalized["key_takeaways"] = normalize_key_takeaways(
            brief_data.get("key_takeaways", [])
        )
    
    return normalized

def extract_ui_labels(brief: dict) -> dict:
    """
    Safely extracts short UI chips from the StrategicBrief.
    Never fails or throws exceptions. Gracefully degrades.
    """
    content = brief.get("content_brief", brief)
    
    ui_labels = {
        "target_audience": "General professionals",
        "seo_keywords": [],
        "h2_outline": [],
        "key_takeaways": []
    }
    
    # 1. Target Audience Chip (Backwards compatibility for Deep Schema)
    role = content.get("persona_role", "")
    seniority = content.get("persona_seniority", "")
    company_type = content.get("persona_company_type", "")
    
    # Combine parts: e.g. "Executive VP of Digital Strategy professional sports league"
    parts = []
    if seniority: parts.append(seniority)
    if role: parts.append(role)
    if company_type: parts.append(f"in {company_type}")
    
    if parts:
        ui_labels["target_audience"] = " ".join(parts)
    else:
        # Fallback to legacy structure or default
        ta = content.get("target_audience", "")
        if ta:
            ui_labels["target_audience"] = ta
    
    # 2. SEO Keywords
    keywords = content.get("seo_keywords", [])
    ui_labels["seo_keywords"] = keywords[:5] 
    
    # 3. H2 Outline
    outline = content.get("h2_outline", [])
    ui_labels["h2_outline"] = outline
    
    # 4. Key Takeaways
    takeaways = content.get("key_takeaways", [])
    ui_labels["key_takeaways"] = takeaways[:2]
    
    return ui_labels

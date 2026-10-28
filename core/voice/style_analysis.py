# core/voice/style_analysis.py
from typing import List, Dict
import statistics
import re
from collections import Counter
import math

# -----------------------------
# Sentence Tokenization
# -----------------------------
def sentence_tokenize(text: str) -> List[str]:
    splits = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in splits if s.strip()]


# -----------------------------
# Average Sentence Length
# -----------------------------
def avg_sentence_length(text: str) -> float:
    sents = sentence_tokenize(text)
    if not sents:
        return 0.0
    return statistics.mean([len(s.split()) for s in sents])


# -----------------------------
# Flesch–Kincaid Reading Level
# -----------------------------
def flesch_kincaid_grade(text: str) -> float:
    sentences = sentence_tokenize(text)
    if not sentences:
        return 0.0

    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) == 0:
        return 0.0

    syllables = sum(count_syllables(w) for w in words)

    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)

    # F-K formula
    return round(0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59, 2)


def count_syllables(word: str) -> int:
    word = word.lower()
    vowels = "aeiouy"
    count = 0
    prev = False

    for c in word:
        if c in vowels:
            if not prev:
                count += 1
                prev = True
        else:
            prev = False

    if word.endswith("e"):
        count = max(1, count - 1)

    return max(1, count)


# -----------------------------
# Sentence Length Buckets
# -----------------------------
def sentence_length_distribution(text: str) -> Dict:
    sents = sentence_tokenize(text)
    if not sents:
        return {"short": 0, "medium": 0, "long": 0}

    bins = {"short": 0, "medium": 0, "long": 0}

    for s in sents:
        length = len(s.split())
        if length <= 10:
            bins["short"] += 1
        elif length <= 20:
            bins["medium"] += 1
        else:
            bins["long"] += 1

    return bins


# -----------------------------
# Passive Voice Detector (heuristic)
# -----------------------------
def detect_passive_voice(text: str) -> float:
    """
    Returns % of sentences that appear passive.
    Very rough heuristic: "was|were|is|are ... by"
    """
    sentences = sentence_tokenize(text)
    if not sentences:
        return 0.0

    passive_count = 0
    pattern = re.compile(r"\b(was|were|is|are|been|be)\b.*\bby\b", re.IGNORECASE)

    for s in sentences:
        if pattern.search(s):
            passive_count += 1

    return round((passive_count / len(sentences)) * 100, 2)


# -----------------------------
# Vocabulary Profile
# -----------------------------
def vocabulary_profile(text: str, top_n: int = 30) -> Dict:
    words = re.findall(r'\b\w+\b', text.lower())
    count = Counter(words)
    return {"top": count.most_common(top_n), "vocab_size": len(count)}


# -----------------------------
# Punctuation Profile
# -----------------------------
def punctuation_profile(text: str) -> Dict:
    return {
        "exclamations": text.count("!"),
        "questions": text.count("?"),
        "commas": text.count(","),
        "dashes": text.count("-")
    }


# -----------------------------
# Combined Style Metric Extractor
# -----------------------------
def style_metrics_from_documents(docs) -> Dict:
    joined = "\n\n".join([d.page_content for d in docs if d.page_content])

    return {
        "avg_sentence_length": avg_sentence_length(joined),
        "sentence_distribution": sentence_length_distribution(joined),
        "reading_level": flesch_kincaid_grade(joined),
        "passive_voice_frequency": detect_passive_voice(joined),
        "vocab_profile": vocabulary_profile(joined),
        "punct_profile": punctuation_profile(joined),
        "sentiment_estimate": "neutral"
    }


# -----------------------------
# Text Quality Scorer
# -----------------------------
def score_text_quality(text: str) -> float:
    """
    Scores writing quality for brand voice representativeness.
    Range: 0.0 to 100.0 (Higher is better)
    
    Factors:
    - Sentence length variance (Standard Deviation): Reward variation.
    - Passive voice ratio: Penalize high passive voice.
    - Readability: Target generally accessible range (e.g., 8-14).
    - Length/Completeness: Penalize very short text.
    """
    cleaned = text.strip()
    if not cleaned or len(cleaned) < 50:
        return 10.0  # Penalize ultra-short/empty text

    sentences = sentence_tokenize(cleaned)
    if len(sentences) < 2:
        return 20.0  # Penalize single-sentence snippets if they are supposed to be substantive

    # 1. Sentence Length Variance (Goal: Dynamic flow)
    lengths = [len(s.split()) for s in sentences]
    if len(lengths) > 1:
        std_dev = statistics.stdev(lengths)
        # Optimal variance is subjective, but 0 variance is robotic.
        # Cap reward at some reasonable std_dev (e.g., 5-10 words).
        variance_score = min(std_dev * 10, 30.0) 
    else:
        variance_score = 0.0

    # 2. Passive Voice (Goal: Active)
    passive_pct = detect_passive_voice(cleaned)  # e.g., 20.0 for 20%
    # Penalize if > 20%?
    # Score = 30 - passive_pct (clamped to 0)
    passive_score = max(0.0, 30.0 - passive_pct)

    # 3. Readability (Goal: Clear, Professional)
    # Flesch-Kincaid Grade level.
    fk_grade = flesch_kincaid_grade(cleaned)
    # Ideal range: 6 - 14?
    if 6 <= fk_grade <= 14:
        readability_score = 30.0
    elif fk_grade < 6:
        readability_score = 15.0 # Too simple
    else:
        readability_score = 15.0 # Too complex

    # 4. Base Integrity
    integrity_score = 10.0

    total_score = variance_score + passive_score + readability_score + integrity_score
    
    return min(100.0, max(0.0, total_score))

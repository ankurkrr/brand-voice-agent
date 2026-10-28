# Null & Empty Safety Guide

**Rule Zero:** `NULL` means "Data Unavailable", NOT "System Failure".

The AI Backend prioritizes **System Stability** over **Data Completeness**. We will return a valid 200 OK response with `null` fields rather than crashing with a 500 Error.

## 1. Safety Matrix

| Field Type | Possible "Empty" State | UI Behavior |
| :--- | :--- | :--- |
| **Strings** | `""` or `null` | Render placeholder text ("Not specified") or hide element. |
| **Arrays** | `[]` (Empty List) | Hide the list section entirely. Do NOT render empty bullets. |
| **Objects** | `null` | Hide the entire component widget. |
| **Numbers** | `null` | Do NOT render charts/graphs. |

## 2. Specific Field Guards

### Dimensional Scores (Radar Chart)
**Risk:** Often `null` for legacy profiles or simple inputs.
**Guard (Pseudo-code):**
```javascript
if (profile.dimensional_scores && 
    Object.values(profile.dimensional_scores).some(v => v !== null)) {
  renderRadarChart(profile.dimensional_scores);
} else {
  renderFallback("Voice analysis unavailable for this profile.");
}
```

### Platform Content (Access)
**Risk:** User requests "Twitter" but AI fails to generate it, or returns only "Blog".
**Guard (Pseudo-code):**
```javascript
// ✅ Safe Access
const tweets = response.twitter?.thread || [];

if (tweets.length > 0) {
  renderThread(tweets);
}
```

### Tone Secondary
**Risk:** Empty array `[]`.
**Guard (Pseudo-code):**
```javascript
// Don't render "Tone: Professional ()"
const secondary = (profile.tone.secondary || []).join(", ");
const label = secondary ? `${primary} (${secondary})` : primary;
```

---

## 3. Testing for Safety
Before approving a PR, verify:
1.  Does the UI crash if `dimensional_scores` is null?
2.  Does the UI look broken if `rules.forbidden_phrases` is empty?
3.  Does the page load if `response.twitter` is missing?

**If the answer is NO/NO/YES, the integration is safe.**

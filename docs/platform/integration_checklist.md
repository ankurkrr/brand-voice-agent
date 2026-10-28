# Platform Integration Checklist

**Use this checklist before deploying frontend integration.**

## 🛡 Safety Guards
- [ ] **Version Check:** UI branches logic based on `profile.version`.
- [ ] **Chart Guard:** Radar chart checks `if (dimensional_scores)` before rendering.
- [ ] **Platform Access:** `response.twitter?.thread` (Optional chaining) used for all platform keys.
- [ ] **List Handling:** UI handles empty arrays `[]` gracefully (hides section).
- [ ] **Latency:** API timeouts set to >60 seconds.

## 🔄 Flow Validation
- [ ] **Ingest:** Can upload PDF and get a `brand_id`.
- [ ] **Ideate:** Can generate a brief from a topic.
- [ ] **Execute:** Can generate stats from a brief.
- [ ] **Feedback:** Can submit feedback (`/feedback`) without 500 error.

## 🐛 Edge Cases
- [ ] **Null Profile:** UI handles 404 Profile Not Found.
- [ ] **Empty Keywords:** Ideation result with `[]` keywords rendering correctly (hidden).
- [ ] **Retry:** Retry button works for failed 500 requests.

---
**Signed Off By:** _________________________

-- Migration: Add Status to Content Briefs
-- Purpose: Track approval status of content briefs (DRAFT, APPROVED, REJECTED)
-- Run Order: 003

ALTER TABLE content_briefs
ADD COLUMN status VARCHAR(50) DEFAULT 'DRAFT';

-- Index for status queries
CREATE INDEX idx_content_briefs_status ON content_briefs(status);

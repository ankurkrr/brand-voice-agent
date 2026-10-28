-- Migration: Add Approval Status Fields
-- Purpose: Enable DRAFT/APPROVED/REJECTED workflow for Agent 1 & 2 outputs
-- Run Order: 001

-- Step 1: Add status column to content_briefs
ALTER TABLE content_briefs 
ADD COLUMN status VARCHAR(50) DEFAULT 'DRAFT';

-- Step 2: Update voice_profiles default status from 'active' to 'DRAFT'
ALTER TABLE voice_profiles 
MODIFY COLUMN status VARCHAR(50) DEFAULT 'DRAFT';

-- Step 3: Backfill existing records (backwards compatibility - assume approved)
UPDATE voice_profiles SET status = 'APPROVED' WHERE status = 'active';
UPDATE content_briefs SET status = 'APPROVED' WHERE status IS NOT NULL;

-- Step 4: Add indexes for status filtering
CREATE INDEX idx_voice_profiles_status ON voice_profiles(status);
CREATE INDEX idx_content_briefs_status ON content_briefs(status);

-- Verification queries (run these to confirm migration worked):
-- SELECT COUNT(*), status FROM voice_profiles GROUP BY status;
-- SELECT COUNT(*), status FROM content_briefs GROUP BY status;

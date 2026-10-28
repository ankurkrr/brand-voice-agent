-- Migration: Create Pipeline States Table
-- Purpose: Track pipeline execution state across Agent 1 → 2 → 3
-- Run Order: 002

CREATE TABLE IF NOT EXISTS pipeline_states (
    id CHAR(36) PRIMARY KEY,
    pipeline_id CHAR(36) NOT NULL UNIQUE,
    brand_id CHAR(36) NOT NULL,
    mode VARCHAR(10) DEFAULT 'v1',  -- 'v1' or 'v2'
    
    -- Agent 1 tracking
    agent1_profile_id CHAR(36),
    agent1_status VARCHAR(50) DEFAULT 'PENDING',  -- PENDING, DRAFT, APPROVED, REJECTED
    
    -- Agent 2 tracking  
    agent2_brief_id CHAR(36),
    agent2_status VARCHAR(50) DEFAULT 'PENDING',
    
    -- Agent 3 tracking
    agent3_execution_id CHAR(36),
    agent3_status VARCHAR(50) DEFAULT 'NOT_STARTED',  -- NOT_STARTED, COMPLETED, FAILED
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (brand_id) REFERENCES brands(brand_id) ON DELETE CASCADE,
    FOREIGN KEY (agent1_profile_id) REFERENCES voice_profiles(profile_id) ON DELETE SET NULL,
    FOREIGN KEY (agent2_brief_id) REFERENCES content_briefs(id) ON DELETE SET NULL
);

-- Indexes for efficient queries
CREATE INDEX idx_pipeline_states_brand_id ON pipeline_states(brand_id);
CREATE INDEX idx_pipeline_states_pipeline_id ON pipeline_states(pipeline_id);
CREATE INDEX idx_pipeline_states_agent1_status ON pipeline_states(agent1_status);
CREATE INDEX idx_pipeline_states_agent2_status ON pipeline_states(agent2_status);

-- Verification query:
-- SELECT * FROM pipeline_states LIMIT 5;

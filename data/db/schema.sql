-- ============================================================================
-- CANONICAL DATABASE SCHEMA: voice_meta
-- Supports: V1 Agents (Legacy) & V2 Agents (Multi-Persona)
-- ============================================================================

-- ============================================================================
-- 1. BRANDS
-- ============================================================================
CREATE TABLE IF NOT EXISTS brands (
    id CHAR(36) PRIMARY KEY,
    brand_id CHAR(36) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_brands_brand_id ON brands(brand_id);
CREATE INDEX idx_brands_name ON brands(name); 

-- ============================================================================
-- 2. AGENT-1 (V1 TABLES)
-- ============================================================================

-- Human-In-The-Loop Data
CREATE TABLE IF NOT EXISTS voice_profiles_human (
    profile_id CHAR(36) PRIMARY KEY,
    brand_id CHAR(36) NOT NULL,
    system_prompt TEXT,
    explicit_rules JSON NOT NULL,
    version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
CREATE INDEX idx_vp_human_brand ON voice_profiles_human(brand_id);

-- Machine-Only Data
CREATE TABLE IF NOT EXISTS voice_profiles_machine (
    id CHAR(36) PRIMARY KEY,
    profile_id CHAR(36) NOT NULL,
    brand_id CHAR(36) NOT NULL,
    dimensional_scores JSON,
    implicit_rules JSON,
    embeddings_meta JSON,
    audio_profile JSON,
    transcript_meta JSON,
    modalities JSON,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_vp_machine_human 
        FOREIGN KEY (profile_id) 
        REFERENCES voice_profiles_human(profile_id)
        ON DELETE CASCADE
);
CREATE INDEX idx_vp_machine_pid ON voice_profiles_machine(profile_id);


-- ============================================================================
-- 2B. PERSONAS (PHASE-2 MULTI-PERSONA)
-- ============================================================================

CREATE TABLE IF NOT EXISTS voice_personas (
    id CHAR(36) PRIMARY KEY,
    persona_id CHAR(36) NOT NULL UNIQUE,
    brand_id CHAR(36) NOT NULL,

    persona_name VARCHAR(255) NOT NULL,
    parent_persona_id CHAR(36) DEFAULT NULL,

    profile_data JSON NOT NULL,
    dimensional_scores JSON DEFAULT NULL,

    status VARCHAR(50) DEFAULT 'active',
    
    -- V2 New Fields
    persona_key VARCHAR(50) DEFAULT NULL,
    persona_origin VARCHAR(20) DEFAULT 'SYSTEM',
    persona_overlay_prompt TEXT DEFAULT NULL,
    persona_scope VARCHAR(20) DEFAULT 'OVERLAY',
    persona_version INT DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_persona_brand (brand_id),
    INDEX idx_persona_parent (parent_persona_id)
);


-- ============================================================================
-- 3. AGENT-2 TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS content_briefs_human (
    brief_id CHAR(36) PRIMARY KEY,
    brand_id CHAR(36) NOT NULL,
    voice_profile_id CHAR(36) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    content_brief_data JSON NOT NULL,
    status VARCHAR(50) DEFAULT 'DRAFT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_cb_human_vp 
        FOREIGN KEY (voice_profile_id) 
        REFERENCES voice_profiles_human(profile_id)
        ON DELETE RESTRICT
);
CREATE INDEX idx_cb_human_brand ON content_briefs_human(brand_id);
CREATE INDEX idx_content_briefs_brand_id ON content_briefs_human(brand_id);
CREATE INDEX idx_content_briefs_voice_profile_id ON content_briefs_human(voice_profile_id);
CREATE INDEX idx_content_briefs_topic ON content_briefs_human(topic);

CREATE TABLE IF NOT EXISTS content_briefs_machine (
    id CHAR(36) PRIMARY KEY,
    brief_id CHAR(36) NOT NULL,
    fingerprint VARCHAR(255),
    constraints JSON,
    web_signals JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_cb_machine_human 
        FOREIGN KEY (brief_id) 
        REFERENCES content_briefs_human(brief_id)
        ON DELETE CASCADE
);
CREATE INDEX idx_cb_machine_bid ON content_briefs_machine(brief_id);

-- ============================================================================
-- 4. AGENT-3 TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS generated_content (
    id CHAR(36) PRIMARY KEY,
    brand_id CHAR(36) NOT NULL,
    voice_profile_id CHAR(36) NOT NULL,
    content_brief_id CHAR(36),
    output_json JSON NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_gen_voice_profile 
        FOREIGN KEY (voice_profile_id) 
        REFERENCES voice_profiles_human(profile_id)
        ON DELETE RESTRICT,
        
    CONSTRAINT fk_gen_content_brief 
        FOREIGN KEY (content_brief_id) 
        REFERENCES content_briefs_human(brief_id)
        ON DELETE SET NULL
);
CREATE INDEX idx_generated_content_brand_id ON generated_content(brand_id);


-- ============================================================================
-- 4B. AGENT-3 (V2 MULTI-PERSONA OUTPUT)
-- ============================================================================

CREATE TABLE IF NOT EXISTS generated_content_machine (
    id CHAR(36) PRIMARY KEY,
    brand_id CHAR(36) NOT NULL,
    persona_id CHAR(36) NOT NULL,
    content_brief_id CHAR(36) NOT NULL,

    output_json JSON NOT NULL,

    dimensional_scores JSON NOT NULL,
    hierarchy_depth INT NOT NULL,

    confidence_score FLOAT,
    variants JSON,
    nuance_summary JSON,

    execution_version VARCHAR(10) DEFAULT 'v2',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gen_machine_brand ON generated_content_machine(brand_id);
CREATE INDEX idx_gen_machine_persona ON generated_content_machine(persona_id);


-- ============================================================================
-- 5. V2 INFRA STRUCTURE (REQUIRED)
-- ============================================================================

-- Dimensional Scoring Cache
CREATE TABLE IF NOT EXISTS persona_dimensional_cache (
    id CHAR(36) PRIMARY KEY,
    content_hash VARCHAR(64) NOT NULL,
    llm_model VARCHAR(50) NOT NULL,
    llm_temperature FLOAT DEFAULT 0.0,
    dimensions JSON NOT NULL,
    scores JSON NOT NULL,
    text_preview TEXT,
    token_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY idx_hash_model (content_hash, llm_model),
    INDEX idx_created (created_at)
);

-- Nuance Detections (Logging only, no FK constraint to avoid dependencies)
CREATE TABLE IF NOT EXISTS nuance_detections (
    id CHAR(36) PRIMARY KEY,
    persona_id CHAR(36) NOT NULL,
    
    generated_text TEXT NOT NULL,
    violation_phrase VARCHAR(500),
    violation_reason TEXT,
    severity ENUM('low', 'medium', 'high') NOT NULL,
    
    suggested_rewrite TEXT,
    platform VARCHAR(50),
    enforcement_mode ENUM('strict', 'advisory') NOT NULL,
    was_blocked BOOLEAN NOT NULL,
    
    semantic_similarity DECIMAL(5,3),
    rewrite_attempts INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_nuance_persona ON nuance_detections(persona_id);
CREATE INDEX idx_nuance_severity ON nuance_detections(severity);
CREATE INDEX idx_nuance_platform ON nuance_detections(platform);
CREATE INDEX idx_nuance_created ON nuance_detections(created_at);

-- ============================================================================
-- 6. SCHEMA VERSION TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_versions (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT IGNORE INTO schema_versions (version, description) 
VALUES ('2.0.0', 'Consolidated Schema: V1 Agents + V2 Infra');
-- ============================================================================
-- 4. FEEDBACK & ANALYTICS
-- ============================================================================

CREATE TABLE IF NOT EXISTS voice_profile_feedback_stats (
    profile_id CHAR(36) PRIMARY KEY,
    brand_id CHAR(36) NOT NULL,
    acceptance_rate DECIMAL(5,4) DEFAULT 0.0000,
    total_events INT DEFAULT 0,
    accept_count INT DEFAULT 0,
    rewrite_count INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_feedback_profile 
        FOREIGN KEY (profile_id) 
        REFERENCES voice_profiles_human(profile_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_feedback_stats_rate ON voice_profile_feedback_stats(acceptance_rate);

-- ============================================================================
-- 5. PIPELINE ORCHESTRATION
-- ============================================================================

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
    CONSTRAINT fk_pipeline_brand FOREIGN KEY (brand_id) REFERENCES brands(brand_id) ON DELETE CASCADE,
    CONSTRAINT fk_pipeline_profile FOREIGN KEY (agent1_profile_id) REFERENCES voice_profiles_human(profile_id) ON DELETE SET NULL,
    CONSTRAINT fk_pipeline_brief FOREIGN KEY (agent2_brief_id) REFERENCES content_briefs_human(brief_id) ON DELETE SET NULL
);

CREATE INDEX idx_pipeline_states_brand_id ON pipeline_states(brand_id);
CREATE INDEX idx_pipeline_states_pipeline_id ON pipeline_states(pipeline_id);
CREATE INDEX idx_pipeline_states_agent1_status ON pipeline_states(agent1_status);
CREATE INDEX idx_pipeline_states_agent2_status ON pipeline_states(agent2_status);

-- Migration: Create Persona Dimensional Cache Table (V2 Infra)
-- Purpose: Cache dimensional scores for determinism and efficiency
-- Schema: voice_meta
-- Run Order: 004

CREATE TABLE IF NOT EXISTS voice_meta.persona_dimensional_cache (
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

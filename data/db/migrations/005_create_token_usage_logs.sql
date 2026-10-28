CREATE TABLE IF NOT EXISTS token_usage_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id VARCHAR(255) NOT NULL,
    pipeline_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    provider VARCHAR(255) NOT NULL,
    model VARCHAR(255),
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    cost_usd FLOAT DEFAULT 0.0,
    latency_ms INT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_pipeline_request (pipeline_id, request_id)
);

CREATE INDEX idx_token_usage_pipeline ON token_usage_logs(pipeline_id);
CREATE INDEX idx_token_usage_agent ON token_usage_logs(agent_name);
CREATE INDEX idx_token_usage_created_at ON token_usage_logs(created_at);

"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-01-11 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # BRANDS TABLE - MySQL syntax
    op.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            id VARCHAR(36) PRIMARY KEY NOT NULL,
            brand_id VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_brands_brand_id (brand_id),
            INDEX idx_brands_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # VOICE PROFILES TABLE - MySQL syntax
    op.execute("""
        CREATE TABLE IF NOT EXISTS voice_profiles (
            id VARCHAR(36) PRIMARY KEY NOT NULL,
            profile_id VARCHAR(36) NOT NULL UNIQUE,
            brand_id VARCHAR(36) NOT NULL,
            version INT DEFAULT 1,
            status VARCHAR(50) DEFAULT 'active',
            profile_data JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_voice_profiles_brand_id (brand_id),
            INDEX idx_voice_profiles_profile_id (profile_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # CONTENT BRIEFS TABLE - MySQL syntax
    op.execute("""
        CREATE TABLE IF NOT EXISTS content_briefs (
            id VARCHAR(36) PRIMARY KEY NOT NULL,
            brand_id VARCHAR(36) NOT NULL,
            voice_profile_id VARCHAR(36) NOT NULL,
            topic VARCHAR(500) NOT NULL,
            content_brief_json JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_content_briefs_brand_id (brand_id),
            INDEX idx_content_briefs_voice_profile_id (voice_profile_id),
            INDEX idx_content_briefs_topic (topic(255)),
            CONSTRAINT fk_voice_profile 
                FOREIGN KEY (voice_profile_id) 
                REFERENCES voice_profiles(profile_id)
                ON DELETE RESTRICT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS content_briefs;")
    op.execute("DROP TABLE IF EXISTS voice_profiles;")
    op.execute("DROP TABLE IF EXISTS brands;")

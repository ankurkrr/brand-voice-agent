"""
V1 → V2 Migration Script for Phase 2: Multi-Persona Architect

This script migrates existing V1 voice profiles to V2 format with backward compatibility.

Migration Strategy:
1. Add new V2 columns to voice_profiles table (persona_id, persona_name, parent_persona_id, dimensional_scores)
2. For each V1 profile:
   - Set persona_id = profile_id (treat as primary persona)
   - Set persona_name = brand.name + " (Primary)"
   - Set parent_persona_id = NULL (root-level)
   - Calculate dimensional_scores from existing style_metrics if available
3. Create dimensional cache table
4. Create nuance detections table

Usage:
    python scripts/migrate_v1_to_v2.py --dry-run  # Preview changes
    python scripts/migrate_v1_to_v2.py --execute  # Apply migration
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.db.session import get_pool
import aiomysql


async def check_schema_version(pool):
    """Check current schema version."""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            # Check if schema_versions table exists
            await cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'schema_versions'
            """)
            result = await cursor.fetchone()
            
            if result['count'] == 0:
                return "1.0.0"  # V1 (no version table)
            
            # Check for V2
            await cursor.execute("SELECT version FROM schema_versions WHERE version = '2.0.0'")
            v2 = await cursor.fetchone()
            
            return "2.0.0" if v2 else "1.0.0"


async def backup_database(pool, db_name):
    """Create a backup before migration."""
    import subprocess
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_v1_{timestamp}.sql"
    
    print(f"Creating backup: {backup_file}")
    
    # Note: This requires mysqldump to be in PATH
    # User should manually backup if this fails
    try:
        subprocess.run([
            "mysqldump",
            "-u", "root",
            "-p",  # Will prompt for password
            db_name,
            "--result-file", backup_file
        ], check=True)
        print(f"✅ Backup created: {backup_file}")
        return backup_file
    except Exception as e:
        print(f"⚠️  Automated backup failed: {e}")
        print("Please manually backup your database before proceeding!")
        return None


async def add_v2_columns(pool, dry_run=False):
    """Add V2 columns to voice_profiles table."""
    alterations = [
        "ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS persona_id CHAR(36) UNIQUE",
        "ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS persona_name VARCHAR(255)",
        "ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS parent_persona_id CHAR(36) NULL",
        "ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS dimensional_scores JSON",
        "ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "CREATE INDEX IF NOT EXISTS idx_voice_profiles_persona_id ON voice_profiles(persona_id)",
        "CREATE INDEX IF NOT EXISTS idx_voice_profiles_parent_persona ON voice_profiles(parent_persona_id)",
    ]
    
    if dry_run:
        print("\n[DRY RUN] Would execute schema alterations:")
        for sql in alterations:
            print(f"  - {sql}")
        return
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for sql in alterations:
                print(f"Executing: {sql[:60]}...")
                await cursor.execute(sql)
            await conn.commit()
    
    print("✅ V2 columns added to voice_profiles table")


async def migrate_v1_profiles(pool, dry_run=False):
    """Migrate existing V1 profiles to V2 format."""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            # Fetch all V1 profiles (where persona_id is NULL)
            await cursor.execute("""
                SELECT vp.*, b.name as brand_name
                FROM voice_profiles vp
                LEFT JOIN brands b ON vp.brand_id = b.brand_id
                WHERE vp.persona_id IS NULL
            """)
            v1_profiles = await cursor.fetchall()
            
            if not v1_profiles:
                print("ℹ️  No V1 profiles found to migrate")
                return 0
            
            print(f"\nFound {len(v1_profiles)} V1 profiles to migrate")
            
            migrated_count = 0
            for profile in v1_profiles:
                profile_id = profile['profile_id']
                brand_name = profile['brand_name'] or "Unknown Brand"
                persona_name = f"{brand_name} (Primary)"
                
                # Parse profile_data JSON to extract style_metrics
                import json
                profile_data = json.loads(profile['profile_data']) if isinstance(profile['profile_data'], str) else profile['profile_data']
                
                # Calculate dimensional scores from style_metrics if available
                style_metrics = profile_data.get('style_metrics', {})
                dimensional_scores = calculate_dimensional_scores(style_metrics)
                
                if dry_run:
                    print(f"\n[DRY RUN] Would migrate profile: {profile_id}")
                    print(f"  - persona_id: {profile_id}")
                    print(f"  - persona_name: {persona_name}")
                    print(f"  - parent_persona_id: NULL")
                    print(f"  - dimensional_scores: {dimensional_scores}")
                else:
                    # Update profile with V2 fields
                    await cursor.execute("""
                        UPDATE voice_profiles
                        SET persona_id = %s,
                            persona_name = %s,
                            parent_persona_id = NULL,
                            dimensional_scores = %s
                        WHERE profile_id = %s
                    """, (profile_id, persona_name, json.dumps(dimensional_scores), profile_id))
                    
                    migrated_count += 1
            
            if not dry_run:
                await conn.commit()
                print(f"\n✅ Migrated {migrated_count} V1 profiles to V2 format")
            
            return migrated_count


def calculate_dimensional_scores(style_metrics):
    """
    Calculate dimensional scores from V1 style_metrics.
    
    Maps V1 metrics to V2 dimensional scores:
    - Humor: Based on punctuation (exclamations, emojis)
    - Empathy: Based on passive voice % (inverse - low passive = more active/empathetic)
    - Authority: Based on reading level (higher = more authoritative)
    - Formality: Based on sentence length and passive voice
    - Urgency: Based on sentence distribution (short sentences = more urgent)
    """
    if not style_metrics:
        # Default neutral scores if no metrics available
        return {
            "Humor": 0.5,
            "Empathy": 0.5,
            "Authority": 0.5,
            "Formality": 0.5,
            "Urgency": 0.5
        }
    
    scores = {}
    
    # Humor: Based on punctuation usage
    punct_profile = style_metrics.get('punct_profile', {})
    exclamations = punct_profile.get('exclamations', 0)
    # Normalize: More exclamations = more humorous (cap at 10)
    scores['Humor'] = min(0.95, max(0.05, exclamations / 10))
    
    # Empathy: Inverse of passive voice (active voice = more empathetic/direct)
    passive_voice_freq = style_metrics.get('passive_voice_frequency', 20) / 100  # Convert to 0-1
    scores['Empathy'] = max(0.05, 1.0 - passive_voice_freq)
    
    # Authority: Based on reading level
    reading_level = style_metrics.get('reading_level', 10)
    # Normalize: Higher reading level = more authoritative (cap at grade 16)
    scores['Authority'] = min(0.95, max(0.05, reading_level / 16))
    
    # Formality: Based on avg sentence length and passive voice
    avg_sentence_len = style_metrics.get('avg_sentence_length', 15)
    # Longer sentences + passive voice = more formal
    formality_score = (avg_sentence_len / 30) * 0.6 + passive_voice_freq * 0.4
    scores['Formality'] = min(0.95, max(0.05, formality_score))
    
    # Urgency: Based on sentence distribution (more short sentences = urgent)
    sent_dist = style_metrics.get('sentence_distribution', {'short': 0, 'medium': 0, 'long': 0})
    total_sents = sum(sent_dist.values()) or 1
    short_ratio = sent_dist.get('short', 0) / total_sents
    scores['Urgency'] = min(0.95, max(0.05, short_ratio))
    
    # Round to 2 decimal places
    return {k: round(v, 2) for k, v in scores.items()}


async def create_v2_tables(pool, dry_run=False):
    """Create new V2 tables (dimensional cache, nuance detections)."""
    # Read schema_v2.sql and extract CREATE TABLE statements for new tables
    schema_file = Path(__file__).parent.parent / "data" / "db" / "schema_v2.sql"
    
    if dry_run:
        print("\n[DRY RUN] Would create V2 tables:")
        print("  - persona_dimensional_cache")
        print("  - nuance_detections")
        print("  - schema_versions")
        return
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Execute schema (idempotent with CREATE TABLE IF NOT EXISTS)
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
            
            for stmt in statements:
                if any(keyword in stmt.upper() for keyword in ['CREATE TABLE', 'CREATE INDEX', 'ALTER TABLE', 'INSERT']):
                    try:
                        await cursor.execute(stmt)
                    except Exception as e:
                        # Ignore duplicate key/constraint errors
                        if 'Duplicate' not in str(e) and 'already exists' not in str(e):
                            print(f"Warning: {e}")
            
            await conn.commit()
    
    print("✅ V2 tables created successfully")


async def verify_migration(pool):
    """Verify migration completed successfully."""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            # Check V2 columns exist
            await cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                AND table_name = 'voice_profiles'
                AND column_name = 'persona_id'
            """)
            result = await cursor.fetchone()
            
            if result['count'] == 0:
                return False, "persona_id column not found"
            
            # Check V2 profiles migrated
            await cursor.execute("SELECT COUNT(*) as count FROM voice_profiles WHERE persona_id IS NOT NULL")
            result = await cursor.fetchone()
            
            if result['count'] == 0:
                return False, "No V2 profiles found (migration may have failed)"
            
            # Check V2 tables exist
            await cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                AND table_name = 'persona_dimensional_cache'
            """)
            result = await cursor.fetchone()
            
            if result['count'] == 0:
                return False, "persona_dimensional_cache table not found"
            
            return True, "All checks passed"


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate Brand Voice Agent from V1 to V2')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--execute', action='store_true', help='Execute migration')
    parser.add_argument('--skip-backup', action='store_true', help='Skip database backup')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("Error: Must specify --dry-run or --execute")
        sys.exit(1)
    
    print("=" * 80)
    print("PHASE 2: V1 → V2 MIGRATION")
    print("=" * 80)
    
    # Get database pool
    pool = await get_pool()
    
    try:
        # Check current version
        current_version = await check_schema_version(pool)
        print(f"\nCurrent schema version: {current_version}")
        
        if current_version == "2.0.0":
            print("✅ Already on V2! No migration needed.")
            return
        
        # Backup database
        if not args.dry_run and not args.skip_backup:
            backup_file = await backup_database(pool, "voice_meta")
            if backup_file is None:
                proceed = input("\nBackup failed. Continue anyway? (yes/no): ")
                if proceed.lower() != 'yes':
                    print("Migration cancelled.")
                    return
        
        # Step 1: Add V2 columns
        print("\n" + "=" * 80)
        print("STEP 1: Adding V2 columns to voice_profiles table")
        print("=" * 80)
        await add_v2_columns(pool, dry_run=args.dry_run)
        
        # Step 2: Migrate V1 profiles
        print("\n" + "=" * 80)
        print("STEP 2: Migrating V1 profiles to V2 format")
        print("=" * 80)
        migrated = await migrate_v1_profiles(pool, dry_run=args.dry_run)
        
        # Step 3: Create V2 tables
        print("\n" + "=" * 80)
        print("STEP 3: Creating V2 tables")
        print("=" * 80)
        await create_v2_tables(pool, dry_run=args.dry_run)
        
        # Verify
        if not args.dry_run:
            print("\n" + "=" * 80)
            print("VERIFICATION")
            print("=" * 80)
            success, message = await verify_migration(pool)
            if success:
                print(f"✅ Migration successful: {message}")
                print(f"\n✅ {migrated} V1 profiles migrated to V2 format")
                print("\nYou can now use multi-persona features!")
            else:
                print(f"❌ Migration verification failed: {message}")
        else:
            print("\n" + "=" * 80)
            print("[DRY RUN COMPLETE]")
            print("=" * 80)
            print("To execute migration, run: python scripts/migrate_v1_to_v2.py --execute")
    
    finally:
        pool.close()
        await pool.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())

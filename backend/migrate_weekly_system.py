from database import SessionLocal
from sqlalchemy import text

def run_migration():
    db = SessionLocal()
    try:
        print("🛠️ Running Weekly System Migration...")
        
        # 1. Add last_level_update to users
        print("➕ Adding 'last_level_update' to 'users'...")
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN last_level_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            print("✅ 'last_level_update' added.")
        except Exception as e:
            print(f"ℹ️ Could not add column (likely already exists): {e}")

        # 2. Create weekly_stats table
        print("➕ Creating 'weekly_stats' table...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS weekly_stats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                week_start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                avg_score FLOAT,
                is_level_up INT DEFAULT 0,
                total_activities INT DEFAULT 0
            )
        """))
        print("✅ 'weekly_stats' table ready.")
        
        db.commit()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    run_migration()

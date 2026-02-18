from database import SessionLocal
from sqlalchemy import text
from datetime import date, timedelta
from main import process_weekly_level_up

def test_levelup_simulation(username):
    db = SessionLocal()
    try:
        print(f"🧪 Simulating Weekly Level-Up for {username}...")
        
        # 1. Ensure user has recent scores in results
        db.execute(
            text("""
                INSERT INTO results (username, category, score, area, timestamp)
                VALUES 
                (:u, 'APTITUDE', 8, 'Logic', NOW()),
                (:u, 'TECHNICAL', 9, 'Python', NOW()),
                (:u, 'GD', 7, 'Communication', NOW()),
                (:u, 'INTERVIEW', 8, 'Performance', NOW())
            """),
            {"u": username}
        )
        db.commit()
        print("✅ Simulated scores added.")

        # 2. Mock 'today' as Sunday for testing (this requires main.py to be mockable or just run on Sunday)
        # For this test, we might need to manually check the code or use a wrapper.
        
        today = date.today()
        if today.weekday() != 6:
            print("⚠️ Not Sunday! Mocking logic check...")
            # We can't easily mock date.today() globally without 'freezegun', 
            # so let's check current levels.
            
        res = process_weekly_level_up(username, db)
        print(f"📊 Result: {'Level Up Processed' if res else 'No Update (likely not Sunday or already updated)'}")

    finally:
        db.close()

if __name__ == '__main__':
    test_levelup_simulation('Abiya')

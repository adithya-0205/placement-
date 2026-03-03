import sys
import os
from sqlalchemy import text
from database import SessionLocal
from main import get_todays_questions, get_questions_by_ids

def manual_test():
    db = SessionLocal()
    try:
        print("🚀 Requesting 10 balanced questions for Adithya (CSE technical)...")
        # This will trigger AI generation if needed and SAVE to daily_quiz
        q_ids = get_todays_questions(db, "Adithya", "technical", "CSE")
        print(f"✅ Selected IDs: {q_ids}")
        
        questions = get_questions_by_ids(db, q_ids)
        areas = [q['area'] for q in questions]
        
        print("\nTopic Distribution:")
        from collections import Counter
        for area, count in Counter(areas).items():
            print(f"- {area}: {count}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    manual_test()

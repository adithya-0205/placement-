from database import SessionLocal
from main import get_todays_questions
from sqlalchemy import text

def verify_aptitude_fallback():
    db = SessionLocal()
    try:
        print("Testing Aptitude Quiz (Hard)...")
        # Try to fetch questions for Aptitude Hard
        # Even if Hard doesn't exist, it should now fall back and return 10 questions
        questions = get_todays_questions(db, "Abiya", "APTITUDE")

        
        print(f"Fetched {len(questions)} questions: {questions}")
        if len(questions) == 10:
            print("✅ Success: Aptitude fallback working!")
        else:
            print(f"❌ Failure: Only fetched {len(questions)} questions.")
            
    except Exception as e:
        print(f"❌ Error during verification: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    verify_aptitude_fallback()

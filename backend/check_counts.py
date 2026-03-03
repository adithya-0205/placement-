from database import SessionLocal
from sqlalchemy import text

def check_counts():
    db = SessionLocal()
    try:
        users = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        results = db.execute(text("SELECT COUNT(*) FROM results")).scalar()
        daily = db.execute(text("SELECT COUNT(*) FROM daily_quiz")).scalar()
        questions = db.execute(text("SELECT COUNT(*) FROM questions")).scalar()
        
        print(f"Users: {users}")
        print(f"Results: {results}")
        print(f"Daily Quiz: {daily}")
        print(f"Questions: {questions}")
        
    finally:
        db.close()

if __name__ == '__main__':
    check_counts()

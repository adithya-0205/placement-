from database import SessionLocal
from sqlalchemy import text

def audit_aptitude():
    db = SessionLocal()
    try:
        print("--- Aptitude Branch Distribution ---")
        res = db.execute(text("SELECT branch, COUNT(*) FROM questions WHERE category='APTITUDE' GROUP BY branch"))
        for row in res:
            print(f"Branch '{row[0]}': {row[1]}")
            
        print("\n--- Aptitude Difficulty Distribution ---")
        res = db.execute(text("SELECT difficulty, COUNT(*) FROM questions WHERE category='APTITUDE' GROUP BY difficulty"))
        for row in res:
            print(f"Difficulty '{row[0]}': {row[1]}")
            
        print("\n--- Aptitude 'Common' Difficulty Distribution ---")
        res = db.execute(text("SELECT difficulty, COUNT(*) FROM questions WHERE category='APTITUDE' AND branch='Common' GROUP BY difficulty"))
        for row in res:
            print(f"Difficulty '{row[0]}': {row[1]}")
            
    finally:
        db.close()

if __name__ == '__main__':
    audit_aptitude()

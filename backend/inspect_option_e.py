from database import SessionLocal
from sqlalchemy import text

def inspect_option_e():
    db = SessionLocal()
    try:
        res = db.execute(text("SELECT id, branch, question, option_e, correct_answer FROM questions WHERE option_e IS NOT NULL AND option_e != '' LIMIT 30"))
        rows = res.fetchall()
        print(f"--- Sample of 30 questions with option_e ---")
        for r in rows:
            print(f"ID {r[0]} ({r[1]}): Ans={r[4]} | Option E: {r[3]}")
    finally:
        db.close()

if __name__ == '__main__':
    inspect_option_e()

from database import SessionLocal
from sqlalchemy import text

def audit_option_e():
    db = SessionLocal()
    try:
        # Check if option_e column exists
        res = db.execute(text("DESCRIBE questions"))
        columns = [row[0] for row in res]
        if 'option_e' not in columns:
            print("❌ 'option_e' column does not exist in the database.")
            return

        print("✅ 'option_e' column exists.")

        # Check for questions with option_e populated
        res = db.execute(text("SELECT id, branch, option_e, correct_answer FROM questions WHERE option_e IS NOT NULL AND option_e != ''"))
        rows = res.fetchall()
        print(f"Total questions with option_e populated: {len(rows)}")
        
        # Check for questions with 'E' as answer
        res = db.execute(text("SELECT id, branch, question, option_e, correct_answer FROM questions WHERE correct_answer = 'E' OR correct_answer = 'e'"))
        rows_e = res.fetchall()
        print(f"Total questions with 'E' as correct_answer: {len(rows_e)}")
        for r in rows_e:
            print(f"ID {r[0]} ({r[1]}): Ans=E | Option E: {r[3]}")

    finally:
        db.close()

if __name__ == '__main__':
    audit_option_e()
